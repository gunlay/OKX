#!/usr/bin/env python3
"""
快速性能测试
"""

import requests
import time

def test_api(endpoint, description):
    """测试单个API端点"""
    url = f"http://13.158.74.102:8000/api{endpoint}"
    print(f"\n测试 {description}...")
    
    try:
        start_time = time.time()
        response = requests.get(url, timeout=30)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            print(f"✅ 成功 - 耗时: {duration:.3f}秒")
            return True, duration
        else:
            print(f"❌ 失败 - 状态码: {response.status_code}")
            return False, duration
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ 异常 - {str(e)} - 耗时: {duration:.3f}秒")
        return False, duration

def main():
    print("🚀 OKX定投系统性能优化验证")
    print("=" * 50)
    
    # 测试关键端点
    tests = [
        ("/debug/status", "系统状态"),
        ("/assets/overview", "资产概览"),
        ("/dca-plan", "定投计划"),
        ("/transactions?limit=10", "交易记录"),
        ("/account/usdt-balance", "USDT余额"),
    ]
    
    results = []
    for endpoint, desc in tests:
        success, duration = test_api(endpoint, desc)
        results.append((desc, success, duration))
    
    # 总结
    print(f"\n📊 测试总结")
    print("=" * 50)
    
    successful = sum(1 for _, success, _ in results if success)
    total = len(results)
    avg_duration = sum(duration for _, success, duration in results if success) / max(successful, 1)
    
    print(f"成功率: {successful}/{total} ({successful/total*100:.1f}%)")
    print(f"平均响应时间: {avg_duration:.3f}秒")
    
    # 性能评级
    if avg_duration < 0.5:
        grade = "🟢 优秀"
    elif avg_duration < 1.0:
        grade = "🟡 良好"  
    elif avg_duration < 2.0:
        grade = "🟠 一般"
    else:
        grade = "🔴 需要优化"
    
    print(f"性能评级: {grade}")
    
    if successful == total and avg_duration < 1.0:
        print("\n🎉 性能优化效果显著！系统响应速度已大幅提升。")
    elif successful == total:
        print("\n✅ 系统运行正常，性能有所改善。")
    else:
        print("\n⚠️  部分接口存在问题，建议检查服务状态。")

if __name__ == "__main__":
    main()