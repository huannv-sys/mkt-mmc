<<<<<<< HEAD
<<<<<<< HEAD
# MikroTik Manager/Monitor

Đây là ứng dụng quản lý và giám sát thiết bị MikroTik toàn diện, giúp theo dõi lưu lượng mạng, quản lý thiết bị và phân tích dữ liệu traffic theo thời gian thực.

## Tính năng chính

### 1. Giám sát traffic interface
- Theo dõi lưu lượng (TX/RX) trên các interface của thiết bị MikroTik
- Hiển thị tốc độ truyền dữ liệu theo thời gian thực
- Tính toán tốc độ trung bình, cao nhất và tổng lưu lượng

### 2. Hiển thị biểu đồ trực quan
- Biểu đồ dòng thời gian hiển thị traffic theo thời gian thực
- Hỗ trợ hiệu ứng động với dữ liệu cập nhật liên tục
- Tùy chỉnh khoảng thời gian hiển thị và lưu biểu đồ

### 3. Giám sát nhiều interface
- Theo dõi đồng thời nhiều interface trên cùng một thiết bị
- Hiển thị bảng so sánh lưu lượng giữa các interface
- Thống kê tổng hợp về hiệu suất từng interface

### 4. Ghi log và phân tích dữ liệu
- Lưu trữ dữ liệu traffic vào cơ sở dữ liệu SQLite
- Thu thập thông tin về thiết bị, interfaces và lưu lượng mạng
- Tạo báo cáo tổng hợp theo ngày, tuần, tháng

### 5. Web interface theo dõi thời gian thực
- Giao diện web hiển thị thông tin thiết bị và traffic
- Cập nhật dữ liệu theo thời gian thực qua WebSocket
- Tương thích với mọi trình duyệt và thiết bị

### 6. Phân tích dữ liệu lịch sử
- Công cụ phân tích dữ liệu từ cơ sở dữ liệu
- Tạo biểu đồ và báo cáo từ dữ liệu lịch sử
- Xuất dữ liệu sang định dạng JSON để phân tích nâng cao

### 7. Quản lý VPN toàn diện
- Hỗ trợ nhiều loại VPN: IPSec, OpenVPN, L2TP, PPTP, SSTP
- Thiết lập, cấu hình và quản lý các kết nối VPN
- Tạo tunnel site-to-site và quản lý người dùng VPN
- Giám sát các kết nối VPN đang hoạt động

## Bắt đầu sử dụng

### Kiểm tra kết nối MikroTik
```
python test_mikrotik.py
```

### Giám sát traffic trên một interface
```
python demo_interface_traffic.py
```

### Hiển thị biểu đồ traffic theo thời gian thực
```
python mikrotik_chart_monitor.py
```

### Giám sát nhiều interface cùng lúc
```
python mikrotik_multi_interface_monitor.py
```

### Ghi log traffic vào cơ sở dữ liệu
```
python mikrotik_traffic_logger.py --log --duration 30
```

### Khởi động web interface
```
python mikrotik_web_monitor.py
```

### Phân tích dữ liệu từ cơ sở dữ liệu
```
python mikrotik_db_analyzer.py info
python mikrotik_db_analyzer.py devices
python mikrotik_db_analyzer.py interfaces
```

### Quản lý VPN
```
python mikrotik_vpn_manager.py list
python mikrotik_vpn_manager.py ipsec-site --remote-gateway 192.168.1.1 --local-subnet 10.0.0.0/24 --remote-subnet 172.16.0.0/24 --shared-key your_key
python mikrotik_vpn_manager.py ovpn-server --name server1 --port 1194
python mikrotik_vpn_manager.py add-user --name user1 --password pass1 --service any
```

## Tài liệu tham khảo

- **[Phân tích dự án](mikrotik_analysis_summary.md)** - Tổng quan về cấu trúc và tính năng
- **[Hướng dẫn cài đặt](installation_guide.md)** - Các bước cài đặt chi tiết
- **[Vấn đề bảo mật](van_de_bao_mat.md)** - Thông tin về bảo mật và các biện pháp bảo vệ

## Cấu hình
Sử dụng file `.env` để cấu hình kết nối đến thiết bị MikroTik:
```
MIKROTIK_HOST=địa_chỉ_ip
MIKROTIK_USER=tên_người_dùng
MIKROTIK_PASSWORD=mật_khẩu
```

## Yêu cầu hệ thống
- Python 3.8 trở lên
- RouterOS 6.x hoặc 7.x
- Các thư viện: routeros-api, matplotlib, tabulate, fastapi, uvicorn, websockets, python-dotenv

## Đóng góp
Mọi đóng góp đều được đánh giá cao! Vui lòng tạo issue hoặc pull request để cải thiện ứng dụng.

## Giấy phép
[MIT](LICENSE)
=======
# Mmc
>>>>>>> 1209f38a7bfdf37baa9c6ea92ea6b8388f6360c8
=======
# mikrotik-msc
>>>>>>> f7cf2fa1d26cd4a8cdb55693d9d3cdd7d08c434f
