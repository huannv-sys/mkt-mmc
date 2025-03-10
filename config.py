"""
Tập tin cấu hình cho MikroTik MSC
Chứa các hằng số và cấu hình toàn cục cho hệ thống
"""

import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình Flask
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# Cấu hình JWT
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key')
JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 giờ

# Cấu hình MikroTik
MIKROTIK_HOST = os.getenv('MIKROTIK_HOST', '192.168.88.1')
MIKROTIK_USERNAME = os.getenv('MIKROTIK_USERNAME', 'admin')
MIKROTIK_PASSWORD = os.getenv('MIKROTIK_PASSWORD', '')

# Cấu hình Twilio
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Cấu hình SMTP
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
DEFAULT_ADMIN_EMAIL = os.getenv('DEFAULT_ADMIN_EMAIL', 'admin@example.com')

# Cấu hình cơ sở dữ liệu
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ip_monitoring.db')

# Cấu hình logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', 'app.log')

# Cấu hình session
SESSION_TYPE = 'filesystem'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Thư mục uploads
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv'}

# Thời gian chờ kết nối MikroTik
MIKROTIK_TIMEOUT = 10  # Seconds
MIKROTIK_API_PORT = 8728
MIKROTIK_API_SSL_PORT = 8729

# Cấu hình cache
CACHE_TYPE = 'filesystem'
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes

# Tạo các thư mục cần thiết
for directory in [os.path.dirname(LOG_FILE), UPLOAD_FOLDER, CACHE_DIR]:
    os.makedirs(directory, exist_ok=True)