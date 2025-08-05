#!/usr/bin/env python3
"""
Database Setup Script
Tạo databases cho các microservices
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
import os

# Database configurations
DATABASES = {
    'authdb': {
        'host': 'localhost',
        'port': 5433,
        'user': 'postgres',
        'password': '123456'
    },
    'productsdb': {
        'host': 'localhost', 
        'port': 5433,
        'user': 'postgres',
        'password': '123456'
    },
    'articlesdb': {
        'host': 'localhost',
        'port': 5433, 
        'user': 'postgres',
        'password': '123456'
    }
}

def create_database(db_name, config):
    """Tạo database nếu chưa tồn tại"""
    try:
        # Kết nối đến PostgreSQL server (không chỉ định database)
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database='postgres'  # Kết nối đến default database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cursor = conn.cursor()
        
        # Kiểm tra database đã tồn tại chưa
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"✅ Created database: {db_name}")
        else:
            print(f"ℹ️  Database already exists: {db_name}")
            
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Error creating database {db_name}: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Setting up databases for FastAPI Monorepo...")
    print("=" * 50)
    
    success_count = 0
    total_count = len(DATABASES)
    
    for db_name, config in DATABASES.items():
        print(f"\n📊 Creating database: {db_name}")
        if create_database(db_name, config):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"✅ Successfully created {success_count}/{total_count} databases")
    
    if success_count == total_count:
        print("🎉 All databases are ready!")
        return 0
    else:
        print("⚠️  Some databases failed to create. Please check PostgreSQL connection.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
