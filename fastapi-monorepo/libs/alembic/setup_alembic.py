#!/usr/bin/env python3
"""
Script để tự động setup Alembic cho service mới trong FastAPI monorepo.
Sử dụng: python setup_alembic.py <service_name>
"""
import os
import sys
import shutil
from pathlib import Path

def setup_alembic_for_service(service_name: str) -> None:
    """Setup Alembic configuration cho service mới"""
    
    # Đường dẫn gốc của monorepo
    monorepo_root = Path(__file__).parent.parent.parent
    service_path = monorepo_root / "services" / service_name
    
    if not service_path.exists():
        print(f"❌ Service '{service_name}' không tồn tại tại {service_path}")
        return
    
    print(f"🚀 Đang setup Alembic cho service '{service_name}'...")
    
    # 1. Tạo thư mục alembic nếu chưa có
    alembic_dir = service_path / "alembic"
    alembic_dir.mkdir(exist_ok=True)
    
    versions_dir = alembic_dir / "versions"
    versions_dir.mkdir(exist_ok=True)
    
    # 2. Copy template alembic.ini
    template_ini = Path(__file__).parent / "alembic_template.ini"
    target_ini = service_path / "alembic.ini"
    
    if template_ini.exists():
        shutil.copy2(template_ini, target_ini)
        print(f"✅ Đã copy alembic.ini template")
    else:
        print(f"⚠️  Template alembic.ini không tìm thấy")
    
    # 3. Copy template env.py
    template_env = Path(__file__).parent / "env_template.py"
    target_env = alembic_dir / "env.py"
    
    if template_env.exists():
        # Đọc template và thay thế placeholder
        with open(template_env, 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        # Thay thế import path cho service cụ thể
        env_content = env_content.replace(
            "# from services.user.app.models.user import User",
            f"from services.{service_name}.app.models import *  # Import all models"
        )
        
        with open(target_env, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print(f"✅ Đã tạo env.py với import path cho service '{service_name}'")
    else:
        print(f"⚠️  Template env.py không tìm thấy")
    
    # 4. Tạo file .env mẫu nếu chưa có
    env_file = service_path / ".env"
    if not env_file.exists():
        env_content = f"""DB_USERNAME=postgres
DB_PASSWORD=123456
DB_HOST=localhost
DB_PORT=5433
DB_NAME={service_name}db
"""
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print(f"✅ Đã tạo file .env với database '{service_name}db'")
    
    # 5. Tạo script.py.mako nếu cần
    script_mako = alembic_dir / "script.py.mako"
    if not script_mako.exists():
        mako_content = '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade schema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade schema."""
    ${downgrades if downgrades else "pass"}
'''
        with open(script_mako, 'w', encoding='utf-8') as f:
            f.write(mako_content)
        print(f"✅ Đã tạo script.py.mako template")
    
    print(f"""
🎉 Setup hoàn thành cho service '{service_name}'!

📋 Các bước tiếp theo:
1. Đảm bảo database '{service_name}db' đã được tạo
2. Tạo models trong services/{service_name}/app/models/
3. Cập nhật import trong alembic/env.py nếu cần
4. Chạy: cd services/{service_name} && alembic revision --autogenerate -m "initial migration"
5. Chạy: alembic upgrade head

📁 Các file đã được tạo:
- services/{service_name}/alembic.ini
- services/{service_name}/alembic/env.py
- services/{service_name}/alembic/script.py.mako
- services/{service_name}/.env (nếu chưa có)
""")

def main():
    if len(sys.argv) != 2:
        print("❌ Sử dụng: python setup_alembic.py <service_name>")
        print("   Ví dụ: python setup_alembic.py orders")
        sys.exit(1)
    
    service_name = sys.argv[1]
    setup_alembic_for_service(service_name)

if __name__ == "__main__":
    main()
