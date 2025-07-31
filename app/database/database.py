import sqlite3
import os
from typing import Optional
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "agent4oa.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库，创建表结构"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建用户关系表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_relationships (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        relationship_id TEXT UNIQUE NOT NULL,
                        elder_user_id TEXT NOT NULL,
                        child_user_id TEXT NOT NULL,
                        relationship_type TEXT DEFAULT 'parent_child',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        UNIQUE(elder_user_id, child_user_id)
                    )
                ''')
                
                # 创建风险通知表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS risk_notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        notification_id TEXT UNIQUE NOT NULL,
                        elder_user_id TEXT NOT NULL,
                        child_user_id TEXT NOT NULL,
                        content_type TEXT NOT NULL,
                        risk_level TEXT NOT NULL,
                        platform TEXT NOT NULL,
                        suggestion TEXT,
                        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_elder_user_id ON user_relationships(elder_user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_child_user_id ON user_relationships(child_user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_notification_elder ON risk_notifications(elder_user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_notification_child ON risk_notifications(child_user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_notification_status ON risk_notifications(status)')
                
                conn.commit()
                logger.info("数据库初始化完成")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
            yield conn
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

# 全局数据库管理器实例
db_manager = DatabaseManager() 