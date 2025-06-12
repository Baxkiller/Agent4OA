#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的API端点
"""

import requests
import json

def test_fake_news_api():
    """测试虚假信息检测API"""
    
    # API端点
    url = "http://127.0.0.1:8000/detect/fake_news"
    
    # 测试数据
    test_data = {
        "content": "1.74 复制打开抖音，看看【滴水观音的作品】# 星座 # 摩羯座  https://v.douyin.com/w3Eh2R5sjl8/ U@Y.mQ 09/18 Rkc:/",
        "user_id": "test_user_001"
    }
    
    print("=" * 60)
    print("测试虚假信息检测API")
    print("=" * 60)
    print(f"请求URL: {url}")
    print(f"请求数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
    print("-" * 60)
    
    try:
        # 发送POST请求
        response = requests.post(
            url, 
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ API调用成功!")
            print(f"响应数据: {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print("✗ API调用失败!")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("✗ 连接失败! 请确保服务正在运行在 http://127.0.0.1:8000")
    except requests.exceptions.Timeout:
        print("✗ 请求超时!")
    except Exception as e:
        print(f"✗ 发生错误: {e}")

def test_toxic_content_api():
    """测试毒性内容检测API"""
    
    url = "http://127.0.0.1:8000/detect/toxic"
    
    test_data = {
        "content": "你这个老不死的，说话真难听",
        "user_id": "test_user_002"
    }
    
    print("\n" + "=" * 60)
    print("测试毒性内容检测API")
    print("=" * 60)
    print(f"请求URL: {url}")
    print(f"请求数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
    print("-" * 60)
    
    try:
        response = requests.post(
            url, 
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ API调用成功!")
            print(f"响应数据: {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print("✗ API调用失败!")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("✗ 连接失败! 请确保服务正在运行在 http://127.0.0.1:8000")
    except requests.exceptions.Timeout:
        print("✗ 请求超时!")
    except Exception as e:
        print(f"✗ 发生错误: {e}")

def test_service_status():
    """测试服务状态"""
    
    url = "http://127.0.0.1:8000/"
    
    print("\n" + "=" * 60)
    print("测试服务状态")
    print("=" * 60)
    
    try:
        response = requests.get(url, timeout=10)
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ 服务运行正常!")
            print(f"服务信息: {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print("✗ 服务状态异常!")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到服务! 请检查服务是否启动")
        return False
    except Exception as e:
        print(f"✗ 发生错误: {e}")
        return False
    
    return True

def test_privacy_leak_api():
    """测试隐私泄露检测API"""
    
    url = "http://127.0.0.1:8000/detect/privacy"
    
    test_data = {
        "content": "我的银行账户是1234567890",
        "user_id": "test_user_003"
    }
    
    print("\n" + "=" * 60)
    print("测试隐私泄露检测API")
    print("=" * 60)
    print(f"请求URL: {url}")
    print(f"请求数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
    print("-" * 60)
    
    try:
        response = requests.post(
            url, 
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ API调用成功!")
            print(f"响应数据: {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print("✗ API调用失败!")
            
    except requests.exceptions.ConnectionError:
        print("✗ 连接失败! 请确保服务正在运行在 http://127.0.0.1:8000")
    except requests.exceptions.Timeout:
        print("✗ 请求超时!")
    except Exception as e:
        print(f"✗ 发生错误: {e}")

if __name__ == "__main__":
    print("开始API测试...")
    
    # 首先检查服务状态
    if test_service_status():
        # 如果服务正常，测试各个API端点
        test_fake_news_api()
        test_toxic_content_api()
        test_privacy_leak_api()
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60) 