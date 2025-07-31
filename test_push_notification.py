#!/usr/bin/env python3
"""
推送通知测试脚本
测试WebSocket、邮件和短信推送功能
"""

import asyncio
import websockets
import json
import requests
import time
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/api/notification/ws"

async def test_websocket_connection():
    """测试WebSocket连接"""
    print("="*60)
    print("测试WebSocket实时推送")
    print("="*60)
    
    user_id = "child_001"
    
    try:
        # 连接WebSocket
        uri = f"{WS_URL}/{user_id}"
        print(f"连接到WebSocket: {uri}")
        
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功")
            
            # 发送订阅消息
            subscribe_message = {
                "type": "subscribe",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(subscribe_message))
            print("📤 发送订阅消息")
            
            # 发送心跳
            ping_message = {
                "type": "ping",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(ping_message))
            print("📤 发送心跳消息")
            
            # 等待接收消息
            print("⏳ 等待接收消息...")
            
            # 设置超时时间
            try:
                async with asyncio.timeout(10):  # 10秒超时
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        print(f"📥 收到消息: {data}")
                        
                        # 如果是通知消息，发送确认
                        if data.get("type") == "risk_notification":
                            ack_message = {
                                "type": "notification_ack",
                                "notification_id": data["notification"]["notification_id"],
                                "timestamp": datetime.now().isoformat()
                            }
                            await websocket.send(json.dumps(ack_message))
                            print("📤 发送通知确认")
                            break
                        
                        # 如果是连接确认或心跳响应，继续等待
                        elif data.get("type") in ["connection_established", "pong", "subscription_confirmed"]:
                            continue
                        else:
                            print(f"未知消息类型: {data.get('type')}")
                            break
                            
            except asyncio.TimeoutError:
                print("⏰ 等待超时，未收到通知消息")
    
    except Exception as e:
        print(f"❌ WebSocket测试失败: {e}")

def test_push_notification_trigger():
    """测试触发推送通知"""
    print("\n" + "="*60)
    print("测试触发推送通知")
    print("="*60)
    
    # 测试内容
    test_content = {
        "content": "测试推送通知：您的银行账户已被冻结，请立即转账到安全账户！",
        "user_id": "elder_001"
    }
    
    try:
        # 发送检测请求
        print("📤 发送检测请求...")
        response = requests.post(f"{BASE_URL}/detect/fake_news", json=test_content)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 检测完成: {result.get('message')}")
            
            if result.get('success'):
                print("🎯 检测到风险，应该触发推送通知")
            else:
                print("⚠️ 检测未成功，可能不会触发推送")
        else:
            print(f"❌ 检测请求失败: {response.status_code}")
    
    except Exception as e:
        print(f"❌ 触发推送测试失败: {e}")

def test_websocket_status():
    """测试WebSocket状态"""
    print("\n" + "="*60)
    print("测试WebSocket连接状态")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/notification/ws/status/child_001")
        
        if response.status_code == 200:
            status = response.json()
            print(f"用户连接状态: {status}")
        else:
            print(f"❌ 获取状态失败: {response.status_code}")
    
    except Exception as e:
        print(f"❌ 状态测试失败: {e}")

def test_email_configuration():
    """测试邮件配置"""
    print("\n" + "="*60)
    print("测试邮件推送配置")
    print("="*60)
    
    # 这里只是示例，实际需要配置真实的邮箱信息
    print("📧 邮件推送配置示例:")
    print("- 需要配置SMTP服务器信息")
    print("- 需要配置发件人邮箱和密码")
    print("- 需要配置收件人邮箱信息")
    print("- 支持HTML格式邮件内容")

def test_sms_configuration():
    """测试短信配置"""
    print("\n" + "="*60)
    print("测试短信推送配置")
    print("="*60)
    
    # 这里只是示例，实际需要配置真实的短信服务
    print("📱 短信推送配置示例:")
    print("- 需要配置短信服务API密钥")
    print("- 需要配置短信模板")
    print("- 需要配置收件人手机号")
    print("- 支持自定义短信内容")

async def main():
    """主测试函数"""
    print("开始测试推送通知功能")
    print("="*80)
    
    # 1. 测试WebSocket连接
    await test_websocket_connection()
    
    # 2. 测试WebSocket状态
    test_websocket_status()
    
    # 3. 测试触发推送通知
    test_push_notification_trigger()
    
    # 4. 测试邮件配置
    test_email_configuration()
    
    # 5. 测试短信配置
    test_sms_configuration()
    
    print("\n" + "="*80)
    print("推送通知功能测试完成！")
    print("="*80)
    print("\n📋 测试说明:")
    print("1. WebSocket测试：需要先建立连接，然后触发检测")
    print("2. 邮件推送：需要配置SMTP服务器信息")
    print("3. 短信推送：需要配置短信服务API")
    print("4. 实时推送：WebSocket连接后可以实时接收通知")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试失败: {e}")
        print("请确保服务器正在运行: python -m app.main") 