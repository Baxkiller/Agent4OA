#!/usr/bin/env python3
"""
API接口测试脚本
测试跨端风险通知模块的所有功能
"""

import requests
import json
import time
from typing import Dict, Any

# API基础URL
BASE_URL = "http://localhost:8000"

def test_api_endpoint(endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
    """测试API端点"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=data)
        elif method.upper() == "POST":
            response = requests.post(url, json=data)
        else:
            return {"error": f"不支持的HTTP方法: {method}"}
        
        print(f"测试 {method} {endpoint}")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return {"success": True, "data": result}
        else:
            print(f"错误: {response.text}")
            return {"success": False, "error": response.text}
            
    except requests.exceptions.ConnectionError:
        print(f"连接错误: 无法连接到 {url}")
        print("请确保服务器正在运行: python -m app.main")
        return {"success": False, "error": "连接失败"}
    except Exception as e:
        print(f"测试失败: {str(e)}")
        return {"success": False, "error": str(e)}

def test_health_check():
    """测试健康检查"""
    print("\n" + "="*50)
    print("1. 测试健康检查")
    print("="*50)
    return test_api_endpoint("/")

def test_detection_apis():
    """测试检测API"""
    print("\n" + "="*50)
    print("2. 测试检测API")
    print("="*50)
    
    # 测试虚假信息检测
    print("\n--- 测试虚假信息检测 ---")
    fake_news_data = {
        "content": "免费领取iPhone 15，点击链接立即领取！",
        "user_id": "elder_001"
    }
    result1 = test_api_endpoint("/detect/fake_news", "POST", fake_news_data)
    
    # 测试毒性内容检测
    print("\n--- 测试毒性内容检测 ---")
    toxic_data = {
        "content": "你是个白痴，滚开！",
        "user_id": "elder_002"
    }
    result2 = test_api_endpoint("/detect/toxic", "POST", toxic_data)
    
    # 测试隐私泄露检测
    print("\n--- 测试隐私泄露检测 ---")
    privacy_data = {
        "content": "我的身份证号是123456789012345678，手机号是13800138000",
        "user_id": "elder_001"
    }
    result3 = test_api_endpoint("/detect/privacy", "POST", privacy_data)
    
    return result1, result2, result3

def test_notification_apis():
    """测试通知API"""
    print("\n" + "="*50)
    print("3. 测试通知API")
    print("="*50)
    
    # 测试获取所有通知
    print("\n--- 测试获取所有通知 ---")
    result1 = test_api_endpoint("/api/notification/notifications")
    
    # 测试根据子女ID获取通知
    print("\n--- 测试根据子女ID获取通知 ---")
    result2 = test_api_endpoint("/api/notification/notifications/by_child", data={"child_user_id": "child_001"})
    
    return result1, result2

def test_relationship_apis():
    """测试用户关系API"""
    print("\n" + "="*50)
    print("4. 测试用户关系API")
    print("="*50)
    
    # 测试根据老年人ID获取子女ID
    print("\n--- 测试根据老年人ID获取子女ID ---")
    result1 = test_api_endpoint("/api/notification/relationship/child", data={"elder_user_id": "elder_001"})
    
    # 测试根据子女ID获取老年人ID
    print("\n--- 测试根据子女ID获取老年人ID ---")
    result2 = test_api_endpoint("/api/notification/relationship/elder", data={"child_user_id": "child_001"})
    
    # 测试不存在的用户
    print("\n--- 测试不存在的用户 ---")
    result3 = test_api_endpoint("/api/notification/relationship/child", data={"elder_user_id": "elder_999"})
    
    return result1, result2, result3

def test_comprehensive_flow():
    """测试完整流程"""
    print("\n" + "="*50)
    print("5. 测试完整流程")
    print("="*50)
    
    # 1. 先检测一个会触发通知的内容
    print("\n--- 步骤1: 检测会触发通知的内容 ---")
    test_content = {
        "content": "紧急通知：您的银行账户已被冻结，请立即转账到安全账户！",
        "user_id": "elder_001"
    }
    detection_result = test_api_endpoint("/detect/fake_news", "POST", test_content)
    
    # 等待一下，确保通知被处理
    time.sleep(2)
    
    # 2. 检查是否生成了通知
    print("\n--- 步骤2: 检查通知是否生成 ---")
    notifications = test_api_endpoint("/api/notification/notifications")
    
    # 3. 检查子女端是否能收到通知
    print("\n--- 步骤3: 检查子女端通知 ---")
    child_notifications = test_api_endpoint("/api/notification/notifications/by_child", data={"child_user_id": "child_001"})
    
    return detection_result, notifications, child_notifications

def main():
    """主测试函数"""
    print("开始测试跨端风险通知模块API接口")
    print("="*60)
    
    # 测试结果统计
    test_results = []
    
    # 1. 健康检查
    health_result = test_health_check()
    test_results.append(("健康检查", health_result))
    
    # 2. 检测API
    detection_results = test_detection_apis()
    test_results.extend([
        ("虚假信息检测", detection_results[0]),
        ("毒性内容检测", detection_results[1]),
        ("隐私泄露检测", detection_results[2])
    ])
    
    # 3. 通知API
    notification_results = test_notification_apis()
    test_results.extend([
        ("获取所有通知", notification_results[0]),
        ("根据子女ID获取通知", notification_results[1])
    ])
    
    # 4. 用户关系API
    relationship_results = test_relationship_apis()
    test_results.extend([
        ("根据老年人ID获取子女ID", relationship_results[0]),
        ("根据子女ID获取老年人ID", relationship_results[1]),
        ("测试不存在的用户", relationship_results[2])
    ])
    
    # 5. 完整流程测试
    flow_results = test_comprehensive_flow()
    test_results.extend([
        ("完整流程-检测", flow_results[0]),
        ("完整流程-通知生成", flow_results[1]),
        ("完整流程-子女端通知", flow_results[2])
    ])
    
    # 输出测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    success_count = 0
    total_count = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 成功" if result.get("success", False) else "❌ 失败"
        print(f"{test_name}: {status}")
        if result.get("success", False):
            success_count += 1
    
    print(f"\n总计: {success_count}/{total_count} 个测试通过")
    
    if success_count == total_count:
        print("🎉 所有测试通过！跨端风险通知模块工作正常。")
    else:
        print("⚠️  部分测试失败，请检查相关功能。")

if __name__ == "__main__":
    main() 