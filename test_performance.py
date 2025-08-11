#!/usr/bin/env python3
"""
性能测试脚本 - 测试优化后的API响应时间
"""

import requests
import time
import statistics
import concurrent.futures
from typing import List, Dict

API_BASE_URL = "http://13.158.74.102:8000/api"

def test_endpoint(endpoint: str, params: dict = None) -> Dict:
    """测试单个端点的性能"""
    url = f"{API_BASE_URL}{endpoint}"
    start_time = time.time()
    
    try:
        response = requests.get(url, params=params, timeout=30)
        duration = time.time() - start_time
        
        return {
            'endpoint': endpoint,
            'duration': duration,
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'response_size': len(response.content) if response.content else 0
        }
    except Exception as e:
        duration = time.time() - start_time
        return {
            'endpoint': endpoint,
            'duration': duration,
            'status_code': 0,
            'success': False,
            'error': str(e),
            'response_size': 0
        }

def run_performance_test():
    """运行性能测试"""
    print("开始性能测试...")
    
    # 测试端点列表
    test_cases = [
        ('/assets/overview', None),
        ('/assets/overview', {'force_refresh': 'true'}),
        ('/assets/history', {'days': 30}),
        ('/dca-plan', None),
        ('/transactions', {'limit': 50}),
        ('/account/usdt-balance', None),
        ('/debug/status', None),
    ]
    
    results = {}
    
    for endpoint, params in test_cases:
        print(f"\n测试端点: {endpoint}")
        
        # 单次测试
        single_results = []
        for i in range(5):
            result = test_endpoint(endpoint, params)
            single_results.append(result)
            status = '成功' if result['success'] else f"失败({result.get('error', 'Unknown')})"
            print(f"  第{i+1}次: {result['duration']:.3f}s - {status}")
            time.sleep(0.5)  # 避免过于频繁的请求
        
        # 计算统计数据
        durations = [r['duration'] for r in single_results if r['success']]
        if durations:
            stats = {
                'endpoint': endpoint,
                'count': len(durations),
                'avg_duration': statistics.mean(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'median_duration': statistics.median(durations),
                'success_rate': len(durations) / len(single_results) * 100,
                'avg_response_size': statistics.mean([r['response_size'] for r in single_results if r['success']])
            }
        else:
            stats = {
                'endpoint': endpoint,
                'count': 0,
                'avg_duration': 0,
                'min_duration': 0,
                'max_duration': 0,
                'median_duration': 0,
                'success_rate': 0,
                'avg_response_size': 0
            }
        
        results[endpoint] = stats
    
    # 并发测试
    print(f"\n并发测试 - 同时请求资产概览...")
    concurrent_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(test_endpoint, '/assets/overview') for _ in range(10)]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            concurrent_results.append(result)
    
    concurrent_durations = [r['duration'] for r in concurrent_results if r['success']]
    if concurrent_durations:
        concurrent_stats = {
            'avg_duration': statistics.mean(concurrent_durations),
            'max_duration': max(concurrent_durations),
            'success_rate': len(concurrent_durations) / len(concurrent_results) * 100
        }
        print(f"并发测试结果: 平均{concurrent_stats['avg_duration']:.3f}s, 最大{concurrent_stats['max_duration']:.3f}s, 成功率{concurrent_stats['success_rate']:.1f}%")
    
    # 打印总结
    print(f"\n=== 性能测试总结 ===")
    for endpoint, stats in results.items():
        print(f"\n{endpoint}:")
        print(f"  平均响应时间: {stats['avg_duration']:.3f}s")
        print(f"  最快响应时间: {stats['min_duration']:.3f}s")
        print(f"  最慢响应时间: {stats['max_duration']:.3f}s")
        print(f"  成功率: {stats['success_rate']:.1f}%")
        print(f"  平均响应大小: {stats['avg_response_size']:.0f} bytes")
        
        # 性能评级
        if stats['avg_duration'] < 0.5:
            grade = "优秀"
        elif stats['avg_duration'] < 1.0:
            grade = "良好"
        elif stats['avg_duration'] < 2.0:
            grade = "一般"
        else:
            grade = "需要优化"
        
        print(f"  性能评级: {grade}")
    
    return results

if __name__ == "__main__":
    run_performance_test()