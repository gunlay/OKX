"""
环境检测工具模块
负责检测当前运行环境（本地开发 vs 生产环境）
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

def is_local_environment():
    """检测是否为本地开发环境"""
    # 优先检查环境变量
    env_setting = os.getenv('ENVIRONMENT', '').lower()
    if env_setting == 'local':
        return True
    elif env_setting == 'production':
        return False
    
    # 如果没有设置环境变量，则通过网络信息判断
    import socket
    try:
        # 检查是否在AWS服务器上（通过IP判断）
        try:
            import urllib.request
            with urllib.request.urlopen('http://httpbin.org/ip', timeout=5) as response:
                data = json.loads(response.read().decode())
                external_ip = data.get('origin', '')
                if external_ip == '13.158.74.102':
                    return False  # 这是AWS服务器
        except Exception:
            pass
            
        # 默认认为是本地环境（更安全的选择）
        return True
        
    except Exception:
        return True