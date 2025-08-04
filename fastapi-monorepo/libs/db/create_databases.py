#!/usr/bin/env python3
"""
Script để tạo các database cần thiết cho FastAPI monorepo
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database(db_name: str, host: str = "localhost", port: int = 5433, 
                   user: str = "postgres", password: str = "123456") -> None:
    """Tạo database nếu chưa tồn tại"""
    try:
        # Kết nối tới PostgreSQL server (không chỉ định database cụ thể)
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database="postgres"  # Kết nối tới database mặc định
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cursor = conn.cursor()
        
        # Kiểm tra xem database đã tồn tại chưa
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"✅ Database '{db_name}' đã được tạo thành công!")
        else:
            print(f"ℹ️  Database '{db_name}' đã tồn tại.")
            
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ Lỗi khi tạo database '{db_name}': {e}")
    except Exception as e:
        print(f"❌ Lỗi không xác định: {e}")

if __name__ == "__main__":
    print("🚀 Đang tạo databases cho FastAPI monorepo...")
    
    # Tạo database cho service auth
    create_database("authdb")
    
    # Tạo database cho service articles (nếu cần)
    create_database("articlesdb")
    
    # Tạo database cho service user
    create_database("userdb")
    
    # Tạo database cho service roles
    create_database("rolesdb")
    
    # Tạo database cho service products
    create_database("productsdb")
    
    print("✨ Hoàn thành!")
