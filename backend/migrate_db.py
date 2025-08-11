#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加索引优化查询性能
"""

import sqlite3
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """执行数据库迁移，添加索引"""
    db_path = "./dca.db"
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查并创建索引
        indexes_to_create = [
            # Transaction表的复合索引
            ("idx_plan_executed_at", "CREATE INDEX IF NOT EXISTS idx_plan_executed_at ON transactions (plan_id, executed_at)"),
            ("idx_status_executed_at", "CREATE INDEX IF NOT EXISTS idx_status_executed_at ON transactions (status, executed_at)"),
            ("idx_symbol_direction_status", "CREATE INDEX IF NOT EXISTS idx_symbol_direction_status ON transactions (symbol, direction, status)"),
            ("idx_plan_status_executed", "CREATE INDEX IF NOT EXISTS idx_plan_status_executed ON transactions (plan_id, status, executed_at)"),
            
            # AssetHistory表的索引
            ("idx_recorded_at_desc", "CREATE INDEX IF NOT EXISTS idx_recorded_at_desc ON asset_history (recorded_at DESC)"),
            
            # DCAPlan表的索引
            ("idx_dca_status", "CREATE INDEX IF NOT EXISTS idx_dca_status ON dca_plans (status)"),
            ("idx_dca_symbol_status", "CREATE INDEX IF NOT EXISTS idx_dca_symbol_status ON dca_plans (symbol, status)"),
        ]
        
        for index_name, sql in indexes_to_create:
            try:
                logger.info(f"创建索引: {index_name}")
                cursor.execute(sql)
                logger.info(f"索引 {index_name} 创建成功")
            except sqlite3.Error as e:
                logger.warning(f"创建索引 {index_name} 失败: {str(e)}")
        
        # 提交更改
        conn.commit()
        
        # 分析表以更新统计信息
        logger.info("更新表统计信息...")
        cursor.execute("ANALYZE")
        conn.commit()
        
        # 显示当前所有索引
        logger.info("当前数据库索引:")
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
        indexes = cursor.fetchall()
        for name, sql in indexes:
            logger.info(f"  {name}: {sql}")
        
        conn.close()
        logger.info("数据库迁移完成")
        return True
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        return False

if __name__ == "__main__":
    migrate_database()