from typing import Optional
import sqlite3
from contextlib import contextmanager
import redis
from app.core.config import settings

# SQLite Configuration
SQLITE_DB_PATH = ":memory:"  # Use in-memory database

# Redis Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

class Database:
    def __init__(self):
        self._sqlite_conn = None
        self._redis_client = None
        
    @property
    def sqlite(self):
        if self._sqlite_conn is None:
            self._sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
            self._init_sqlite_tables()
        return self._sqlite_conn
    
    @property
    def redis(self):
        if self._redis_client is None:
            self._redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True
            )
        return self._redis_client
    
    def _init_sqlite_tables(self):
        """Initialize SQLite tables for chat data"""
        with self.sqlite:
            self.sqlite.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.sqlite.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
                )
            """)
            
            self.sqlite.execute("""
                CREATE TABLE IF NOT EXISTS collected_fields (
                    session_id TEXT PRIMARY KEY,
                    field_name TEXT,
                    field_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
                )
            """)
    
    @contextmanager
    def get_connection(self):
        """Context manager for SQLite connections"""
        conn = sqlite3.connect(SQLITE_DB_PATH)
        try:
            yield conn
        finally:
            conn.close()
    
    def close(self):
        """Close all database connections"""
        if self._sqlite_conn:
            self._sqlite_conn.close()
            self._sqlite_conn = None
        
        if self._redis_client:
            self._redis_client.close()
            self._redis_client = None

# Create global database instance
db = Database() 