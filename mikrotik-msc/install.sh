#!/bin/bash

# Script cài đặt MikroTik Manager/Monitor trên Ubuntu 24.04
# Tác giả: MikroTik Manager/Monitor Team

set -e

# Định nghĩa màu sắc
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Hàm in tiêu đề
print_header() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

# Hàm in thông báo
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Hàm in cảnh báo
print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Hàm in lỗi
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Kiểm tra và cài đặt các gói phụ thuộc
install_dependencies() {
    print_header "Cài đặt các gói phụ thuộc"
    
    print_message "Cập nhật thông tin gói..."
    sudo apt update
    
    print_message "Cài đặt các gói cần thiết..."
    sudo apt install -y python3 python3-pip python3-venv python3-dev \
        postgresql postgresql-contrib libpq-dev \
        nodejs npm git curl

    print_message "Kiểm tra phiên bản Python..."
    python3 --version
    
    print_message "Kiểm tra phiên bản Node.js..."
    node --version
    
    print_message "Kiểm tra phiên bản npm..."
    npm --version
}

# Cài đặt cơ sở dữ liệu PostgreSQL
setup_database() {
    print_header "Cài đặt cơ sở dữ liệu PostgreSQL"
    
    # Khởi động dịch vụ PostgreSQL
    print_message "Khởi động dịch vụ PostgreSQL..."
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    
    # Tạo người dùng và cơ sở dữ liệu
    print_message "Tạo người dùng và cơ sở dữ liệu..."
    
    # Đặt mật khẩu cho người dùng PostgreSQL
    read -sp "Nhập mật khẩu cho người dùng PostgreSQL 'mikrotik_manager': " DB_PASSWORD
    echo ""
    
    # Tạo người dùng và cơ sở dữ liệu với quyền superuser (để thuận tiện cho migration)
    sudo -u postgres psql -c "CREATE USER mikrotik_manager WITH PASSWORD '$DB_PASSWORD' SUPERUSER;"
    sudo -u postgres psql -c "CREATE DATABASE mikrotik_manager WITH OWNER mikrotik_manager;"
    
    print_message "Đã tạo cơ sở dữ liệu 'mikrotik_manager' với người dùng 'mikrotik_manager'"
}

# Cài đặt backend
install_backend() {
    print_header "Cài đặt Backend"
    
    # Di chuyển đến thư mục backend
    cd NetworkMasterControl/web/backend
    
    # Tạo môi trường ảo Python
    print_message "Tạo môi trường ảo Python..."
    python3 -m venv venv
    source venv/bin/activate
    
    # Cài đặt các gói phụ thuộc
    print_message "Cài đặt các gói phụ thuộc Python..."
    pip install -U pip
    pip install fastapi uvicorn[standard] sqlalchemy alembic psycopg2-binary python-dotenv python-jose[cryptography] passlib[bcrypt] websockets routeros-api
    
    # Tạo file .env
    print_message "Tạo file .env..."
    
    if [ -f .env ]; then
        print_warning "File .env đã tồn tại. Tạo bản sao lưu..."
        cp .env .env.backup
    fi
    
    cat > .env << EOF
# Cấu hình cơ sở dữ liệu
DATABASE_URL=postgresql://mikrotik_manager:${DB_PASSWORD}@localhost/mikrotik_manager

# Cấu hình JWT
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Cấu hình server
HOST=0.0.0.0
PORT=8000

# Cấu hình môi trường
ENV=production

# Cấu hình mặc định MikroTik
MIKROTIK_DEFAULT_USERNAME=admin
MIKROTIK_DEFAULT_PASSWORD=
EOF
    
    # Tạo thư mục logs
    print_message "Tạo thư mục logs..."
    mkdir -p logs
    
    # Chạy migration để tạo cấu trúc cơ sở dữ liệu
    print_message "Chạy migration để tạo cấu trúc cơ sở dữ liệu..."
    # Tạo thư mục migrations nếu chưa có
    mkdir -p migrations/versions
    
    # Tạo file env.py cho Alembic
    cat > migrations/env.py << EOF
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))
sys.path.append(BASE_DIR)

# Thêm đường dẫn tới models
from app.database.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url():
    return os.getenv("DATABASE_URL")

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
EOF
    
    # Tạo file alembic.ini
    cat > alembic.ini << EOF
# A generic, single database configuration.

[alembic]
# path to migration scripts
script_location = migrations

# template used to generate migration files
# file_template = %%(rev)s_%%(slug)s

# timezone to use when rendering the date
# within the migration file as well as the filename.
# string value is passed to dateutil.tz.gettz()
# leave blank for localtime
# timezone =

# max length of characters to apply to the
# "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version location specification; this defaults
# to migrations/versions.  When using multiple version
# directories, initial revisions must be specified with --version-path
# version_locations = %(here)s/bar %(here)s/bat migrations/versions

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks=black
# black.type=console_scripts
# black.entrypoint=black
# black.options=-l 79

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
EOF
    
    # Tạo script mako
    mkdir -p migrations/script.py.mako
    cat > migrations/script.py.mako << EOF
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}
EOF
    
    # Tạo migration ban đầu
    print_message "Tạo migration ban đầu..."
    alembic revision --autogenerate -m "Initial migration"
    
    # Chạy migration
    print_message "Chạy migration..."
    alembic upgrade head
    
    # Trở về thư mục gốc
    cd ../../../
    
    print_message "Backend đã được cài đặt thành công!"
}

# Cài đặt frontend
install_frontend() {
    print_header "Cài đặt Frontend"
    
    # Di chuyển đến thư mục frontend
    cd NetworkMasterControl/web/frontend
    
    # Cài đặt các gói phụ thuộc npm
    print_message "Cài đặt các gói phụ thuộc npm..."
    npm install
    
    # Tạo biến môi trường cho frontend
    print_message "Tạo file .env cho frontend..."
    
    if [ -f .env ]; then
        print_warning "File .env đã tồn tại. Tạo bản sao lưu..."
        cp .env .env.backup
    fi
    
    cat > .env << EOF
REACT_APP_API_URL=http://localhost:8000/api
EOF
    
    # Build frontend
    print_message "Build frontend..."
    npm run build
    
    # Trở về thư mục gốc
    cd ../../../
    
    print_message "Frontend đã được cài đặt thành công!"
}

# Tạo service systemd cho backend
create_systemd_services() {
    print_header "Tạo service systemd"
    
    # Lấy đường dẫn tuyệt đối
    APP_DIR=$(pwd)
    
    # Tạo service cho backend
    print_message "Tạo service cho backend..."
    
    cat > mikrotik-manager-backend.service << EOF
[Unit]
Description=MikroTik Manager/Monitor Backend Service
After=network.target postgresql.service

[Service]
User=$(whoami)
Group=$(whoami)
WorkingDirectory=${APP_DIR}/NetworkMasterControl/web/backend
Environment="PATH=${APP_DIR}/NetworkMasterControl/web/backend/venv/bin"
ExecStart=${APP_DIR}/NetworkMasterControl/web/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
EOF
    
    # Cài đặt service
    print_message "Cài đặt service systemd..."
    sudo mv mikrotik-manager-backend.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable mikrotik-manager-backend.service
    sudo systemctl start mikrotik-manager-backend.service
    
    print_message "Service đã được cài đặt và khởi động thành công!"
}

# Cài đặt cấu hình Nginx
setup_nginx() {
    print_header "Cài đặt và cấu hình Nginx"
    
    # Cài đặt Nginx
    print_message "Cài đặt Nginx..."
    sudo apt install -y nginx
    
    # Lấy đường dẫn tuyệt đối
    APP_DIR=$(pwd)
    
    # Tạo cấu hình Nginx
    print_message "Tạo cấu hình Nginx..."
    
    cat > mikrotik-manager.conf << EOF
server {
    listen 80;
    server_name _;

    # Phục vụ frontend từ thư mục build
    location / {
        root ${APP_DIR}/NetworkMasterControl/web/frontend/build;
        index index.html index.htm;
        try_files \$uri \$uri/ /index.html;
    }

    # Proxy API requests đến backend
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    # Proxy WebSocket connections
    location /api/realtime/ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host \$host;
    }
}
EOF
    
    # Cài đặt cấu hình Nginx
    print_message "Cài đặt cấu hình Nginx..."
    sudo mv mikrotik-manager.conf /etc/nginx/sites-available/
    sudo ln -sf /etc/nginx/sites-available/mikrotik-manager.conf /etc/nginx/sites-enabled/
    
    # Kiểm tra cấu hình Nginx
    print_message "Kiểm tra cấu hình Nginx..."
    sudo nginx -t
    
    # Khởi động lại Nginx
    print_message "Khởi động lại Nginx..."
    sudo systemctl restart nginx
    
    print_message "Nginx đã được cấu hình thành công!"
}

# Hoàn tất và hiển thị thông tin
finish_installation() {
    print_header "Cài đặt hoàn tất"
    
    print_message "MikroTik Manager/Monitor đã được cài đặt thành công!"
    print_message "Bạn có thể truy cập ứng dụng qua trình duyệt tại: http://localhost/"
    print_message "API Backend: http://localhost:8000"
    print_message "API Documentation: http://localhost:8000/docs"
    
    print_message "\nCấu hình hệ thống:"
    print_message "- Backend Service: mikrotik-manager-backend.service"
    print_message "- Nginx Configuration: /etc/nginx/sites-available/mikrotik-manager.conf"
    print_message "- Database: PostgreSQL, Database name: mikrotik_manager, User: mikrotik_manager"
    
    print_message "\nĐể xem log của backend:"
    print_message "sudo journalctl -u mikrotik-manager-backend.service -f"
    
    print_message "\nĐể xem log của Nginx:"
    print_message "sudo tail -f /var/log/nginx/error.log"
    
    print_message "\nThank you for using MikroTik Manager/Monitor!"
}

# Hàm chính
main() {
    # Kiểm tra xem script có được chạy bởi root không
    if [[ $EUID -ne 0 ]]; then
        print_warning "Script này cần được chạy với quyền sudo!"
        print_warning "Vui lòng chạy lại với 'sudo ./install.sh'"
        exit 1
    fi
    
    print_header "Bắt đầu cài đặt MikroTik Manager/Monitor"
    
    echo -e "${YELLOW}Script này sẽ cài đặt MikroTik Manager/Monitor trên Ubuntu 24.04.${NC}"
    echo -e "${YELLOW}Bạn có muốn tiếp tục không? (y/n)${NC}"
    read -r confirm
    
    if [[ $confirm != "y" && $confirm != "Y" ]]; then
        print_message "Đã hủy cài đặt."
        exit 0
    fi
    
    # Thực hiện các bước cài đặt
    install_dependencies
    setup_database
    install_backend
    install_frontend
    create_systemd_services
    setup_nginx
    finish_installation
}

# Chạy chương trình chính
main