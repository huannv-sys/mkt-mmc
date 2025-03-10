# Alembic Migrations

Thư mục này chứa các file migration cho schema cơ sở dữ liệu.

## Cách sử dụng

1. Khởi tạo Alembic:
    ```sh
    alembic init migrations
    ```

2. Tạo migration mới:
    ```sh
    alembic revision --autogenerate -m "Tên migration"
    ```

3. Áp dụng migration:
    ```sh
    alembic upgrade head
    ```

4. Quay lại migration trước đó:
    ```sh
    alembic downgrade -1
    ```

Đảm bảo bạn đã cấu hình Alembic để kết nối với cơ sở dữ liệu trong `alembic.ini`.