"""
配置管理服务
负责处理API配置、币种配置等相关业务逻辑
"""
import json
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from models import UserConfig, encrypt_text, decrypt_text
from okx_api import get_popular_coins_public

logger = logging.getLogger(__name__)

class ConfigService:
    """配置管理服务类"""
    
    def __init__(self, session_local):
        """
        初始化配置服务
        
        Args:
            session_local: SQLAlchemy会话工厂
        """
        self.SessionLocal = session_local
    
    def save_api_config(self, api_key: str, secret_key: str, passphrase: str) -> Dict:
        """
        保存API配置
        
        Args:
            api_key: API密钥
            secret_key: 密钥
            passphrase: 密码短语
            
        Returns:
            操作结果
        """
        try:
            db = self.SessionLocal()
            try:
                # 加密敏感信息
                encrypted_api_key = encrypt_text(api_key)
                encrypted_secret_key = encrypt_text(secret_key)
                encrypted_passphrase = encrypt_text(passphrase)
                
                # 查找现有配置
                user_config = db.query(UserConfig).first()
                if user_config:
                    user_config.api_key = encrypted_api_key
                    user_config.secret_key = encrypted_secret_key
                    user_config.passphrase = encrypted_passphrase
                else:
                    user_config = UserConfig(
                        api_key=encrypted_api_key,
                        secret_key=encrypted_secret_key,
                        passphrase=encrypted_passphrase
                    )
                    db.add(user_config)
                
                db.commit()
                logger.info("API配置保存成功")
                return {"message": "API配置保存成功", "success": True}
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"保存API配置失败: {str(e)}")
            return {"message": f"保存失败: {str(e)}", "success": False}
    
    def get_api_config(self) -> Dict:
        """
        获取API配置
        
        Returns:
            API配置信息
        """
        try:
            db = self.SessionLocal()
            try:
                config = db.query(UserConfig).first()
                if config:
                    return {
                        "api_key": decrypt_text(config.api_key) if config.api_key else "",
                        "secret_key": decrypt_text(config.secret_key) if config.secret_key else "",
                        "passphrase": decrypt_text(config.passphrase) if config.passphrase else "",
                        "selected_coins": json.loads(config.selected_coins) if config.selected_coins else []
                    }
                else:
                    return {
                        "api_key": "",
                        "secret_key": "",
                        "passphrase": "",
                        "selected_coins": []
                    }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取API配置失败: {str(e)}")
            return {
                "api_key": "",
                "secret_key": "",
                "passphrase": "",
                "selected_coins": []
            }
    
    def save_coin_config(self, selected_coins: List[str]) -> Dict:
        """
        保存币种配置
        
        Args:
            selected_coins: 选中的币种列表
            
        Returns:
            操作结果
        """
        try:
            db = self.SessionLocal()
            try:
                # 查找现有配置
                user_config = db.query(UserConfig).first()
                if user_config:
                    user_config.selected_coins = json.dumps(selected_coins)
                else:
                    user_config = UserConfig(selected_coins=json.dumps(selected_coins))
                    db.add(user_config)
                
                db.commit()
                logger.info(f"币种配置保存成功: {len(selected_coins)}个币种")
                return {"message": "币种配置保存成功", "success": True}
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"保存币种配置失败: {str(e)}")
            return {"message": f"保存失败: {str(e)}", "success": False}
    
    def get_coin_config(self) -> List[str]:
        """
        获取币种配置
        
        Returns:
            选中的币种列表
        """
        try:
            db = self.SessionLocal()
            try:
                config = db.query(UserConfig).first()
                if config and config.selected_coins:
                    return json.loads(config.selected_coins)
                else:
                    return []
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取币种配置失败: {str(e)}")
            return []
    
    def get_popular_coins(self, limit: int = 100) -> List[str]:
        """
        获取热门币种
        
        Args:
            limit: 返回数量限制
            
        Returns:
            热门币种列表
        """
        try:
            coins = get_popular_coins_public(limit)
            logger.info(f"获取热门币种成功: {len(coins)}个")
            return coins
        except Exception as e:
            logger.error(f"获取热门币种失败: {str(e)}")
            return []
    
    def test_api_connection(self, api_key: str, secret_key: str, passphrase: str) -> Dict:
        """
        测试API连接
        
        Args:
            api_key: API密钥
            secret_key: 密钥
            passphrase: 密码短语
            
        Returns:
            测试结果
        """
        try:
            if not all([api_key, secret_key, passphrase]):
                return {"success": False, "message": "API配置不完整"}
            
            # 导入客户端创建函数
            from main import create_okx_client
            
            # 创建客户端并测试连接
            client = create_okx_client(api_key, secret_key, passphrase)
            result = client.get_trading_balance()
            
            if result.get('code') == '0':
                logger.info("API连接测试成功")
                return {"success": True, "message": "API连接测试成功"}
            else:
                error_msg = result.get('msg', '未知错误')
                logger.warning(f"API连接测试失败: {error_msg}")
                return {"success": False, "message": f"API连接测试失败: {error_msg}"}
                
        except Exception as e:
            logger.error(f"API连接测试异常: {str(e)}")
            return {"success": False, "message": f"连接测试失败: {str(e)}"}
    
    def get_decrypted_api_config(self) -> Optional[Dict[str, str]]:
        """
        获取解密后的API配置（用于内部服务调用）
        
        Returns:
            解密后的API配置，如果配置不存在或不完整则返回None
        """
        try:
            db = self.SessionLocal()
            try:
                config = db.query(UserConfig).first()
                if not config:
                    return None
                
                api_key = decrypt_text(config.api_key) if config.api_key else ""
                secret_key = decrypt_text(config.secret_key) if config.secret_key else ""
                passphrase = decrypt_text(config.passphrase) if config.passphrase else ""
                
                if not all([api_key, secret_key, passphrase]):
                    return None
                
                return {
                    "api_key": api_key,
                    "secret_key": secret_key,
                    "passphrase": passphrase
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取解密API配置失败: {str(e)}")
            return None