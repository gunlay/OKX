#!/usr/bin/env python3
"""
性能监控工具 - 监控API响应时间和数据库查询性能
"""

import time
import logging
import functools
from typing import Dict, Any, Optional
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceMonitor:
    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self.api_metrics = defaultdict(lambda: deque(maxlen=max_records))
        self.db_metrics = defaultdict(lambda: deque(maxlen=max_records))
        self.lock = threading.Lock()
    
    def record_api_call(self, endpoint: str, duration: float, success: bool = True):
        """记录API调用性能"""
        with self.lock:
            self.api_metrics[endpoint].append({
                'duration': duration,
                'success': success,
                'timestamp': datetime.now()
            })
    
    def record_db_query(self, query_type: str, duration: float, success: bool = True):
        """记录数据库查询性能"""
        with self.lock:
            self.db_metrics[query_type].append({
                'duration': duration,
                'success': success,
                'timestamp': datetime.now()
            })
    
    def get_api_stats(self, endpoint: str = None) -> Dict[str, Any]:
        """获取API性能统计"""
        with self.lock:
            if endpoint:
                metrics = self.api_metrics.get(endpoint, deque())
                return self._calculate_stats(list(metrics), endpoint)
            else:
                stats = {}
                for ep, metrics in self.api_metrics.items():
                    stats[ep] = self._calculate_stats(list(metrics), ep)
                return stats
    
    def get_db_stats(self, query_type: str = None) -> Dict[str, Any]:
        """获取数据库性能统计"""
        with self.lock:
            if query_type:
                metrics = self.db_metrics.get(query_type, deque())
                return self._calculate_stats(list(metrics), query_type)
            else:
                stats = {}
                for qt, metrics in self.db_metrics.items():
                    stats[qt] = self._calculate_stats(list(metrics), qt)
                return stats
    
    def _calculate_stats(self, metrics: list, name: str) -> Dict[str, Any]:
        """计算性能统计数据"""
        if not metrics:
            return {
                'name': name,
                'count': 0,
                'avg_duration': 0,
                'min_duration': 0,
                'max_duration': 0,
                'success_rate': 0,
                'recent_avg': 0
            }
        
        durations = [m['duration'] for m in metrics]
        successes = [m['success'] for m in metrics]
        
        # 最近10次的平均响应时间
        recent_durations = durations[-10:] if len(durations) >= 10 else durations
        recent_avg = sum(recent_durations) / len(recent_durations) if recent_durations else 0
        
        return {
            'name': name,
            'count': len(metrics),
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'success_rate': sum(successes) / len(successes) * 100,
            'recent_avg': recent_avg
        }
    
    def get_slow_queries(self, threshold: float = 1.0) -> Dict[str, list]:
        """获取慢查询列表"""
        slow_apis = []
        slow_dbs = []
        
        with self.lock:
            # 检查API调用
            for endpoint, metrics in self.api_metrics.items():
                for metric in metrics:
                    if metric['duration'] > threshold:
                        slow_apis.append({
                            'endpoint': endpoint,
                            'duration': metric['duration'],
                            'timestamp': metric['timestamp']
                        })
            
            # 检查数据库查询
            for query_type, metrics in self.db_metrics.items():
                for metric in metrics:
                    if metric['duration'] > threshold:
                        slow_dbs.append({
                            'query_type': query_type,
                            'duration': metric['duration'],
                            'timestamp': metric['timestamp']
                        })
        
        return {
            'slow_apis': sorted(slow_apis, key=lambda x: x['duration'], reverse=True),
            'slow_dbs': sorted(slow_dbs, key=lambda x: x['duration'], reverse=True)
        }
    
    def print_summary(self):
        """打印性能摘要"""
        print("\n=== 性能监控摘要 ===")
        
        # API性能
        api_stats = self.get_api_stats()
        if api_stats:
            print("\nAPI调用性能:")
            for endpoint, stats in api_stats.items():
                print(f"  {endpoint}:")
                print(f"    调用次数: {stats['count']}")
                print(f"    平均耗时: {stats['avg_duration']:.3f}s")
                print(f"    最近平均: {stats['recent_avg']:.3f}s")
                print(f"    成功率: {stats['success_rate']:.1f}%")
        
        # 数据库性能
        db_stats = self.get_db_stats()
        if db_stats:
            print("\n数据库查询性能:")
            for query_type, stats in db_stats.items():
                print(f"  {query_type}:")
                print(f"    查询次数: {stats['count']}")
                print(f"    平均耗时: {stats['avg_duration']:.3f}s")
                print(f"    最近平均: {stats['recent_avg']:.3f}s")
                print(f"    成功率: {stats['success_rate']:.1f}%")
        
        # 慢查询
        slow_queries = self.get_slow_queries()
        if slow_queries['slow_apis'] or slow_queries['slow_dbs']:
            print("\n慢查询 (>1秒):")
            for slow_api in slow_queries['slow_apis'][:5]:  # 只显示前5个
                print(f"  API: {slow_api['endpoint']} - {slow_api['duration']:.3f}s")
            for slow_db in slow_queries['slow_dbs'][:5]:  # 只显示前5个
                print(f"  DB: {slow_db['query_type']} - {slow_db['duration']:.3f}s")

# 全局性能监控实例
monitor = PerformanceMonitor()

def monitor_api_call(endpoint: str):
    """API调用性能监控装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                monitor.record_api_call(endpoint, duration, success)
                if duration > 2.0:  # 记录超过2秒的慢调用
                    logger.warning(f"慢API调用: {endpoint} 耗时 {duration:.3f}s")
        return wrapper
    return decorator

def monitor_db_query(query_type: str):
    """数据库查询性能监控装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                monitor.record_db_query(query_type, duration, success)
                if duration > 1.0:  # 记录超过1秒的慢查询
                    logger.warning(f"慢数据库查询: {query_type} 耗时 {duration:.3f}s")
        return wrapper
    return decorator

if __name__ == "__main__":
    # 测试性能监控
    import random
    
    # 模拟一些API调用
    for i in range(10):
        duration = random.uniform(0.1, 2.0)
        monitor.record_api_call("/api/assets/overview", duration, True)
        
        duration = random.uniform(0.05, 0.5)
        monitor.record_db_query("get_transactions", duration, True)
    
    # 打印摘要
    monitor.print_summary()