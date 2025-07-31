from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Any
import json
import logging
from app.notification.push_service import push_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket连接端点"""
    await websocket.accept()
    
    try:
        # 添加客户端到推送服务
        push_service.add_websocket_client(user_id, websocket)
        logger.info(f"WebSocket客户端已连接: {user_id}")
        
        # 发送连接确认消息
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "user_id": user_id,
            "message": "WebSocket连接已建立"
        }))
        
        # 保持连接，等待消息
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 处理客户端消息
                await handle_client_message(websocket, user_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket客户端断开连接: {user_id}")
                break
            except Exception as e:
                logger.error(f"处理WebSocket消息失败: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "消息处理失败"
                }))
    
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
    finally:
        # 移除客户端
        push_service.remove_websocket_client(user_id)

async def handle_client_message(websocket: WebSocket, user_id: str, message: Dict[str, Any]):
    """处理客户端消息"""
    message_type = message.get("type")
    
    if message_type == "ping":
        # 心跳检测
        await websocket.send_text(json.dumps({
            "type": "pong",
            "timestamp": message.get("timestamp")
        }))
    
    elif message_type == "subscribe":
        # 订阅通知
        await websocket.send_text(json.dumps({
            "type": "subscription_confirmed",
            "message": "已订阅风险通知"
        }))
    
    elif message_type == "notification_ack":
        # 通知确认
        notification_id = message.get("notification_id")
        logger.info(f"用户 {user_id} 确认收到通知: {notification_id}")
        
        # 这里可以更新通知状态为已读
        from app.notification.notification_store import update_notification_status
        update_notification_status(notification_id, "read")
        
        await websocket.send_text(json.dumps({
            "type": "ack_confirmed",
            "notification_id": notification_id
        }))
    
    else:
        # 未知消息类型
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"未知的消息类型: {message_type}"
        }))

@router.get("/ws/status/{user_id}")
async def get_websocket_status(user_id: str):
    """获取WebSocket连接状态"""
    is_connected = user_id in push_service.websocket_provider.connected_clients
    return {
        "user_id": user_id,
        "connected": is_connected,
        "connected_clients_count": len(push_service.websocket_provider.connected_clients)
    } 