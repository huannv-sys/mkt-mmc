# Hướng dẫn cài đặt và cải thiện MikroTik Manager/Monitor

## 1. Hướng dẫn cài đặt

### Yêu cầu hệ thống
- Python 3.7 trở lên
- Quyền truy cập vào MikroTik Router của bạn (API phải được bật)
- PostgreSQL (tuỳ chọn, nếu bạn muốn lưu trữ dữ liệu)

### Bước cài đặt

1. **Clone repository từ GitHub**
   ```bash
   git clone https://github.com/huannv-sys/mikrotik-manager-monitor.git
   cd mikrotik-manager-monitor/NetworkMasterControl
   ```

2. **Cài đặt các gói phụ thuộc**
   ```bash
   pip install -r requirements.txt
   ```

3. **Cài đặt cơ sở dữ liệu** (nếu cần)
   ```bash
   cd app/database/migrations
   python -m alembic upgrade head
   ```

4. **Cấu hình ứng dụng**
   - Tạo file `.env` từ mẫu dưới đây và đặt vào thư mục NetworkMasterControl
   ```
   # Cấu hình bảo mật
   SECRET_KEY=your_secure_secret_key
   
   # Cấu hình kết nối MikroTik
   MIKROTIK_HOST=192.168.88.1
   MIKROTIK_USER=admin
   MIKROTIK_PASSWORD=your_secure_password
   
   # Cấu hình Email cho cảnh báo
   SMTP_SERVER=smtp.example.com
   SMTP_PORT=465
   SMTP_USER=your_email@example.com
   SMTP_PASSWORD=your_email_password
   ALERT_RECIPIENT=recipient@example.com
   
   # Cấu hình cơ sở dữ liệu
   DATABASE_URL=postgresql://user:password@localhost:5432/mikrotik_db
   ```

5. **Chạy ứng dụng**
   ```bash
   # Trở về thư mục NetworkMasterControl
   cd ../../..
   python -m app.main
   ```

6. **Sử dụng Docker** (tuỳ chọn)
   ```bash
   docker-compose up -d
   ```

## 2. Các vấn đề cần cải thiện

### Vấn đề bảo mật

1. **Loại bỏ thông tin xác thực hardcode**
   
   **File: `app/auth/jwt_handler.py`**
   ```python
   # Thay thế:
   SECRET_KEY = "your_secret_key"
   
   # Bằng:
   import os
   from dotenv import load_dotenv

   load_dotenv()
   SECRET_KEY = os.getenv("SECRET_KEY")
   ```

   **File: `app/api/capsman_api.py`**
   ```python
   # Thay thế:
   capsman_api = CAPsMANAPI(base_url="http://192.168.88.1", username="admin", password="password")
   
   # Bằng:
   import os
   from dotenv import load_dotenv

   load_dotenv()
   capsman_api = CAPsMANAPI(
       base_url=f"http://{os.getenv('MIKROTIK_HOST')}", 
       username=os.getenv("MIKROTIK_USER"), 
       password=os.getenv("MIKROTIK_PASSWORD")
   )
   ```

   **File: `app/smnp/alerts.py`**
   ```python
   # Thay thế:
   from_email = "your_email@example.com"
   password = "your_password"
   
   # Bằng:
   import os
   from dotenv import load_dotenv

   load_dotenv()
   from_email = os.getenv("SMTP_USER")
   password = os.getenv("SMTP_PASSWORD")
   ```

2. **Sử dụng biến môi trường**
   - Cài đặt thư viện python-dotenv
   ```bash
   pip install python-dotenv
   ```
   - Cập nhật requirements.txt
   ```
   requests==2.28.1
   pysnmp==4.4.12
   sqlalchemy==1.4.46
   PyJWT==2.6.0
   pyyaml==6.0
   python-dotenv==0.21.0
   ```

### Vấn đề phụ thuộc

1. **Cập nhật requirements.txt với phiên bản cụ thể**
   ```
   requests==2.28.1
   pysnmp==4.4.12
   sqlalchemy==1.4.46
   PyJWT==2.6.0
   pyyaml==6.0
   ```

2. **Tạo môi trường ảo**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Trên Linux/Mac
   venv\Scripts\activate  # Trên Windows
   ```

### Cải thiện code

1. **Thêm logging thay vì print**
   ```python
   import logging

   # Cấu hình logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       filename='mikrotik_manager.log'
   )
   logger = logging.getLogger("mikrotik")

   # Thay thế print bằng logger
   # Thay: print("Some message")
   # Bằng: logger.info("Some message")
   ```

2. **Loại bỏ code debug trong production**
   - Sử dụng biến môi trường để bật/tắt chế độ debug
   ```python
   import os

   DEBUG = os.getenv("DEBUG", "False").lower() == "true"

   if DEBUG:
       # Chỉ chạy code debug khi DEBUG=True
       print("Debug message")
   ```

3. **Sử dụng try-except phù hợp**
   ```python
   try:
       # Code có thể gây lỗi
       result = some_function()
   except Exception as e:
       logger.error(f"Error occurred: {e}")
       # Xử lý lỗi một cách phù hợp
   ```

## 3. Hướng dẫn kiểm tra

1. **Kiểm tra kết nối MikroTik**
   ```bash
   python -m scripts.test_connection
   ```

2. **Kiểm tra cơ sở dữ liệu**
   ```bash
   python -m scripts.test_database
   ```

3. **Kiểm tra cảnh báo**
   ```bash
   python -m scripts.test_alerts
   ```

## 4. Giải quyết lỗi phổ biến

### Lỗi kết nối đến MikroTik
- Đảm bảo router có thể truy cập được qua mạng
- Kiểm tra API đã được bật trên router
- Xác minh thông tin đăng nhập chính xác

### Lỗi cơ sở dữ liệu
- Kiểm tra PostgreSQL đang chạy
- Kiểm tra user và mật khẩu chính xác
- Kiểm tra URL cơ sở dữ liệu có đúng định dạng

### Lỗi cảnh báo email
- Kiểm tra cấu hình SMTP (server, port)
- Kích hoạt "Ứng dụng kém an toàn" nếu sử dụng Gmail
- Kiểm tra tường lửa có chặn port SMTP hay không