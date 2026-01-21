"""
Database models for multi-user Greenie
SQLAlchemy ORM models for PostgreSQL
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

# Database connection
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "sqlite:///./greenie.db"  # SQLite for local development
)

# PostgreSQL URLs from Render use 'postgres://' but SQLAlchemy requires 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL query logging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class User(Base):
    """User accounts for multi-user support"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    knowledge = relationship("Knowledge", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    error_logs = relationship("ErrorLog", back_populates="user", cascade="all, delete-orphan")


class Memory(Base):
    """Long-term memories for each user"""
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    timestamp = Column(Float, nullable=False)  # Unix timestamp for compatibility
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="memories")
    
    # Index for fast queries
    __table_args__ = (
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
    )


class Knowledge(Base):
    """Knowledge base entries for each user"""
    __tablename__ = "knowledge"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    keywords = Column(Text)  # JSON string of keywords list
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="knowledge")
    
    # Index for fast searches
    __table_args__ = (
        Index('idx_user_keywords', 'user_id', 'keywords'),
    )


class Session(Base):
    """Session storage for ephemeral conversation history"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    session_data = Column(Text)  # JSON string of conversation history
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="sessions")
    
    # Unique constraint: one session per user per session_id
    __table_args__ = (
        Index('idx_user_session', 'user_id', 'session_id', unique=True),
    )


class ErrorLog(Base):
    """Error logs for debugging and monitoring"""
    __tablename__ = "error_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Optional if not logged in
    error_message = Column(Text, nullable=False)
    error_type = Column(String(100), nullable=False)  # "chat_error", "auth_error", "network_error", etc
    error_details = Column(Text)  # JSON string with additional details
    resolved = Column(String(50), default="open")  # "open", "investigating", "resolved"
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = relationship("User", back_populates="error_logs")
    
    # Index for fast queries
    __table_args__ = (
        Index('idx_created_at', 'created_at'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )


# Database helper functions
def get_db():
    """Dependency for FastAPI endpoints to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def drop_all():
    """Drop all tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)


# For backwards compatibility with existing JSON-based code
class DatabaseBackedMemory:
    """Memory class that uses database instead of JSON file"""
    
    def __init__(self, user_id: int | None = None, max_items: int = 1000):
        self.user_id = user_id or 1  # Default to user 1 for single-user mode
        self.max_items = max_items
    
    def add_memory(self, text: str) -> None:
        """Add a memory for the user"""
        db = SessionLocal()
        try:
            import time
            memory = Memory(
                user_id=self.user_id,
                text=text,
                timestamp=time.time()
            )
            db.add(memory)
            db.commit()
            
            # Keep only most recent max_items
            count = db.query(Memory).filter(Memory.user_id == self.user_id).count()
            if count > self.max_items:
                # Delete oldest memories
                oldest = db.query(Memory).filter(
                    Memory.user_id == self.user_id
                ).order_by(Memory.timestamp.asc()).limit(count - self.max_items).all()
                for m in oldest:
                    db.delete(m)
                db.commit()
        finally:
            db.close()
    
    def get_recent(self, n: int = 5) -> list[str]:
        """Get recent memories for the user"""
        db = SessionLocal()
        try:
            memories = db.query(Memory).filter(
                Memory.user_id == self.user_id
            ).order_by(Memory.timestamp.desc()).limit(n).all()
            return [m.text for m in memories]
        finally:
            db.close()
    
    def clear(self) -> None:
        """Clear all memories for the user"""
        db = SessionLocal()
        try:
            db.query(Memory).filter(Memory.user_id == self.user_id).delete()
            db.commit()
        finally:
            db.close()


class DatabaseBackedKnowledgeStore:
    """Knowledge store that uses database instead of JSON file"""
    
    def __init__(self, user_id: int | None = None):
        self.user_id = user_id or 1  # Default to user 1 for single-user mode
    
    def add_knowledge(self, name: str, description: str, keywords: list[str] | None = None) -> None:
        """Add knowledge entry"""
        db = SessionLocal()
        try:
            import json
            knowledge = Knowledge(
                user_id=self.user_id,
                name=name,
                description=description,
                keywords=json.dumps(keywords or [])
            )
            db.add(knowledge)
            db.commit()
        finally:
            db.close()
    
    def search(self, query: str, n: int = 5) -> list[dict]:
        """Search knowledge base"""
        db = SessionLocal()
        try:
            import json
            # Simple case-insensitive search
            query_lower = query.lower()
            results = db.query(Knowledge).filter(
                Knowledge.user_id == self.user_id
            ).all()
            
            # Score and filter results
            scored = []
            for k in results:
                score = 0
                if query_lower in k.name.lower():
                    score += 10
                if query_lower in k.description.lower():
                    score += 5
                keywords = json.loads(k.keywords) if k.keywords else []
                for kw in keywords:
                    if query_lower in kw.lower():
                        score += 3
                
                if score > 0:
                    scored.append((score, {
                        'name': k.name,
                        'description': k.description,
                        'keywords': keywords
                    }))
            
            # Sort by score and return top n
            scored.sort(reverse=True, key=lambda x: x[0])
            return [item[1] for item in scored[:n]]
        finally:
            db.close()
    
    def list_all(self) -> list[dict]:
        """List all knowledge entries"""
        db = SessionLocal()
        try:
            import json
            results = db.query(Knowledge).filter(
                Knowledge.user_id == self.user_id
            ).all()
            return [{
                'name': k.name,
                'description': k.description,
                'keywords': json.loads(k.keywords) if k.keywords else []
            } for k in results]
        finally:
            db.close()
