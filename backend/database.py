"""SQLite 数据库连接和初始化"""
import sqlite3
import os
from typing import Optional
from contextlib import contextmanager


class Database:
    """数据库管理类"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，如果为 None 则使用默认路径
        """
        if db_path is None:
            # 默认数据库路径：history/redink.db
            history_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "history"
            )
            os.makedirs(history_dir, exist_ok=True)
            db_path = os.path.join(history_dir, "redink.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. records 表 - 记录主表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    topic TEXT,
                    status TEXT DEFAULT 'draft',
                    reference_images_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 2. tones 表 - 内容基调
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id TEXT NOT NULL,
                    tone_text TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tones_record_id 
                ON tones(record_id)
            """)
            
            # 3. outlines 表 - 大纲信息
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS outlines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tone_id INTEGER NOT NULL,
                    raw_outline TEXT,
                    metadata_title TEXT,
                    metadata_content TEXT,
                    metadata_tags TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_outlines_tone_id 
                ON outlines(tone_id)
            """)
            
            # 4. pages 表 - 页面信息
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    outline_id INTEGER NOT NULL,
                    page_index INTEGER NOT NULL,
                    page_type TEXT NOT NULL,
                    content TEXT,
                    image_id INTEGER
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pages_outline_id 
                ON pages(outline_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pages_outline_page 
                ON pages(outline_id, page_index)
            """)
            
            # 5. images 表 - 图片信息
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    thumbnail_filename TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_images_record_id 
                ON images(record_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_images_filename 
                ON images(filename)
            """)
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接（上下文管理器）
        
        使用方式:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
        try:
            yield conn
        finally:
            conn.close()
    
    def execute(self, query: str, params: tuple = None):
        """
        执行单条 SQL 语句
        
        Args:
            query: SQL 查询语句
            params: 查询参数
            
        Returns:
            cursor 对象
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor
    
    def fetchone(self, query: str, params: tuple = None):
        """
        查询单条记录
        
        Args:
            query: SQL 查询语句
            params: 查询参数
            
        Returns:
            查询结果（字典形式）
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def fetchall(self, query: str, params: tuple = None):
        """
        查询多条记录
        
        Args:
            query: SQL 查询语句
            params: 查询参数
            
        Returns:
            查询结果列表（字典列表）
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


# 全局数据库实例
_db_instance: Optional[Database] = None


def get_database() -> Database:
    """获取全局数据库实例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def reset_database():
    """重置数据库实例（主要用于测试）"""
    global _db_instance
    _db_instance = None

