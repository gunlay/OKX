from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import base64
import os
from cryptography.fernet import Fernet

Base = declarative_base()

class UserConfig(Base):
    __tablename__ = "user_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(Text)  # 加密存储
    secret_key = Column(Text)  # 加密存储
    passphrase = Column(Text)  # 加密存储
    selected_coins = Column(Text)  # JSON 字符串存储
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 定投计划模型
class DCAPlan(Base):
    __tablename__ = "dca_plans"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)  # 任务标题
    symbol = Column(String, index=True)
    amount = Column(Float)
    frequency = Column(String)  # daily, weekly, monthly
    day_of_week = Column(Integer, nullable=True)  # 0=Monday
    month_days = Column(Text, nullable=True)  # 存储每月的多个日期，JSON字符串
    time = Column(String)  # "10:00"
    direction = Column(String, default="buy")  # buy, sell
    status = Column(String, default="enabled")  # enabled, disabled
    last_time_update = Column(DateTime, nullable=True)  # 记录最后一次时间修改，用于判断是否允许同一天再次执行
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 交易记录模型
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, index=True)
    symbol = Column(String, index=True)
    amount = Column(Float)
    direction = Column(String, index=True)  # buy, sell
    status = Column(String, index=True)  # success, failed
    response = Column(Text)  # 存储API响应
    execution_count = Column(Integer, default=1)  # 任务执行次数
    executed_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 添加复合索引来优化常用查询
    __table_args__ = (
        Index('idx_plan_executed_at', 'plan_id', 'executed_at'),
        Index('idx_status_executed_at', 'status', 'executed_at'),
        Index('idx_symbol_direction_status', 'symbol', 'direction', 'status'),
        Index('idx_plan_status_executed', 'plan_id', 'status', 'executed_at'),
    )

# 资产历史记录模型
class AssetHistory(Base):
    __tablename__ = "asset_history"
    id = Column(Integer, primary_key=True, index=True)
    total_assets = Column(Float)
    total_investment = Column(Float)
    total_profit = Column(Float)
    asset_distribution = Column(Text)  # JSON字符串存储
    recorded_at = Column(DateTime, default=datetime.utcnow)

# 加密密钥管理
def get_encryption_key():
    """获取或生成加密密钥"""
    key_file = "encryption_key.key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
        return key

def encrypt_text(text):
    """加密文本"""
    if not text:
        return ""
    key = get_encryption_key()
    f = Fernet(key)
    return f.encrypt(text.encode()).decode()

def decrypt_text(encrypted_text):
    """解密文本"""
    if not encrypted_text:
        return ""
    key = get_encryption_key()
    f = Fernet(key)
    return f.decrypt(encrypted_text.encode()).decode()