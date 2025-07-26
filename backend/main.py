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
from fastapi.middleware.cors import CORSMiddleware

# 导入自定义模块
from models import Base, UserConfig, encrypt_text, decrypt_text
from okx_api import OKXClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dca_service.log')
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
scheduler = BackgroundScheduler()
scheduler.start()
lock = threading.Lock()

# 创建数据库表
Base.metadata.create_all(bind=engine)

# Pydantic 模型
class DCAPlanCreate(BaseModel):
    symbol: str
    amount: float
    frequency: str
    day_of_week: Optional[int] = None
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
            order_result = client.place_order(
                symbol=plan.symbol,
                side=side,
                order_type="market",
                size=str(plan.amount)
            )
            
            # 记录执行结果
            logger.info(f"任务 {plan_id} 执行结果: {order_result}")
            
            # 创建交易记录
            if order_result.get('code') == '0':
                # 成功执行
                transaction = Transaction(
                    plan_id=plan.id,
                    symbol=plan.symbol,
                    amount=plan.amount,
                    direction=plan.direction or "buy",
                    status="success",
                    response=json.dumps(order_result),
                    executed_at=datetime.utcnow()
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
                    executed_at=datetime.utcnow()
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
def schedule_task(plan):
    job_id = f"dca_task_{plan.id}"
    
    # 如果已存在任务，先移除
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    # 如果任务已禁用，不再调度
    if plan.status != "enabled":
        logger.info(f"任务 {plan.id} 已禁用，不再调度")
        return
    
    # 解析时间
    hour, minute = plan.time.split(":")
    
    # 根据频率创建触发器
    if plan.frequency == "daily":
        trigger = CronTrigger(hour=hour, minute=minute)
        logger.info(f"任务 {plan.id} 调度为每天 {plan.time}")
    elif plan.frequency == "weekly" and plan.day_of_week is not None:
        trigger = CronTrigger(day_of_week=plan.day_of_week, hour=hour, minute=minute)
        logger.info(f"任务 {plan.id} 调度为每周 {plan.day_of_week} {plan.time}")
    elif plan.frequency == "monthly":
        trigger = CronTrigger(day=1, hour=hour, minute=minute)
        logger.info(f"任务 {plan.id} 调度为每月 {plan.time}")
    else:
        logger.error(f"任务 {plan.id} 频率配置错误: {plan.frequency}")
        return
    
    # 添加任务
    scheduler.add_job(
        execute_dca_task,
        trigger=trigger,
        args=[plan.id],
        id=job_id,
        replace_existing=True
    )
    
    # 添加一次性任务，用于测试
    test_time = datetime.now() + timedelta(seconds=30)
    test_job_id = f"test_dca_task_{plan.id}"
    if scheduler.get_job(test_job_id):
        scheduler.remove_job(test_job_id)
    
    logger.info(f"添加测试任务 {test_job_id}，将在30秒后执行")
    scheduler.add_job(
        execute_dca_task,
        'date',
        run_date=test_time,
        args=[plan.id],
        id=test_job_id
    )

# 初始化所有任务的调度
def init_scheduler():
    logger.info("初始化定时任务调度")
    db = SessionLocal()
    try:
        plans = db.query(DCAPlan).filter(DCAPlan.status == "enabled").all()
        for plan in plans:
            schedule_task(plan)
        logger.info(f"成功调度 {len(plans)} 个定投任务")
    except Exception as e:
        logger.exception(f"初始化定时任务异常: {str(e)}")
    finally:
        db.close()

# 启动时初始化调度器
@app.on_event("startup")
def startup_event():
    logger.info("服务启动，初始化调度器")
    init_scheduler()

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
    
    for key, value in plan.dict().items():
        setattr(db_plan, key, value)
    
    db.commit()
    db.refresh(db_plan)
    
    # 更新调度
    schedule_task(db_plan)
    
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
    
    # 删除计划
    db.delete(db_plan)
    db.commit()
    
    return {"ok": True}

@app.put("/api/dca-plan/{plan_id}/status")
def update_plan_status(plan_id: int, status: str = Body(..., embed=True)):
    if status not in ["enabled", "disabled"]:
        raise HTTPException(status_code=400, detail="Status must be 'enabled' or 'disabled'")
    
    db = next(get_db())
    db_plan = db.query(DCAPlan).filter(DCAPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    db_plan.status = status
    db.commit()
    
    # 更新调度
    schedule_task(db_plan)
    
    return {"id": plan_id, "status": status}

# 获取交易记录
@app.get("/api/transactions")
def get_transactions(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    direction: Optional[str] = None,
    limit: int = 100
):
    db = next(get_db())
    query = db.query(Transaction)
    
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
    return transactions

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
        existing_config.updated_at = datetime.utcnow()
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
        existing_config.updated_at = datetime.utcnow()
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
@app.get("/api/assets/overview")
def get_assets_overview():
    db = next(get_db())
    config = db.query(UserConfig).first()
    
    if not config:
        return {
            "totalAssets": 0,
            "totalInvestment": 0,
            "totalProfit": 0,
            "assetDistribution": []
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
                "error": "API配置不完整"
            }
        
        # 创建OKX客户端
        client = OKXClient(api_key=api_key, secret_key=secret_key, passphrase=passphrase)
        
        # 获取账户余额
        balance_result = client.get_trading_balance()
        
        if balance_result.get('code') != '0':
            return {
                "totalAssets": 0,
                "totalInvestment": 0,
                "totalProfit": 0,
                "assetDistribution": [],
                "error": f"获取余额失败: {balance_result.get('msg', '未知错误')}"
            }
        
        # 计算总投资金额
        total_investment = db.query(Transaction).filter(Transaction.status == "success").count() * 100  # 假设每次投资100 USDT
        
        # 解析余额数据
        assets = []
        total_assets = 0
        
        for item in balance_result.get('data', []):
            for balance in item.get('details', []):
                currency = balance.get('ccy')
                available = float(balance.get('availBal', 0))
                
                if available > 0:
                    # 如果不是USDT，需要获取当前价格
                    if currency != 'USDT':
                        ticker_result = client.get_ticker(f"{currency}-USDT")
                        if ticker_result.get('code') == '0' and ticker_result.get('data'):
                            price = float(ticker_result['data'][0].get('last', 0))
                            value_in_usdt = available * price
                        else:
                            value_in_usdt = 0
                    else:
                        value_in_usdt = available
                    
                    assets.append({
                        "currency": currency,
                        "amount": available,
                        "valueInUsdt": value_in_usdt
                    })
                    
                    total_assets += value_in_usdt
        
        # 计算总收益
        total_profit = total_assets - total_investment
        
        # 计算资产分布
        asset_distribution = []
        for asset in assets:
            if total_assets > 0:
                percentage = (asset["valueInUsdt"] / total_assets) * 100
            else:
                percentage = 0
            
            asset_distribution.append({
                "currency": asset["currency"],
                "percentage": percentage
            })
        
        return {
            "totalAssets": total_assets,
            "totalInvestment": total_investment,
            "totalProfit": total_profit,
            "assetDistribution": asset_distribution
        }
    
    except Exception as e:
        logger.exception(f"获取资产概览异常: {str(e)}")
        return {
            "totalAssets": 0,
            "totalInvestment": 0,
            "totalProfit": 0,
            "assetDistribution": [],
            "error": f"服务器异常: {str(e)}"
        }

# 定投计划模型
class DCAPlan(Base):
    __tablename__ = "dca_plans"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    amount = Column(Float)
    frequency = Column(String)  # daily, weekly, monthly
    day_of_week = Column(Integer, nullable=True)  # 0=Monday
    time = Column(String)  # "10:00"
    direction = Column(String, default="buy")  # buy, sell
    status = Column(String, default="enabled")  # enabled, disabled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 交易记录模型
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, index=True)
    symbol = Column(String, index=True)
    amount = Column(Float)
    direction = Column(String)  # buy, sell
    status = Column(String)  # success, failed
    response = Column(Text)  # 存储API响应
    executed_at = Column(DateTime, default=datetime.utcnow) 