from typing import List, Dict, Optional
import json
from datetime import datetime
from app.core.database import db
from app.schemas.chat import ChatMessage, ChatSession

class ChatRepository:
    def __init__(self):
        self.redis = db.redis
        self.sqlite = db.sqlite
    
    def create_session(self, session_id: str, user_id: Optional[str] = None) -> None:
        """Create a new chat session"""
        # Store in SQLite
        with self.sqlite:
            self.sqlite.execute(
                """
                INSERT INTO chat_sessions (session_id, user_id)
                VALUES (?, ?)
                """,
                (session_id, user_id)
            )
        
        # Store in Redis for quick access
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
        self.redis.hset(f"chat:session:{session_id}", mapping=session_data)
    
    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Add a message to the chat session"""
        # Store in SQLite
        with self.sqlite:
            self.sqlite.execute(
                """
                INSERT INTO chat_messages (session_id, role, content)
                VALUES (?, ?, ?)
                """,
                (session_id, message.role, message.content)
            )
        
        # Store in Redis for quick access
        message_data = {
            "role": message.role,
            "content": message.content,
            "timestamp": datetime.now().isoformat()
        }
        self.redis.rpush(f"chat:messages:{session_id}", json.dumps(message_data))
        
        # Update last activity
        self.redis.hset(f"chat:session:{session_id}", "last_activity", datetime.now().isoformat())
    
    def get_messages(self, session_id: str, limit: int = 50) -> List[ChatMessage]:
        """Get messages for a chat session"""
        # Try Redis first
        redis_messages = self.redis.lrange(f"chat:messages:{session_id}", -limit, -1)
        if redis_messages:
            return [ChatMessage(**json.loads(msg)) for msg in redis_messages]
        
        # Fallback to SQLite
        cursor = self.sqlite.execute(
            """
            SELECT role, content, timestamp
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (session_id, limit)
        )
        return [
            ChatMessage(role=row[0], content=row[1])
            for row in cursor.fetchall()
        ]
    
    def update_collected_fields(self, session_id: str, fields: Dict[str, str]) -> None:
        """Update collected fields for a chat session"""
        # Store in SQLite
        with self.sqlite:
            for field_name, field_value in fields.items():
                self.sqlite.execute(
                    """
                    INSERT OR REPLACE INTO collected_fields (session_id, field_name, field_value)
                    VALUES (?, ?, ?)
                    """,
                    (session_id, field_name, field_value)
                )
        
        # Store in Redis
        self.redis.hset(f"chat:fields:{session_id}", mapping=fields)
    
    def get_collected_fields(self, session_id: str) -> Dict[str, str]:
        """Get collected fields for a chat session"""
        # Try Redis first
        redis_fields = self.redis.hgetall(f"chat:fields:{session_id}")
        if redis_fields:
            return redis_fields
        
        # Fallback to SQLite
        cursor = self.sqlite.execute(
            """
            SELECT field_name, field_value
            FROM collected_fields
            WHERE session_id = ?
            """,
            (session_id,)
        )
        return {row[0]: row[1] for row in cursor.fetchall()}
    
    def delete_session(self, session_id: str) -> None:
        """Delete a chat session and all associated data"""
        # Delete from SQLite
        with self.sqlite:
            self.sqlite.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            self.sqlite.execute("DELETE FROM collected_fields WHERE session_id = ?", (session_id,))
            self.sqlite.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
        
        # Delete from Redis
        self.redis.delete(f"chat:session:{session_id}")
        self.redis.delete(f"chat:messages:{session_id}")
        self.redis.delete(f"chat:fields:{session_id}")
    
    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists"""
        # Try Redis first
        if self.redis.exists(f"chat:session:{session_id}"):
            return True
        
        # Fallback to SQLite
        cursor = self.sqlite.execute(
            "SELECT 1 FROM chat_sessions WHERE session_id = ?",
            (session_id,)
        )
        return cursor.fetchone() is not None

# Create global repository instance
chat_repository = ChatRepository() 