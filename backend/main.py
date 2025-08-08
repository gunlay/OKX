from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import threading
import json
import logging
import os
from fastapi.middleware.cors import CORSMiddleware
import pytz

# 导入自定义模块
from models import Base, UserConfig, DCAPlan, Transaction, AssetHistory, encrypt_text, decrypt_text
from okx_api import OKXClient, get_popular_coins_public

# 配置日志
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'dca_service.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger("dca-service")

DATABASE_URL = "sqlite:///./dca.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

# 允许所有来源跨域（开发环境用，生产建议指定域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或指定前端地址如 ["http://13.158.74.102"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 使用Asia/Shanghai时区
TIMEZONE = pytz.timezone('Asia/Shanghai')

# 配置调度器，使用Asia/Shanghai时区
scheduler = BackgroundScheduler(timezone=TIMEZONE)
scheduler.start()
lock = threading.Lock()

# 创建数据库表
Base.metadata.create_all(bind=engine)

# Pydantic 模型
class DCAPlanCreate(BaseModel):
    title: Optional[str] = None
    symbol: str
    amount: float
    frequency: str
    day_of_week: Optional[int] = None
    month_days: Optional[str] = None  # 存储每月的多个日期，JSON字符串
    time: str
    direction: Optional[str] = "buy"  # 默认为买入

class DCAPlanOut(DCAPlanCreate):
    id: int
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

class ApiConfig(BaseModel):
    api_key: str
    secret_key: str
    passphrase: str

class CoinConfig(BaseModel):
    selected_coins: List[str]

class ConfigResponse(BaseModel):
    api_key: str = ""
    secret_key: str = ""
    passphrase: str = ""
    selected_coins: List[str] = []

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 执行定投任务
def execute_dca_task(plan_id: int):
    logger.info(f"执行定投任务 ID: {plan_id}")
    with lock:
        db = SessionLocal()
        try:
            # 获取任务信息
            plan = db.query(DCAPlan).filter(DCAPlan.id == plan_id).first()
            if not plan or plan.status != "enabled":
                logger.warning(f"任务 {plan_id} 不存在或已禁用，跳过执行")
                return
            
            # 检查是否已经执行过（防止重复执行）
            now = datetime.now(TIMEZONE)
            today = now.date()
            today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=TIMEZONE)
            today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=TIMEZONE)
            
            # 获取任务的最后时间更新时间
            last_time_update = getattr(plan, 'last_time_update', None)
            
            # 检查今天是否已经执行过该任务
            query = db.query(Transaction).filter(
                Transaction.plan_id == plan_id,
                Transaction.executed_at >= today_start,
                Transaction.executed_at <= today_end
            )
            
            # 如果任务时间有更新，只检查更新后的执行记录
            if last_time_update and last_time_update.date() == today:
                query = query.filter(Transaction.executed_at > last_time_update)
            
            existing_transaction = query.first()
            
            if existing_transaction:
                logger.info(f"任务 {plan_id} 在当前时间设置下今天已经执行过，跳过执行")
                return
            
            # 获取API配置
            config = db.query(UserConfig).first()
            if not config:
                logger.error(f"任务 {plan_id} 执行失败: 未找到API配置")
                return
            
            api_key = decrypt_text(config.api_key)
            secret_key = decrypt_text(config.secret_key)
            passphrase = decrypt_text(config.passphrase)
            
            if not api_key or not secret_key or not passphrase:
                logger.error(f"任务 {plan_id} 执行失败: API配置不完整")
                return
            
            # 创建OKX客户端
            client = OKXClient(api_key=api_key, secret_key=secret_key, passphrase=passphrase)
            
            # 执行交易
            side = "sell" if plan.direction == "sell" else "buy"
            
            # 对于卖出操作，需要先查询账户余额，获取可用的币种数量
            if side == "sell":
                # 获取币种信息，例如BTC-USDT中的BTC
                base_currency = plan.symbol.split('-')[0]
                balance_result = client.get_trading_balance()
                
                if balance_result.get('code') != '0':
                    logger.error(f"任务 {plan_id} 获取账户余额失败: {balance_result.get('msg', '未知错误')}")
                    # 记录失败交易
                    transaction = Transaction(
                        plan_id=plan.id,
                        symbol=plan.symbol,
                        amount=plan.amount,
                        direction=plan.direction,
                        status="failed",
                        response=json.dumps({"error": f"获取账户余额失败: {balance_result.get('msg', '未知错误')}"}),
                        executed_at=datetime.now(TIMEZONE)
                    )
                    db.add(transaction)
                    db.commit()
                    return
                
                # 查找对应币种的可用余额
                available_amount = 0
                for item in balance_result.get('data', []):
                    for balance in item.get('details', []):
                        if balance.get('ccy') == base_currency:
                            available_amount = float(balance.get('availBal', 0))
                            break
                
                if available_amount <= 0:
                    logger.error(f"任务 {plan_id} 卖出失败: {base_currency}余额不足")
                    # 记录失败交易
                    transaction = Transaction(
                        plan_id=plan.id,
                        symbol=plan.symbol,
                        amount=plan.amount,
                        direction=plan.direction,
                        status="failed",
                        response=json.dumps({"error": f"{base_currency}余额不足"}),
                        executed_at=datetime.now(TIMEZONE)
                    )
                    db.add(transaction)
                    db.commit()
                    return
                
                # 获取当前市场价格，计算可以卖出的数量
                ticker_result = client.get_ticker(plan.symbol)
                if ticker_result.get('code') != '0':
                    logger.error(f"任务 {plan_id} 获取市场价格失败: {ticker_result.get('msg', '未知错误')}")
                    # 记录失败交易
                    transaction = Transaction(
                        plan_id=plan.id,
                        symbol=plan.symbol,
                        amount=plan.amount,
                        direction=plan.direction,
                        status="failed",
                        response=json.dumps({"error": f"获取市场价格失败: {ticker_result.get('msg', '未知错误')}"}),
                        executed_at=datetime.now(TIMEZONE)
                    )
                    db.add(transaction)
                    db.commit()
                    return
                
                current_price = float(ticker_result['data'][0].get('last', 0))
                if current_price <= 0:
                    logger.error(f"任务 {plan_id} 获取市场价格异常: {current_price}")
                    # 记录失败交易
                    transaction = Transaction(
                        plan_id=plan.id,
                        symbol=plan.symbol,
                        amount=plan.amount,
                        direction=plan.direction,
                        status="failed",
                        response=json.dumps({"error": f"获取市场价格异常: {current_price}"}),
                        executed_at=datetime.now(TIMEZONE)
                    )
                    db.add(transaction)
                    db.commit()
                    return
                
                # 计算卖出数量：如果plan.amount小于等于可用余额*当前价格，则按照plan.amount/当前价格计算卖出数量
                # 否则卖出全部可用余额
                if plan.amount <= available_amount * current_price:
                    sell_size = plan.amount / current_price
                else:
                    sell_size = available_amount
                
                # 确保卖出数量不超过可用余额
                sell_size = min(sell_size, available_amount)
                
                # 处理精度问题：OKX对不同币种有不同的精度要求
                # 通常BTC是8位小数，ETH是6位小数，其他币种可能有不同要求
                # 这里我们根据币种类型设置合适的精度
                if base_currency == 'BTC':
                    sell_size = round(sell_size, 8)  # BTC通常使用8位小数
                elif base_currency == 'ETH':
                    sell_size = round(sell_size, 6)  # ETH通常使用6位小数
                else:
                    sell_size = round(sell_size, 4)  # 其他币种默认使用4位小数
                
                # 确保数量大于0
                if sell_size <= 0:
                    logger.error(f"任务 {plan_id} 卖出失败: 计算后的卖出数量为0")
                    # 记录失败交易
                    transaction = Transaction(
                        plan_id=plan.id,
                        symbol=plan.symbol,
                        amount=plan.amount,
                        direction=plan.direction,
                        status="failed",
                        response=json.dumps({"error": "计算后的卖出数量为0"}),
                        executed_at=datetime.now(TIMEZONE)
                    )
                    db.add(transaction)
                    db.commit()
                    return
                
                logger.info(f"任务 {plan_id} 卖出 {base_currency}: 金额 {plan.amount} USDT, 数量 {sell_size} {base_currency}, 当前价格 {current_price} USDT")
                
                # 执行卖出订单
                order_result = client.place_order(
                    symbol=plan.symbol,
                    side=side,
                    order_type="market",
                    size=str(sell_size)
                )
            else:
                # 买入逻辑保持不变
                order_result = client.place_order(
                    symbol=plan.symbol,
                    side=side,
                    order_type="market",
                    size=str(plan.amount)
                )
            
            # 记录执行结果
            # 记录执行结果
            logger.info(f"任务 {plan_id} 执行结果: {order_result}")
            
            # 创建交易记录
            if order_result.get('code') == '0':
                # 成功执行，尝试获取订单详情来获取成交价格和数量
                order_id = None
                fill_details = None
                if order_result.get('data') and len(order_result['data']) > 0:
                    order_id = order_result['data'][0].get('ordId')
                
                # 获取成交详情
                if order_id:
                    import time
                    # 等待5秒让成交数据生成（增加等待时间）
                    time.sleep(5)
                    
                    # 对于市价单，我们需要特别处理
                    # 市价买单：sz表示买入金额，需要从成交明细获取实际成交数量
                    # 市价卖单：sz表示卖出数量，需要从成交明细获取实际成交金额
                    
                    # 先尝试获取成交明细，这是最准确的
                    fills_result = client.get_order_fills(order_id)
                    logger.info(f"任务 {plan_id} 成交明细响应: {fills_result}")
                    
                    if fills_result.get('code') == '0' and fills_result.get('data') and len(fills_result['data']) > 0:
                        # 成交明细可能有多条记录，我们需要汇总
                        total_fill_px = 0
                        total_fill_sz = 0
                        total_fill_amt = 0
                        fill_count = 0
                        
                        for fill_info in fills_result['data']:
                            try:
                                fill_px = float(fill_info.get('fillPx', 0))
                                fill_sz = float(fill_info.get('fillSz', 0))
                                
                                if fill_px > 0 and fill_sz > 0:
                                    total_fill_px += fill_px * fill_sz  # 加权价格
                                    total_fill_sz += fill_sz
                                    total_fill_amt += fill_px * fill_sz
                                    fill_count += 1
                            except (ValueError, TypeError) as e:
                                logger.warning(f"解析成交明细数据异常: {str(e)}")
                        
                        # 计算加权平均价格
                        if total_fill_sz > 0:
                            avg_fill_px = total_fill_px / total_fill_sz
                            
                            fill_details = {
                                'fillPx': str(avg_fill_px),  # 成交均价
                                'fillSz': str(total_fill_sz),  # 累计成交数量
                                'fillAmt': str(total_fill_amt),  # 成交金额
                                'ordId': order_id
                            }
                            logger.info(f"任务 {plan_id} 从成交明细汇总获取成交信息: {fill_details}")
                    
                    # 如果成交明细没有数据，尝试获取订单详情
                    if not fill_details:
                        for attempt in range(3):  # 最多重试3次
                            try:
                                order_detail = client.get_order_detail(order_id)
                                logger.info(f"任务 {plan_id} 订单详情响应 (尝试{attempt+1}): {order_detail}")
                                
                                if order_detail.get('code') == '0' and order_detail.get('data'):
                                    order_info = order_detail['data'][0]
                                    
                                    # 检查订单状态是否已完成
                                    if order_info.get('state') in ['filled', 'partially_filled']:
                                        # 从订单详情中获取成交价格和数量
                                        avg_px = order_info.get('avgPx')
                                        acc_fill_sz = order_info.get('accFillSz')
                                        fill_amt = None
                                        
                                        # 计算成交金额
                                        if avg_px and acc_fill_sz:
                                            try:
                                                fill_amt = str(float(avg_px) * float(acc_fill_sz))
                                            except (ValueError, TypeError):
                                                pass
                                        
                                        # 确保值不为空
                                        if avg_px and acc_fill_sz:
                                            fill_details = {
                                                'fillPx': avg_px,  # 成交均价
                                                'fillSz': acc_fill_sz,  # 累计成交数量
                                                'fillAmt': fill_amt,  # 成交金额
                                                'ordId': order_id
                                            }
                                            logger.info(f"任务 {plan_id} 从订单详情获取成交信息: {fill_details}")
                                            break
                                    else:
                                        logger.info(f"任务 {plan_id} 订单状态: {order_info.get('state')} (尝试{attempt+1})")
                                
                                if attempt < 2:  # 不是最后一次尝试
                                    time.sleep(3)  # 等待3秒再重试
                                    
                            except Exception as e:
                                logger.warning(f"任务 {plan_id} 获取订单详情异常 (尝试{attempt+1}): {str(e)}")
                                if attempt < 2:  # 不是最后一次尝试
                                    time.sleep(3)  # 等待3秒再重试
                    
                    # 如果仍然没有获取到成交信息，使用原始订单信息和当前市场价格估算
                    if not fill_details:
                        logger.warning(f"任务 {plan_id} 无法从API获取成交详情，使用估算值")
                        
                        # 获取当前市场价格
                        try:
                            ticker_result = client.get_ticker(plan.symbol)
                            if ticker_result.get('code') == '0' and ticker_result.get('data'):
                                current_price = float(ticker_result['data'][0].get('last', 0))
                                
                                # 根据订单类型估算成交信息
                                if side == "buy":
                                    # 买入：使用订单金额和当前价格估算
                                    est_size = float(plan.amount) / current_price
                                    fill_details = {
                                        'fillPx': str(current_price),
                                        'fillSz': str(est_size),
                                        'fillAmt': str(plan.amount),
                                        'ordId': order_id,
                                        'estimated': True  # 标记为估算值
                                    }
                                else:
                                    # 卖出：使用卖出数量和当前价格估算
                                    if 'sell_size' in locals():
                                        est_amount = float(sell_size) * current_price
                                        fill_details = {
                                            'fillPx': str(current_price),
                                            'fillSz': str(sell_size),
                                            'fillAmt': str(est_amount),
                                            'ordId': order_id,
                                            'estimated': True  # 标记为估算值
                                        }
                                
                                logger.info(f"任务 {plan_id} 使用估算值作为成交信息: {fill_details}")
                        except Exception as e:
                            logger.warning(f"任务 {plan_id} 估算成交信息异常: {str(e)}")
                
                # 构建完整的响应数据，包含成交详情
                complete_response = {
                    "order_result": order_result,
                    "fill_details": fill_details
                }
                
                transaction = Transaction(
                    plan_id=plan.id,
                    symbol=plan.symbol,
                    amount=plan.amount,
                    direction=plan.direction or "buy",
                    status="success",
                    response=json.dumps(complete_response),
                    executed_at=datetime.now(TIMEZONE)
                )
                db.add(transaction)
                db.commit()
                logger.info(f"任务 {plan_id} 交易记录已保存")
            else:
                # 执行失败
                transaction = Transaction(
                    plan_id=plan.id,
                    symbol=plan.symbol,
                    amount=plan.amount,
                    direction=plan.direction or "buy",
                    status="failed",
                    response=json.dumps(order_result),
                    executed_at=datetime.now(TIMEZONE)
                )
                db.add(transaction)
                db.commit()
                logger.error(f"任务 {plan_id} 执行失败: {order_result.get('msg', '未知错误')}")
        except Exception as e:
            logger.exception(f"任务 {plan_id} 执行异常: {str(e)}")
            db.rollback()
        finally:
            db.close()

# 调度任务
def schedule_task(plan, check_missed=False):
    job_id = f"dca_task_{plan.id}"
    
    # 如果已存在任务，先移除
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"移除现有任务调度 {job_id}")
    
    # 如果任务已禁用，不再调度
    if plan.status != "enabled":
        logger.info(f"任务 {plan.id} 已禁用，不再调度")
        return
    
    # 解析时间
    try:
        hour, minute = plan.time.split(":")
        hour = int(hour)
        minute = int(minute)
    except (ValueError, TypeError) as e:
        logger.error(f"任务 {plan.id} 时间格式错误: {plan.time}, 错误: {str(e)}")
        return
    
    # 根据频率创建触发器
    if plan.frequency == "daily":
        trigger = CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE)
        logger.info(f"任务 {plan.id} 调度为每天 {hour:02d}:{minute:02d}")
    elif plan.frequency == "weekly" and plan.day_of_week is not None:
        trigger = CronTrigger(day_of_week=plan.day_of_week, hour=hour, minute=minute, timezone=TIMEZONE)
        logger.info(f"任务 {plan.id} 调度为每周 {plan.day_of_week} {hour:02d}:{minute:02d}")
    elif plan.frequency == "monthly":
        if plan.month_days and len(plan.month_days) > 0:
            try:
                month_days = json.loads(plan.month_days)
                # 为每个日期创建单独的任务
                for day in month_days:
                    day_job_id = f"dca_task_{plan.id}_day_{day}"
                    if scheduler.get_job(day_job_id):
                        scheduler.remove_job(day_job_id)
                        logger.info(f"移除现有月度任务调度 {day_job_id}")
                    
                    day_trigger = CronTrigger(day=day, hour=hour, minute=minute, timezone=TIMEZONE)
                    scheduler.add_job(
                        execute_dca_task,
                        trigger=day_trigger,
                        args=[plan.id],
                        id=day_job_id,
                        replace_existing=True,
                        misfire_grace_time=86400,  # 允许任务最多延迟1天执行
                        coalesce=True,  # 合并错过的执行
                        max_instances=1  # 最多同时运行1个实例
                    )
                    logger.info(f"任务 {plan.id} 调度为每月 {day}日 {hour:02d}:{minute:02d}, job_id={day_job_id}")
                
                # 已经为每个日期创建了单独的任务，不需要再创建主任务
                return
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"解析月份日期失败: {str(e)}, 原始数据: {plan.month_days}")
                # 如果解析失败，回退到默认行为：每月1日执行
                trigger = CronTrigger(day=1, hour=hour, minute=minute, timezone=TIMEZONE)
                logger.info(f"任务 {plan.id} 解析月份日期失败，回退到每月1日 {hour:02d}:{minute:02d}")
        else:
            # 如果没有指定日期，默认每月1日执行
            trigger = CronTrigger(day=1, hour=hour, minute=minute, timezone=TIMEZONE)
            logger.info(f"任务 {plan.id} 调度为每月1日 {hour:02d}:{minute:02d}")
    else:
        logger.error(f"任务 {plan.id} 频率配置错误: {plan.frequency}")
        return
    
    # 添加任务（针对每日和每周的情况，或者月份解析失败的情况）
    scheduler.add_job(
        execute_dca_task,
        trigger=trigger,
        args=[plan.id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=86400,  # 允许任务最多延迟1天执行
        coalesce=True,  # 合并错过的执行
        max_instances=1  # 最多同时运行1个实例
    )
    logger.info(f"成功添加任务调度 {job_id}")
    
    # 检查任务是否成功添加
    job = scheduler.get_job(job_id)
    if job:
        next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "未调度"
        logger.info(f"任务 {plan.id} 下次执行时间: {next_run}")
        
        # 检查是否需要立即执行一次任务（仅当check_missed为True时）
        if check_missed and job.next_run_time:
            now = datetime.now(TIMEZONE)
            # 如果下次执行时间比当前时间晚很多（超过一个周期），可能是因为今天的执行时间已经过去
            # 检查今天是否已经执行过
            today = now.date()
            today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=TIMEZONE)
            today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=TIMEZONE)
            
            db = SessionLocal()
            try:
                # 检查今天是否已经执行过该任务
                existing_transaction = db.query(Transaction).filter(
                    Transaction.plan_id == plan.id,
                    Transaction.executed_at >= today_start,
                    Transaction.executed_at <= today_end
                ).first()
                
                # 如果今天没有执行过，并且当前时间已经超过了计划执行时间，则立即执行一次
                plan_hour, plan_minute = map(int, plan.time.split(":"))
                plan_time_today = datetime.combine(today, datetime.min.time()).replace(tzinfo=TIMEZONE)
                plan_time_today = plan_time_today.replace(hour=plan_hour, minute=plan_minute)
                
                if not existing_transaction and now >= plan_time_today:
                    # 检查是否符合执行条件（每周或每月的特定日期）
                    should_execute = False
                    
                    if plan.frequency == "daily":
                        should_execute = True
                    elif plan.frequency == "weekly" and plan.day_of_week is not None:
                        # 检查今天是否是指定的星期几
                        if now.weekday() == plan.day_of_week:
                            should_execute = True
                    elif plan.frequency == "monthly" and plan.month_days:
                        # 检查今天是否是指定的月份日期
                        try:
                            month_days = json.loads(plan.month_days)
                            if now.day in month_days:
                                should_execute = True
                        except (json.JSONDecodeError, ValueError):
                            pass
                    
                    if should_execute:
                        logger.info(f"任务 {plan.id} 编辑后时间已过，立即执行一次")
                        # 在新线程中执行，避免阻塞当前线程
                        import threading
                        threading.Thread(target=execute_dca_task, args=[plan.id]).start()
            finally:
                db.close()
    else:
        logger.error(f"任务 {plan.id} 调度失败，未找到对应的任务")

# 打印所有调度任务
def print_all_jobs():
    jobs = scheduler.get_jobs()
    logger.info(f"当前共有 {len(jobs)} 个调度任务:")
    for job in jobs:
        next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "未调度"
        logger.info(f"任务ID: {job.id}, 下次执行时间: {next_run}, 触发器: {job.trigger}")

# 初始化所有任务的调度
def init_scheduler():
    logger.info("初始化定时任务调度")
    db = SessionLocal()
    try:
        plans = db.query(DCAPlan).filter(DCAPlan.status == "enabled").all()
        for plan in plans:
            schedule_task(plan)
        logger.info(f"成功调度 {len(plans)} 个定投任务")
        # 打印所有调度任务
        print_all_jobs()
    except Exception as e:
        logger.exception(f"初始化定时任务异常: {str(e)}")
    finally:
        db.close()

# 记录资产历史数据的定时任务
@scheduler.scheduled_job('cron', hour=0, minute=0, timezone=TIMEZONE)
def record_asset_history():
    """每天零点记录一次定投策略的资产数据"""
    try:
        logger.info("开始记录定投策略资产历史数据")
        
        # 获取资产数据
        asset_data = get_assets_overview(force_refresh=True)
        
        # 如果有错误，记录日志但不保存数据
        if "error" in asset_data:
            logger.error(f"记录资产历史数据失败: {asset_data['error']}")
            return
        
        # 记录到数据库
        db = SessionLocal()
        try:
            history = AssetHistory(
                total_assets=asset_data["totalAssets"],
                total_investment=asset_data["totalInvestment"],
                total_profit=asset_data["totalProfit"],
                asset_distribution=json.dumps(asset_data["assetDistribution"]),
                recorded_at=datetime.now(TIMEZONE)
            )
            db.add(history)
            db.commit()
            logger.info("定投策略资产历史数据记录成功")
        except Exception as e:
            db.rollback()
            logger.exception(f"保存资产历史数据异常: {str(e)}")
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"记录资产历史数据任务异常: {str(e)}")

# 获取资产历史数据的API
def calculate_max_drawdown(asset_history):
    """计算最大回撤"""
    if not asset_history or len(asset_history) < 2:
        return 0
    
    # 提取总资产值
    values = [record["totalAssets"] for record in asset_history]
    
    # 计算最大回撤
    max_drawdown = 0
    peak = values[0]
    
    for value in values:
        if value > peak:
            peak = value
        else:
            drawdown = (peak - value) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
    
    return max_drawdown

@app.get("/api/assets/history")
def calculate_sharpe_ratio(result, risk_free_rate=0.02):
    """计算夏普比率
    
    参数:
        result: 资产历史数据列表
        risk_free_rate: 无风险利率，默认为2%
    
    返回:
        夏普比率，如果无法计算则返回0
    """
    if len(result) <= 1:
        return 0
    
    try:
        import numpy as np
        
        # 提取总资产值
        values = [record["totalAssets"] for record in result]
        
        # 计算日收益率
        returns = [(values[i] - values[i-1]) / values[i-1] if values[i-1] > 0 else 0 
                for i in range(1, len(values))]
        
        # 计算平均日收益率
        avg_return = np.mean(returns)
        
        # 计算日收益率标准差
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0
        
        # 计算日无风险利率
        daily_risk_free = risk_free_rate / 252
        
        # 计算夏普比率
        sharpe = (avg_return - daily_risk_free) / std_return
        
        # 年化夏普比率
        annual_sharpe = sharpe * (252 ** 0.5)
        
        return annual_sharpe
    except Exception as e:
        logger.warning(f"计算夏普比率异常: {str(e)}")
        return 0

def get_asset_history(days: int = 30, include_metrics: bool = False):
    """获取指定天数的资产历史数据，可选择是否包含风险指标"""
    db = next(get_db())
    
    try:
        # 计算起始日期
        end_date = datetime.now(TIMEZONE)
        start_date = end_date - timedelta(days=days)
        
        # 查询历史数据
        history_records = db.query(AssetHistory).filter(
            AssetHistory.recorded_at >= start_date,
            AssetHistory.recorded_at <= end_date
        ).order_by(AssetHistory.recorded_at.asc()).all()
        
        # 格式化结果
        result = []
        for record in history_records:
            result.append({
                "date": record.recorded_at.isoformat(),
                "totalAssets": record.total_assets,
                "totalInvestment": record.total_investment,
                "totalProfit": record.total_profit,
                "assetDistribution": json.loads(record.asset_distribution) if record.asset_distribution else []
            })
        
        # 如果需要包含风险指标
        if include_metrics and result:
            # 计算最大回撤
            max_drawdown = calculate_max_drawdown(result)
            
            # 计算波动率（标准差）
            volatility = 0
            if len(result) > 1:
                values = [record["totalAssets"] for record in result]
                if len(values) > 1:
                    import numpy as np
                    try:
                        # 计算日收益率
                        returns = [(values[i] - values[i-1]) / values[i-1] if values[i-1] > 0 else 0 
                                for i in range(1, len(values))]
                        # 计算标准差
                        volatility = float(np.std(returns))
                        # 年化波动率（假设252个交易日）
                        volatility = volatility * (252 ** 0.5)
                    except Exception as e:
                        logger.warning(f"计算波动率异常: {str(e)}")
            
            # 计算夏普比率
            sharpe_ratio = calculate_sharpe_ratio(result)
            
            # 添加风险指标到返回结果
            return {
                "history": result,
                "metrics": {
                    "maxDrawdown": max_drawdown,
                    "volatility": volatility,
                    "sharpeRatio": sharpe_ratio
                }
            }
        
        return result
    except Exception as e:
        logger.exception(f"获取资产历史数据异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取资产历史数据失败: {str(e)}")

# 启动时初始化调度器
@app.on_event("startup")
def startup_event():
    logger.info("服务启动，初始化调度器")
    init_scheduler()
    
    # 启动时记录一次资产数据
    try:
        logger.info("启动时记录资产数据")
        # 使用线程执行，避免阻塞启动过程
        import threading
        threading.Thread(target=record_asset_history).start()
    except Exception as e:
        logger.exception(f"启动时记录资产数据异常: {str(e)}")

# 添加手动执行任务接口
@app.post("/api/dca-plan/{plan_id}/execute")
def manual_execute_plan(plan_id: int):
    db = next(get_db())
    db_plan = db.query(DCAPlan).filter(DCAPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    if db_plan.status != "enabled":
        raise HTTPException(status_code=400, detail="Cannot execute disabled plan")
    
    logger.info(f"手动执行任务 {plan_id}")
    execute_dca_task(plan_id)
    
    return {"message": f"任务 {plan_id} 已手动执行"}

# 定投计划相关接口
@app.post("/api/dca-plan", response_model=DCAPlanOut)
def create_dca_plan(plan: DCAPlanCreate):
    db = next(get_db())
    db_plan = DCAPlan(**plan.dict(), status="enabled")
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    
    # 调度任务
    schedule_task(db_plan)
    logger.info(f"创建新任务: {db_plan.id}, 币种: {db_plan.symbol}, 金额: {db_plan.amount}, 频率: {db_plan.frequency}")
    
    # 打印所有调度任务
    print_all_jobs()
    
    return db_plan

@app.get("/api/dca-plan", response_model=List[DCAPlanOut])
def list_dca_plans():
    db = next(get_db())
    plans = db.query(DCAPlan).all()
    return plans

@app.put("/api/dca-plan/{plan_id}", response_model=DCAPlanOut)
def update_dca_plan(plan_id: int, plan: DCAPlanCreate):
    db = next(get_db())
    db_plan = db.query(DCAPlan).filter(DCAPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    logger.info(f"更新任务 {plan_id}: 币种: {plan.symbol}, 金额: {plan.amount}, 频率: {plan.frequency}")
    
    # 保存原始时间信息，用于检测是否修改了时间
    original_time = db_plan.time
    original_frequency = db_plan.frequency
    original_day_of_week = db_plan.day_of_week
    original_month_days = db_plan.month_days
    
    for key, value in plan.dict().items():
        setattr(db_plan, key, value)
    
    # 如果修改了时间，清除今天的执行记录标记，允许在新时间点再次执行
    time_changed = (
        original_time != db_plan.time or 
        original_frequency != db_plan.frequency or 
        original_day_of_week != db_plan.day_of_week or 
        original_month_days != db_plan.month_days
    )
    
    # 如果时间有变化，添加一个标记字段，表示允许在同一天再次执行
    if time_changed:
        # 添加一个特殊的字段到数据库，标记这个任务已经被修改过时间
        db_plan.last_time_update = datetime.now(TIMEZONE)
        logger.info(f"任务 {plan_id} 时间已修改，允许在新时间点再次执行")
    
    db.commit()
    db.refresh(db_plan)
    
    # 更新调度，如果时间设置有变化，则检查是否需要立即执行
    schedule_task(db_plan, check_missed=time_changed)
    
    # 打印所有调度任务
    print_all_jobs()
    
    return db_plan

@app.delete("/api/dca-plan/{plan_id}")
def delete_dca_plan(plan_id: int):
    db = next(get_db())
    db_plan = db.query(DCAPlan).filter(DCAPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # 移除调度
    job_id = f"dca_task_{plan_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"移除任务调度 {job_id}")
    
    # 如果是月度任务，还需要移除每个日期的单独任务
    if db_plan.frequency == "monthly" and db_plan.month_days:
        try:
            month_days = json.loads(db_plan.month_days)
            for day in month_days:
                day_job_id = f"dca_task_{plan_id}_day_{day}"
                if scheduler.get_job(day_job_id):
                    scheduler.remove_job(day_job_id)
                    logger.info(f"移除月度任务调度 {day_job_id}")
        except (json.JSONDecodeError, ValueError):
            pass
    
    # 删除计划
    logger.info(f"删除任务 {plan_id}")
    db.delete(db_plan)
    db.commit()
    
    # 打印所有调度任务
    print_all_jobs()
    
    return {"ok": True}

@app.put("/api/dca-plan/{plan_id}/status")
def update_plan_status(plan_id: int, status: str = Body(..., embed=True)):
    if status not in ["enabled", "disabled"]:
        raise HTTPException(status_code=400, detail="Status must be 'enabled' or 'disabled'")
    
    db = next(get_db())
    db_plan = db.query(DCAPlan).filter(DCAPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    logger.info(f"更新任务 {plan_id} 状态为 {status}")
    db_plan.status = status
    db.commit()
    
    # 更新调度
    schedule_task(db_plan)
    
    # 打印所有调度任务
    print_all_jobs()
    
    return {"id": plan_id, "status": status}

# 获取交易记录
@app.get("/api/transactions")
@app.get("/api/transactions")
def get_transactions(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    direction: Optional[str] = None,
    limit: int = 100
):
    db = next(get_db())
    
    # 联表查询，获取任务名称
    query = db.query(
        Transaction.id,
        Transaction.plan_id,
        Transaction.symbol,
        Transaction.amount,
        Transaction.direction,
        Transaction.status,
        Transaction.response,
        Transaction.executed_at,
        DCAPlan.title.label('plan_title')
    ).outerjoin(DCAPlan, Transaction.plan_id == DCAPlan.id)
    
    if symbol:
        query = query.filter(Transaction.symbol == symbol)
    
    if start_date:
        start = datetime.fromisoformat(start_date)
        query = query.filter(Transaction.executed_at >= start)
    
    if end_date:
        end = datetime.fromisoformat(end_date)
        query = query.filter(Transaction.executed_at <= end)
    
    if direction:
        query = query.filter(Transaction.direction == direction)
    
    transactions = query.order_by(Transaction.executed_at.desc()).limit(limit).all()
    
    # 计算每个任务的执行次数并解析交易详情
    result = []
    for transaction in transactions:
        # 计算该任务在此交易之前的执行次数
        execution_count = db.query(Transaction).filter(
            Transaction.plan_id == transaction.plan_id,
            Transaction.executed_at <= transaction.executed_at,
            Transaction.status == "success"
        ).count()
        
        # 解析交易响应获取成交价格和数量
        trade_price = None
        trade_quantity = None
        
        if transaction.status == "success" and transaction.response:
            try:
                response_data = json.loads(transaction.response)
                logger.info(f"解析交易记录 ID: {transaction.id}, 响应数据: {response_data}")
                
                # 检查是否有成交详情
                if 'fill_details' in response_data and response_data['fill_details']:
                    fill_data = response_data['fill_details']
                    # 成交价格和数量
                    if 'fillPx' in fill_data and fill_data['fillPx']:
                        try:
                            trade_price = float(fill_data['fillPx'])
                        except (ValueError, TypeError):
                            pass
                            
                    if 'fillSz' in fill_data and fill_data['fillSz']:
                        try:
                            trade_quantity = float(fill_data['fillSz'])
                        except (ValueError, TypeError):
                            pass
                
                # 如果没有fill_details或者解析失败，尝试从order_result中获取
                if (trade_price is None or trade_quantity is None) and 'order_result' in response_data:
                    if response_data['order_result'].get('data'):
                        order_data = response_data['order_result']['data'][0]
                        
                        # 尝试多种可能的字段名获取价格
                        for price_field in ['avgPx', 'px', 'fillPx']:
                            if price_field in order_data and order_data[price_field]:
                                try:
                                    trade_price = float(order_data[price_field])
                                    break
                                except (ValueError, TypeError):
                                    pass
                        
                        # 尝试多种可能的字段名获取数量
                        for size_field in ['accFillSz', 'sz', 'fillSz']:
                            if size_field in order_data and order_data[size_field]:
                                try:
                                    trade_quantity = float(order_data[size_field])
                                    break
                                except (ValueError, TypeError):
                                    pass
                
                # 如果是市价买单，可能需要特殊处理
                # 市价买单中，sz表示买入金额，而不是买入数量
                if trade_price and trade_price > 0 and transaction.direction == "buy" and trade_quantity is None:
                    # 如果有价格但没有数量，尝试用金额除以价格计算数量
                    if 'order_result' in response_data and response_data['order_result'].get('data'):
                        order_data = response_data['order_result']['data'][0]
                        if 'sz' in order_data and order_data['sz']:
                            try:
                                amount = float(order_data['sz'])
                                trade_quantity = amount / trade_price
                            except (ValueError, TypeError, ZeroDivisionError):
                                pass
                
                # 如果是市价卖单，可能需要特殊处理
                # 市价卖单中，sz表示卖出数量
                if trade_quantity and trade_quantity > 0 and transaction.direction == "sell" and trade_price is None:
                    # 如果有数量但没有价格，尝试用金额除以数量计算价格
                    if 'order_result' in response_data and response_data['order_result'].get('data'):
                        order_data = response_data['order_result']['data'][0]
                        if 'sz' in order_data and order_data['sz']:
                            try:
                                amount = float(transaction.amount)  # 使用交易记录中的金额
                                trade_price = amount / trade_quantity
                            except (ValueError, TypeError, ZeroDivisionError):
                                pass
                
                # 如果仍然没有获取到价格和数量，尝试使用交易记录中的金额和当前市场价格估算
                if trade_price is None or trade_quantity is None:
                    # 这里我们可以添加获取当前市场价格的逻辑，但为了简单起见，暂时不实现
                    pass
                        
            except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
                logger.warning(f"解析交易响应失败: {str(e)}, 响应数据: {transaction.response}")
                # 如果解析失败，保持为None
                pass
            
            # 记录解析结果
            logger.info(f"交易记录 ID: {transaction.id}, 解析结果: 价格={trade_price}, 数量={trade_quantity}")
        
        result.append({
            "id": transaction.id,
            "plan_id": transaction.plan_id,
            "plan_title": transaction.plan_title or f"任务{transaction.plan_id}",
            "execution_count": execution_count,
            "symbol": transaction.symbol,
            "amount": transaction.amount,
            "direction": transaction.direction,
            "status": transaction.status,
            "response": transaction.response,
            "executed_at": transaction.executed_at,
            "trade_price": trade_price,
            "trade_quantity": trade_quantity
        })
    
    return result

# 配置中心相关接口
@app.post("/api/config/api")
def save_api_config(config: ApiConfig):
    db = next(get_db())
    
    # 检查是否已有配置
    existing_config = db.query(UserConfig).first()
    if existing_config:
        # 更新现有配置
        existing_config.api_key = encrypt_text(config.api_key)
        existing_config.secret_key = encrypt_text(config.secret_key)
        existing_config.passphrase = encrypt_text(config.passphrase)
        existing_config.updated_at = datetime.now(TIMEZONE)
    else:
        # 创建新配置
        new_config = UserConfig(
            api_key=encrypt_text(config.api_key),
            secret_key=encrypt_text(config.secret_key),
            passphrase=encrypt_text(config.passphrase)
        )
        db.add(new_config)
    
    db.commit()
    return {"message": "API 配置保存成功"}

@app.get("/api/config/api", response_model=ConfigResponse)
def get_api_config():
    db = next(get_db())
    config = db.query(UserConfig).first()
    
    if not config:
        return ConfigResponse()
    
    return ConfigResponse(
        api_key=decrypt_text(config.api_key),
        secret_key=decrypt_text(config.secret_key),
        passphrase=decrypt_text(config.passphrase),
        selected_coins=json.loads(config.selected_coins) if config.selected_coins else []
    )

@app.post("/api/config/coins")
def save_coin_config(config: CoinConfig):
    db = next(get_db())
    
    # 检查是否已有配置
    existing_config = db.query(UserConfig).first()
    if existing_config:
        # 更新现有配置
        existing_config.selected_coins = json.dumps(config.selected_coins)
        existing_config.updated_at = datetime.now(TIMEZONE)
    else:
        # 创建新配置
        new_config = UserConfig(selected_coins=json.dumps(config.selected_coins))
        db.add(new_config)
    
    db.commit()
    return {"message": "币种配置保存成功"}

@app.get("/api/config/coins", response_model=List[str])
def get_coin_config():
    db = next(get_db())
    config = db.query(UserConfig).first()
    
    if not config or not config.selected_coins:
        return []
    
    return json.loads(config.selected_coins)

@app.get("/api/config/popular-coins", response_model=List[str])
def get_popular_coins(limit: int = 100):
    """获取OKX热门币种列表"""
    try:
        # 使用公共API获取热门币种（无需API密钥）
        popular_coins = get_popular_coins_public(limit)
        return popular_coins
    except Exception as e:
        logger.exception(f"获取热门币种异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取热门币种失败: {str(e)}")

@app.post("/api/config/test")
def test_api_connection(config: ApiConfig = Body(...)):
    """测试 OKX API 连接，前端传递 ApiConfig 参数"""
    try:
        client = OKXClient(
            api_key=config.api_key,
            secret_key=config.secret_key,
            passphrase=config.passphrase
        )
        result = client.test_connection()
        if result.get('code') == '0':
            return {"success": True, "message": "API 连接成功"}
        else:
            return {
                "success": False,
                "message": f"API 连接失败: {result.get('msg', '未知错误')}",
                "raw": result
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"后端异常: {str(e)}"
        }

# 获取资产概览
# 资产数据缓存
assets_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 300  # 缓存有效期，单位秒
}

def calculate_dca_assets_and_investment(db, client):
    """计算定投策略的资产价值、投入和收益"""
    # 获取所有成功的交易记录
    transactions = db.query(Transaction).filter(Transaction.status == "success").all()
    
    # 按币种统计买入和卖出数量
    coin_balances = {}  # 格式: {symbol: {'bought': 数量, 'sold': 数量, 'investment': 投入金额}}
    total_investment = 0
    
    for tx in transactions:
        symbol = tx.symbol.split('-')[0]  # 例如从"BTC-USDT"提取"BTC"
        
        if symbol not in coin_balances:
            coin_balances[symbol] = {'bought': 0, 'sold': 0, 'investment': 0}
        
        try:
            # 解析交易响应获取实际成交数量和金额
            if tx.response:
                response_data = json.loads(tx.response)
                
                # 检查是否有成交详情
                if 'fill_details' in response_data and response_data['fill_details']:
                    fill_data = response_data['fill_details']
                    
                    # 获取成交数量
                    if 'fillSz' in fill_data and fill_data['fillSz']:
                        try:
                            fill_size = float(fill_data['fillSz'])
                            
                            # 买入交易增加持仓数量和投入金额
                            if tx.direction == "buy":
                                coin_balances[symbol]['bought'] += fill_size
                                
                                # 获取成交金额
                                if 'fillAmt' in fill_data and fill_data['fillAmt']:
                                    try:
                                        fill_amount = float(fill_data['fillAmt'])
                                        coin_balances[symbol]['investment'] += fill_amount
                                        total_investment += fill_amount
                                    except (ValueError, TypeError):
                                        # 如果无法获取成交金额，使用订单金额
                                        coin_balances[symbol]['investment'] += tx.amount
                                        total_investment += tx.amount
                                else:
                                    coin_balances[symbol]['investment'] += tx.amount
                                    total_investment += tx.amount
                            
                            # 卖出交易减少持仓数量和投入金额
                            elif tx.direction == "sell":
                                coin_balances[symbol]['sold'] += fill_size
                                
                                # 获取成交金额
                                if 'fillAmt' in fill_data and fill_data['fillAmt']:
                                    try:
                                        fill_amount = float(fill_data['fillAmt'])
                                        coin_balances[symbol]['investment'] -= fill_amount
                                        total_investment -= fill_amount
                                    except (ValueError, TypeError):
                                        # 如果无法获取成交金额，使用订单金额
                                        coin_balances[symbol]['investment'] -= tx.amount
                                        total_investment -= tx.amount
                                else:
                                    coin_balances[symbol]['investment'] -= tx.amount
                                    total_investment -= tx.amount
                                
                        except (ValueError, TypeError):
                            # 如果无法解析成交数量，使用默认逻辑
                            if tx.direction == "buy":
                                coin_balances[symbol]['investment'] += tx.amount
                                total_investment += tx.amount
                            elif tx.direction == "sell":
                                coin_balances[symbol]['investment'] -= tx.amount
                                total_investment -= tx.amount
                    else:
                        # 如果无法获取成交数量，使用默认逻辑
                        if tx.direction == "buy":
                            coin_balances[symbol]['investment'] += tx.amount
                            total_investment += tx.amount
                        elif tx.direction == "sell":
                            coin_balances[symbol]['investment'] -= tx.amount
                            total_investment -= tx.amount
                else:
                    # 如果没有成交详情，使用默认逻辑
                    if tx.direction == "buy":
                        coin_balances[symbol]['investment'] += tx.amount
                        total_investment += tx.amount
                    elif tx.direction == "sell":
                        coin_balances[symbol]['investment'] -= tx.amount
                        total_investment -= tx.amount
            else:
                # 如果没有响应数据，使用默认逻辑
                if tx.direction == "buy":
                    coin_balances[symbol]['investment'] += tx.amount
                    total_investment += tx.amount
                elif tx.direction == "sell":
                    coin_balances[symbol]['investment'] -= tx.amount
                    total_investment -= tx.amount
                
        except (json.JSONDecodeError, KeyError) as e:
            # 如果解析失败，使用默认逻辑
            if tx.direction == "buy":
                coin_balances[symbol]['investment'] += tx.amount
                total_investment += tx.amount
            elif tx.direction == "sell":
                coin_balances[symbol]['investment'] -= tx.amount
                total_investment -= tx.amount
    
    # 计算每种币的净持仓数量
    net_balances = {}
    for symbol, data in coin_balances.items():
        net_balance = data['bought'] - data['sold']
        if net_balance > 0:
            net_balances[symbol] = net_balance
    
    # 计算当前价值
    assets = []
    total_assets = 0
    
    for symbol, balance in net_balances.items():
        if balance > 0:
            # 获取当前价格
            ticker_result = client.get_ticker(f"{symbol}-USDT")
            if ticker_result.get('code') == '0' and ticker_result.get('data'):
                price = float(ticker_result['data'][0].get('last', 0))
                value_in_usdt = balance * price
                
                assets.append({
                    "currency": symbol,
                    "amount": balance,
                    "valueInUsdt": value_in_usdt
                })
                
                total_assets += value_in_usdt
    
    return total_assets, assets, total_investment, None

def calculate_total_investment(db):
    """计算用户的总投入金额"""
    # 获取所有成功的交易记录
    transactions = db.query(Transaction).filter(Transaction.status == "success").all()
    
    total_investment = 0
    
    for tx in transactions:
        try:
            # 解析交易响应获取实际成交金额
            if tx.response:
                response_data = json.loads(tx.response)
                
                # 检查是否有成交详情
                if 'fill_details' in response_data and response_data['fill_details']:
                    fill_data = response_data['fill_details']
                    
                    # 对于买入交易，使用实际成交金额
                    if tx.direction == "buy":
                        if 'fillAmt' in fill_data and fill_data['fillAmt']:
                            try:
                                fill_amount = float(fill_data['fillAmt'])
                                total_investment += fill_amount
                                continue
                            except (ValueError, TypeError):
                                pass
                    
                    # 对于卖出交易，使用实际成交金额，从总投入中减去
                    elif tx.direction == "sell":
                        if 'fillAmt' in fill_data and fill_data['fillAmt']:
                            try:
                                fill_amount = float(fill_data['fillAmt'])
                                total_investment -= fill_amount
                                continue
                            except (ValueError, TypeError):
                                pass
            
            # 如果无法从成交详情获取，则使用交易记录中的金额
            if tx.direction == "buy":
                total_investment += tx.amount
            elif tx.direction == "sell":
                total_investment -= tx.amount
                
        except (json.JSONDecodeError, KeyError) as e:
            # 如果解析失败，使用交易记录中的金额
            if tx.direction == "buy":
                total_investment += tx.amount
            elif tx.direction == "sell":
                total_investment -= tx.amount
    
    return total_investment

def calculate_asset_distribution(assets, total_assets):
    """计算资产分布百分比"""
    asset_distribution = []
    
    for asset in assets:
        if total_assets > 0:
            percentage = (asset["valueInUsdt"] / total_assets) * 100
        else:
            percentage = 0
        
        asset_distribution.append({
            "currency": asset["currency"],
            "amount": asset["amount"],
            "valueInUsdt": asset["valueInUsdt"],
            "percentage": percentage
        })
    
    # 按价值排序
    asset_distribution.sort(key=lambda x: x["valueInUsdt"], reverse=True)
    
    return asset_distribution

def get_strategy_info(db):
    """获取定投策略的基本信息，如开始时间和执行次数"""
    try:
        # 获取第一笔成功交易的时间作为策略开始时间
        first_transaction = db.query(Transaction).filter(
            Transaction.status == "success"
        ).order_by(Transaction.executed_at.asc()).first()
        
        # 获取成功交易的总数作为执行次数
        execution_count = db.query(Transaction).filter(
            Transaction.status == "success"
        ).count()
        
        # 计算策略运行天数
        days_running = 0
        if first_transaction:
            start_date = first_transaction.executed_at.replace(tzinfo=None)
            current_date = datetime.now()
            days_running = (current_date - start_date).days
            if days_running < 1:
                days_running = 1  # 至少为1天，避免除零错误
        
        return {
            "startDate": first_transaction.executed_at.isoformat() if first_transaction else None,
            "executionCount": execution_count,
            "daysRunning": days_running
        }
    except Exception as e:
        logger.exception(f"获取策略信息异常: {str(e)}")
        return {
            "startDate": None,
            "executionCount": 0
        }

def calculate_total_investment(db):
    """此函数已被替换为calculate_dca_assets_and_investment，保留此函数签名以避免引用错误"""
    logger.warning("calculate_total_investment函数已被弃用，请使用calculate_dca_assets_and_investment")
    return 0

@app.get("/api/assets/overview")
def get_assets_overview(force_refresh: bool = False):
    """获取定投策略的资产概览数据，包括总资产、总投入、总收益和资产分布"""
    global assets_cache
    
    # 检查缓存是否有效
    current_time = time.time()
    if not force_refresh and assets_cache["data"] and (current_time - assets_cache["timestamp"]) < assets_cache["ttl"]:
        return assets_cache["data"]
    
    db = next(get_db())
    config = db.query(UserConfig).first()
    
    if not config:
        return {
            "totalAssets": 0,
            "totalInvestment": 0,
            "totalProfit": 0,
            "assetDistribution": [],
            "lastUpdated": datetime.now(TIMEZONE).isoformat()
        }
    
    try:
        # 解密API密钥
        api_key = decrypt_text(config.api_key)
        secret_key = decrypt_text(config.secret_key)
        passphrase = decrypt_text(config.passphrase)
        
        if not api_key or not secret_key or not passphrase:
            return {
                "totalAssets": 0,
                "totalInvestment": 0,
                "totalProfit": 0,
                "assetDistribution": [],
                "error": "API配置不完整",
                "lastUpdated": datetime.now(TIMEZONE).isoformat()
            }
        
        # 创建OKX客户端
        client = OKXClient(api_key=api_key, secret_key=secret_key, passphrase=passphrase)
        
        # 1. 计算定投策略的资产价值、投入和收益
        total_assets, assets, total_investment, error = calculate_dca_assets_and_investment(db, client)
        if error:
            return {
                "totalAssets": 0,
                "totalInvestment": 0,
                "totalProfit": 0,
                "assetDistribution": [],
                "error": error,
                "lastUpdated": datetime.now(TIMEZONE).isoformat()
            }
        
        # 2. 计算总收益和年化收益率
        total_profit = total_assets - total_investment
        
        # 计算年化收益率
        annualized_return = 0
        strategy_info = get_strategy_info(db)
        days_running = strategy_info.get('daysRunning', 0)
        
        if days_running > 0 and total_investment > 0:
            # 计算总收益率
            total_return_rate = total_profit / total_investment
            # 转换为年化收益率: (1 + r)^(365/days) - 1
            annualized_return = ((1 + total_return_rate) ** (365 / days_running)) - 1
        
        # 3. 计算资产分布
        full_asset_distribution = calculate_asset_distribution(assets, total_assets)
        
        # 简化资产分布数据，只返回前端需要的字段
        simplified_distribution = []
        for asset in full_asset_distribution:
            simplified_distribution.append({
                "currency": asset["currency"],
                "percentage": asset["percentage"]
            })
        
        # 获取策略信息
        strategy_info = get_strategy_info(db)
        
        # 构建结果
        result = {
            "totalAssets": total_assets,
            "totalInvestment": total_investment,
            "totalProfit": total_profit,
            "annualizedReturn": annualized_return,
            "assetDistribution": simplified_distribution,
            "strategyInfo": strategy_info,
            "lastUpdated": datetime.now(TIMEZONE).isoformat()
        }
        
        # 更新缓存
        assets_cache["data"] = result
        assets_cache["timestamp"] = current_time
        
        return result
    
    except Exception as e:
        logger.exception(f"获取资产概览异常: {str(e)}")
        return {
            "totalAssets": 0,
            "totalInvestment": 0,
            "totalProfit": 0,
            "assetDistribution": [],
            "error": f"服务器异常: {str(e)}",
            "lastUpdated": datetime.now(TIMEZONE).isoformat()
        }
