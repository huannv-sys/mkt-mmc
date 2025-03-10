#!/bin/bash

# Script đóng gói MikroTik Manager/Monitor
# Tác giả: MikroTik Manager/Monitor Team

# Định nghĩa màu sắc
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Tạo thư mục tạm để chứa các file cần thiết
print_message "Tạo thư mục tạm..."
TEMP_DIR="./mikrotik-manager-monitor-package"
mkdir -p $TEMP_DIR

# Sao chép các file và thư mục cần thiết
print_message "Sao chép các file và thư mục cần thiết..."

# Sao chép thư mục NetworkMasterControl
mkdir -p $TEMP_DIR/NetworkMasterControl
cp -r NetworkMasterControl/web $TEMP_DIR/NetworkMasterControl/
cp -r NetworkMasterControl/scripts $TEMP_DIR/NetworkMasterControl/
cp -r NetworkMasterControl/app $TEMP_DIR/NetworkMasterControl/

# Sao chép các file cài đặt
cp install.sh $TEMP_DIR/
cp README-INSTALL.md $TEMP_DIR/README.md
cp LICENSE $TEMP_DIR/ 2>/dev/null || print_warning "Không tìm thấy file LICENSE"

# Sao chép các file tài liệu
mkdir -p $TEMP_DIR/docs
cp *.md $TEMP_DIR/docs/ 2>/dev/null

# Tạo thư mục logs và cấu hình
mkdir -p $TEMP_DIR/NetworkMasterControl/web/backend/logs
mkdir -p $TEMP_DIR/NetworkMasterControl/web/backend/migrations/versions

# Đảm bảo script cài đặt có quyền thực thi
chmod +x $TEMP_DIR/install.sh

# Tạo file .gitignore
cat > $TEMP_DIR/.gitignore << EOF
*.pyc
__pycache__/
*.pyo
*.pyd
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg
node_modules/
.env
.env.local
.env.development.local
.env.test.local
.env.production.local
npm-debug.log*
yarn-debug.log*
yarn-error.log*
logs/*.log
*.log
.DS_Store
EOF

# Đóng gói thành file tar.gz
print_message "Đóng gói thành file tar.gz..."
tar -czf mikrotik-manager-monitor.tar.gz -C $TEMP_DIR .

# Xóa thư mục tạm
print_message "Xóa thư mục tạm..."
rm -rf $TEMP_DIR

print_message "Đã tạo gói cài đặt: mikrotik-manager-monitor.tar.gz"
print_message "Kích thước gói: $(du -h mikrotik-manager-monitor.tar.gz | cut -f1)"
print_message "Hoàn tất!"