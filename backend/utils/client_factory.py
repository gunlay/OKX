"""
OKX客户端工厂模块
负责根据环境创建合适的OKX客户端实例
"""
import logging
from .environment import is_local_environment

logger = logging.getLogger(__name__)

def create_okx_client(api_key: str, secret_key: str, passphrase: str):
    """根据环境创建合适的OKX客户端"""
    if is_local_environment():
        logger.info("检测到本地环境，使用代理客户端")
        from proxy_api import OKXProxyClient
        return OKXProxyClient(api_key, secret_key, passphrase)
    else:
        logger.info("检测到生产环境，使用直连客户端")
        from okx_api import OKXClient
        return OKXClient(api_key, secret_key, passphrase)