#!/usr/bin/env python3
"""
优化后的服务启动脚本
"""

import uvicorn
import logging
import signal
import sys
from performance_monitor import monitor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def signal_handler(sig, frame):
    """优雅关闭处理"""
    logger.info("收到关闭信号，正在优雅关闭...")
    
    # 打印性能摘要
    monitor.print_summary()
    
    sys.exit(0)

def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("启动优化后的OKX定投服务...")
    
    # 启动服务
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=1,  # 单进程，避免调度器冲突
        access_log=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()