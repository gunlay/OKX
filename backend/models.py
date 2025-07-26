from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
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