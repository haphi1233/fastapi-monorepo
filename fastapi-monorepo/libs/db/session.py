from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool
import os
import logging
from typing import Generator, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create declarative base
Base = declarative_base()

class DatabaseManager:
    """Database manager cho microservice architecture"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or self._build_database_url()
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _build_database_url(self) -> str:
        """Xây dựng database URL từ environment variables"""
        username = os.getenv('DB_USERNAME', 'postgres')
        password = os.getenv('DB_PASSWORD', '123456')
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5433')
        database = os.getenv('DB_NAME', 'defaultdb')
        
        return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
    
    def _initialize_engine(self) -> None:
        """Khởi tạo engine với cấu hình tối ưu cho microservice"""
        self.engine = create_engine(
            self.database_url,
            # Connection pooling configuration
            poolclass=QueuePool,
            pool_size=10,  # Số connection cơ bản
            max_overflow=20,  # Số connection tối đa khi cần
            pool_pre_ping=True,  # Kiểm tra connection trước khi sử dụng
            pool_recycle=3600,  # Recycle connection sau 1 giờ
            pool_timeout=30,  # Timeout khi lấy connection từ pool
            
            # Logging configuration
            echo=os.getenv('DB_ECHO', 'false').lower() == 'true',
            echo_pool=os.getenv('DB_ECHO_POOL', 'false').lower() == 'true',
            
            # Connection arguments
            connect_args={
                "connect_timeout": 10,
                "application_name": os.getenv('SERVICE_NAME', 'fastapi-service')
            }
        )
        
        # Setup session factory
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False  # Tránh lazy loading issues
        )
        
        # Add event listeners
        self._setup_event_listeners()
        
        logger.info(f"Database engine initialized for: {self._mask_password(self.database_url)}")
    
    def _setup_event_listeners(self) -> None:
        """Setup các event listeners cho monitoring và debugging"""
        
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set connection parameters khi kết nối"""
            if 'postgresql' in self.database_url:
                # Set timezone cho PostgreSQL
                with dbapi_connection.cursor() as cursor:
                    cursor.execute("SET timezone TO 'UTC'")
        
        @event.listens_for(self.engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log SQL queries nếu cần debug"""
            if os.getenv('DB_LOG_QUERIES', 'false').lower() == 'true':
                logger.debug(f"SQL Query: {statement[:100]}...")
    
    def _mask_password(self, url: str) -> str:
        """Mask password trong URL để log an toàn"""
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', url)
    
    def get_session(self) -> Generator[Session, None, None]:
        """Dependency để lấy database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """Kiểm tra kết nối database cho health check endpoint"""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False
    
    def close(self) -> None:
        """Đóng tất cả connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")

# Global database manager instance
# Mỗi service sẽ khởi tạo instance riêng với database riêng
db_manager = DatabaseManager()

# Backward compatibility functions
def get_db() -> Generator[Session, None, None]:
    """Dependency function để sử dụng trong FastAPI endpoints"""
    yield from db_manager.get_session()

def get_engine():
    """Lấy engine instance"""
    return db_manager.engine

def get_session_local():
    """Lấy SessionLocal class"""
    return db_manager.SessionLocal