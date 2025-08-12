#!/usr/bin/env python3
"""
本地开发启动脚本
设置环境变量并启动FastAPI服务
"""

import os
import sys
import subprocess

def main():
    # 设置环境变量
    os.environ['ENVIRONMENT'] = 'local'
    os.environ['PROXY_BASE_URL'] = 'http://13.158.74.102:8000'
    
    print("🚀 启动本地开发环境")
    print("📡 使用代理模式连接OKX API")
    print(f"🔗 代理服务器: {os.environ['PROXY_BASE_URL']}")
    print("-" * 50)
    
    # 启动FastAPI服务
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "127.0.0.1", 
            "--port", "8000", 
            "--reload"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()