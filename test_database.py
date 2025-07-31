#!/usr/bin/env python3
"""
数据库功能测试脚本
测试数据持久化功能
"""

import requests
import json
import time
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:8000"

def test_database_functionality():
    """测试数据库功能"""
    print("开始测试数据库持久化功能")
    print("="*60)
    
    # 1. 测试用户关系管理
    print("\n1. 测试用户关系管理")
    print("-"*40)
    
    # 获取所有关系
    response = requests.get(f"{BASE_URL}/api/notification/relationships")
    print(f"获取所有关系: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"关系数量: {data.get('count', 0)}")
    
    # 测试查询关系
    response = requests.get(f"{BASE_URL}/api/notification/relationship/child", params={"elder_user_id": "elder_001"})
    print(f"查询老年人关系: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"找到子女: {data.get('child_user_id')}")
    
    # 2. 测试通知持久化
    print("\n2. 测试通知持久化")
    print("-"*40)
    
    # 先检测一个会触发通知的内容
    test_content = {
        "content": "测试数据库持久化：您的账户已被冻结，请立即转账！",
        "user_id": "elder_001"
    }
    
    response = requests.post(f"{BASE_URL}/detect/fake_news", json=test_content)
    print(f"检测虚假信息: {response.status_code}")
    
    # 等待一下
    time.sleep(2)
    
    # 检查通知是否保存到数据库
    response = requests.get(f"{BASE_URL}/api/notification/notifications")
    print(f"获取所有通知: {response.status_code}")
    if response.status_code == 200:
        notifications = response.json()
        print(f"通知数量: {len(notifications)}")
        if notifications:
            print(f"最新通知: {notifications[0]}")
    
    # 3. 测试通知状态更新
    print("\n3. 测试通知状态更新")
    print("-"*40)
    
    if notifications:
        notification_id = notifications[0]['notification_id']
        response = requests.put(f"{BASE_URL}/api/notification/notifications/{notification_id}/status", params={"status": "read"})
        print(f"更新通知状态: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"更新结果: {data.get('message')}")
    
    # 4. 测试通知删除
    print("\n4. 测试通知删除")
    print("-"*40)
    
    if notifications:
        notification_id = notifications[0]['notification_id']
        response = requests.delete(f"{BASE_URL}/api/notification/notifications/{notification_id}")
        print(f"删除通知: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"删除结果: {data.get('message')}")
    
    # 5. 验证数据持久化
    print("\n5. 验证数据持久化")
    print("-"*40)
    
    # 重启服务器后数据应该仍然存在
    print("请手动重启服务器，然后运行以下命令验证数据是否持久化:")
    print("curl http://localhost:8000/api/notification/notifications")
    print("curl http://localhost:8000/api/notification/relationships")

def test_database_operations():
    """测试数据库操作"""
    print("\n" + "="*60)
    print("测试数据库CRUD操作")
    print("="*60)
    
    # 测试添加新关系
    print("\n1. 测试添加新用户关系")
    new_relationship = {
        "relationship_id": "rel_test_001",
        "elder_user_id": "elder_test_001",
        "child_user_id": "child_test_001",
        "relationship_type": "parent_child",
        "is_active": True
    }
    
    response = requests.post(f"{BASE_URL}/api/notification/relationships", json=new_relationship)
    print(f"添加关系: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"添加结果: {data.get('message')}")
    
    # 测试查询新关系
    response = requests.get(f"{BASE_URL}/api/notification/relationship/child", params={"elder_user_id": "elder_test_001"})
    print(f"查询新关系: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"查询结果: {data}")

if __name__ == "__main__":
    try:
        test_database_functionality()
        test_database_operations()
        print("\n" + "="*60)
        print("数据库功能测试完成！")
        print("="*60)
    except Exception as e:
        print(f"测试失败: {e}")
        print("请确保服务器正在运行: python -m app.main") 