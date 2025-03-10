#!/usr/bin/env python3
"""
Giám sát nhiều interface trên thiết bị MikroTik
Script này giám sát lưu lượng mạng trên nhiều interface của thiết bị MikroTik cùng lúc
"""

import os
import sys
import time
import json
import logging
import threading
from tabulate import tabulate
from dotenv import load_dotenv

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mikrotik_multi_interface")

# Load biến môi trường
load_dotenv()

# Kiểm tra xem gói routeros-api đã được cài đặt
try:
    import routeros_api
except ImportError:
    logger.error("Không thể import routeros_api. Chạy: pip install routeros-api")
    sys.exit(1)

# Kiểm tra thư viện tabulate
try:
    from tabulate import tabulate
except ImportError:
    logger.error("Không thể import tabulate. Chạy: pip install tabulate")
    print("Đang cài đặt tabulate...")
    os.system("pip install tabulate")
    from tabulate import tabulate


class MikroTikMultiInterfaceMonitor:
    """Lớp giám sát nhiều interface của thiết bị MikroTik."""
    
    def __init__(self, host, username, password):
        """Khởi tạo với thông tin kết nối."""
        self.host = host
        self.username = username
        self.password = password
        self.connection = None
        self.api = None
        self.running = False
        self.interfaces_data = {}  # Dữ liệu về mỗi interface
        self.lock = threading.Lock()  # Lock để đồng bộ hóa truy cập vào data
    
    def connect(self):
        """Kết nối đến thiết bị MikroTik và trả về API object."""
        try:
            # Thiết lập kết nối
            logger.info(f"Đang kết nối đến {self.host}...")
            self.connection = routeros_api.RouterOsApiPool(
                self.host,
                username=self.username,
                password=self.password,
                plaintext_login=True
            )
            self.api = self.connection.get_api()
            logger.info(f"Đã kết nối thành công đến {self.host}")
            return self.api
        except Exception as e:
            logger.error(f"Lỗi kết nối đến {self.host}: {e}")
            return None
    
    def disconnect(self):
        """Ngắt kết nối."""
        if self.connection:
            self.connection.disconnect()
            logger.info(f"Đã ngắt kết nối từ {self.host}")
    
    def get_interfaces(self):
        """Lấy danh sách interfaces đang hoạt động."""
        if not self.api:
            return None
        
        try:
            interfaces = self.api.get_resource('/interface')
            interface_list = interfaces.get()
            
            result = []
            for iface in interface_list:
                # Chỉ lấy các interface đang hoạt động và không bị vô hiệu hóa
                if iface.get('disabled', 'true') == 'false' and iface.get('running', 'false') == 'true':
                    result.append({
                        'name': iface.get('name', 'Unknown'),
                        'type': iface.get('type', 'Unknown'),
                        'running': iface.get('running', 'false'),
                        'disabled': iface.get('disabled', 'true'),
                        'comment': iface.get('comment', '')
                    })
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách interfaces: {e}")
            return None
    
    def get_interface_traffic(self, interface_name):
        """Lấy dữ liệu traffic cho một interface cụ thể."""
        if not self.api:
            return None
        
        try:
            interfaces = self.api.get_resource('/interface')
            iface_data = interfaces.get(name=interface_name)
            
            if iface_data and len(iface_data) > 0:
                current_tx = int(iface_data[0].get('tx-byte', '0'))
                current_rx = int(iface_data[0].get('rx-byte', '0'))
                return current_tx, current_rx
            else:
                return None
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu traffic cho {interface_name}: {e}")
            return None
    
    def monitor_interface(self, interface_name, interval=2):
        """Thread function để giám sát một interface cụ thể."""
        logger.info(f"Bắt đầu giám sát interface {interface_name}")
        
        # Khởi tạo dữ liệu cho interface này
        with self.lock:
            self.interfaces_data[interface_name] = {
                'history': [],
                'previous_values': None,
                'avg_tx': 0,
                'avg_rx': 0,
                'max_tx': 0,
                'max_rx': 0,
                'samples': 0
            }
        
        while self.running:
            # Lấy dữ liệu traffic hiện tại
            traffic_data = self.get_interface_traffic(interface_name)
            
            if traffic_data:
                current_tx, current_rx = traffic_data
                
                # Nếu đã có dữ liệu trước đó, tính toán tốc độ
                with self.lock:
                    previous_values = self.interfaces_data[interface_name]['previous_values']
                    
                    if previous_values:
                        # Tính toán tốc độ dựa trên sự khác biệt
                        tx_bytes = current_tx - previous_values[0]
                        rx_bytes = current_rx - previous_values[1]
                        
                        # Bytes/giây
                        tx_bytes_per_second = tx_bytes / interval
                        rx_bytes_per_second = rx_bytes / interval
                        
                        # Bits/giây (1 byte = 8 bits)
                        tx_bits_per_second = tx_bytes_per_second * 8
                        rx_bits_per_second = rx_bytes_per_second * 8
                        
                        # Chuyển đổi sang KB/s
                        tx_kbps = tx_bits_per_second / 1024
                        rx_kbps = rx_bits_per_second / 1024
                        
                        # Cập nhật dữ liệu
                        self.interfaces_data[interface_name]['history'].append({
                            'time': time.time(),
                            'tx_kbps': tx_kbps,
                            'rx_kbps': rx_kbps
                        })
                        
                        # Giới hạn kích thước lịch sử
                        if len(self.interfaces_data[interface_name]['history']) > 100:
                            self.interfaces_data[interface_name]['history'] = self.interfaces_data[interface_name]['history'][-100:]
                        
                        # Cập nhật thống kê
                        self.interfaces_data[interface_name]['samples'] += 1
                        current_avg_tx = self.interfaces_data[interface_name]['avg_tx']
                        current_avg_rx = self.interfaces_data[interface_name]['avg_rx']
                        samples = self.interfaces_data[interface_name]['samples']
                        
                        # Tính trung bình cập nhật
                        self.interfaces_data[interface_name]['avg_tx'] = (current_avg_tx * (samples - 1) + tx_kbps) / samples
                        self.interfaces_data[interface_name]['avg_rx'] = (current_avg_rx * (samples - 1) + rx_kbps) / samples
                        
                        # Cập nhật giá trị lớn nhất
                        self.interfaces_data[interface_name]['max_tx'] = max(self.interfaces_data[interface_name]['max_tx'], tx_kbps)
                        self.interfaces_data[interface_name]['max_rx'] = max(self.interfaces_data[interface_name]['max_rx'], rx_kbps)
                    
                    # Lưu giá trị hiện tại cho lần sau
                    self.interfaces_data[interface_name]['previous_values'] = (current_tx, current_rx)
            
            # Ngủ đến lần cập nhật tiếp theo
            time.sleep(interval)
        
        logger.info(f"Đã dừng giám sát interface {interface_name}")
    
    def display_statistics(self, interval=2):
        """Thread function để hiển thị thống kê"""
        last_display_time = 0
        
        while self.running:
            current_time = time.time()
            
            # Chỉ hiển thị mỗi interval giây
            if current_time - last_display_time >= interval:
                last_display_time = current_time
                
                # Tạo dữ liệu bảng
                with self.lock:
                    table_data = []
                    for interface_name, data in self.interfaces_data.items():
                        if data['samples'] > 0:
                            latest_tx = 0
                            latest_rx = 0
                            
                            # Lấy giá trị mới nhất nếu có
                            if data['history']:
                                latest = data['history'][-1]
                                latest_tx = latest['tx_kbps']
                                latest_rx = latest['rx_kbps']
                            
                            table_data.append([
                                interface_name,
                                f"{latest_tx:.2f} KB/s",
                                f"{latest_rx:.2f} KB/s",
                                f"{data['avg_tx']:.2f} KB/s",
                                f"{data['avg_rx']:.2f} KB/s",
                                f"{data['max_tx']:.2f} KB/s",
                                f"{data['max_rx']:.2f} KB/s"
                            ])
                
                # Hiển thị bảng
                if table_data:
                    # Xóa màn hình (thích hợp cho môi trường Linux/Mac)
                    os.system('clear' if os.name == 'posix' else 'cls')
                    
                    # Tạo header cho bảng
                    headers = ["Interface", "TX Hiện tại", "RX Hiện tại", 
                              "TX Trung bình", "RX Trung bình", 
                              "TX Lớn nhất", "RX Lớn nhất"]
                    
                    # In bảng
                    print(f"\n=== GIÁM SÁT TRAFFIC TRÊN {self.host} ===")
                    print(f"Thời gian: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(tabulate(table_data, headers=headers, tablefmt="grid"))
                    print(f"Đang giám sát {len(self.interfaces_data)} interface(s). Ấn Ctrl+C để dừng.")
            
            # Ngủ một chút để không tiêu tốn CPU
            time.sleep(0.5)
    
    def start_monitoring(self, interface_names=None, interval=2, duration=None):
        """Bắt đầu giám sát nhiều interface."""
        if not self.api:
            logger.error("Không có kết nối API. Vui lòng kết nối trước.")
            return
        
        # Nếu không chỉ định interface, lấy danh sách và giám sát tất cả
        if not interface_names:
            interfaces = self.get_interfaces()
            if not interfaces or len(interfaces) == 0:
                logger.error("Không tìm thấy interface nào đang hoạt động.")
                return
            
            print("\n=== DANH SÁCH INTERFACES ===")
            for i, iface in enumerate(interfaces):
                status = "Hoạt động" if iface['running'] == 'true' else "Không hoạt động"
                disabled = "Đã vô hiệu hóa" if iface['disabled'] == 'true' else "Đã bật"
                print(f"{i+1}. {iface['name']} ({iface['type']}) - {status}, {disabled}")
            
            # Sử dụng tất cả các interface đang hoạt động
            interface_names = [iface['name'] for iface in interfaces]
            print(f"\nĐã chọn tự động {len(interface_names)} interface để giám sát")
        
        # Bắt đầu giám sát
        self.running = True
        
        # Tạo thread cho mỗi interface
        threads = []
        for interface_name in interface_names:
            thread = threading.Thread(
                target=self.monitor_interface,
                args=(interface_name, interval),
                daemon=True  # Thread sẽ tự động kết thúc khi chương trình chính kết thúc
            )
            thread.start()
            threads.append(thread)
        
        # Tạo thread hiển thị
        display_thread = threading.Thread(
            target=self.display_statistics,
            args=(interval,),
            daemon=True
        )
        display_thread.start()
        
        try:
            # Nếu có thời lượng, chờ đợi và sau đó dừng
            if duration:
                time.sleep(duration)
                self.running = False
                print("\nĐã hoàn thành thời gian giám sát.")
            else:
                # Nếu không, chờ cho đến khi người dùng dừng bằng Ctrl+C
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            print("\nĐã nhận tín hiệu dừng giám sát.")
        finally:
            # Dừng tất cả các thread
            self.running = False
            
            # Chờ cho tất cả các thread kết thúc (với timeout)
            for thread in threads:
                thread.join(timeout=1)
            
            display_thread.join(timeout=1)
            
            # Hiển thị báo cáo cuối cùng
            self.display_final_report()
    
    def display_final_report(self):
        """Hiển thị báo cáo tổng kết sau khi kết thúc giám sát."""
        print("\n=== BÁO CÁO TỔNG KẾT GIÁM SÁT ===")
        
        with self.lock:
            for interface_name, data in self.interfaces_data.items():
                if data['samples'] > 0:
                    print(f"\nInterface: {interface_name}")
                    print(f"Số mẫu đã thu thập: {data['samples']}")
                    print(f"TX trung bình: {data['avg_tx']:.2f} KB/s ({data['avg_tx']/1024:.4f} MB/s)")
                    print(f"RX trung bình: {data['avg_rx']:.2f} KB/s ({data['avg_rx']/1024:.4f} MB/s)")
                    print(f"TX lớn nhất: {data['max_tx']:.2f} KB/s ({data['max_tx']/1024:.4f} MB/s)")
                    print(f"RX lớn nhất: {data['max_rx']:.2f} KB/s ({data['max_rx']/1024:.4f} MB/s)")
        
        # Lưu báo cáo vào file
        self.save_report_to_file()
    
    def save_report_to_file(self):
        """Lưu báo cáo vào file để tham khảo sau."""
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"interface_traffic_report_{timestamp}.json"
            
            # Tạo báo cáo có cấu trúc
            report = {
                'host': self.host,
                'timestamp': timestamp,
                'interfaces': {}
            }
            
            with self.lock:
                for interface_name, data in self.interfaces_data.items():
                    if data['samples'] > 0:
                        report['interfaces'][interface_name] = {
                            'samples': data['samples'],
                            'avg_tx_kbps': data['avg_tx'],
                            'avg_rx_kbps': data['avg_rx'],
                            'max_tx_kbps': data['max_tx'],
                            'max_rx_kbps': data['max_rx'],
                            # Chỉ lưu 50 mẫu gần nhất để file không quá lớn
                            'history': data['history'][-50:] if data['history'] else []
                        }
            
            # Lưu báo cáo vào file
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"\nĐã lưu báo cáo chi tiết vào file: {filename}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu báo cáo: {e}")


def main():
    """Hàm chính để chạy giám sát."""
    # Lấy thông tin kết nối từ biến môi trường
    host = os.getenv('MIKROTIK_HOST')
    username = os.getenv('MIKROTIK_USER')
    password = os.getenv('MIKROTIK_PASSWORD')
    
    if not host or not username or not password:
        logger.error("Không tìm thấy thông tin kết nối MikroTik trong file .env")
        logger.info("Vui lòng kiểm tra file .env và đảm bảo đã cấu hình MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASSWORD")
        sys.exit(1)
    
    # Tạo đối tượng monitor
    monitor = MikroTikMultiInterfaceMonitor(host, username, password)
    
    # Kết nối đến thiết bị
    api = monitor.connect()
    if not api:
        sys.exit(1)
    
    try:
        # Bắt đầu giám sát
        monitor.start_monitoring(interval=2, duration=60)  # Giám sát trong 60 giây
    
    finally:
        # Đảm bảo luôn ngắt kết nối
        monitor.disconnect()


if __name__ == "__main__":
    print("=== MikroTik Multi Interface Monitor ===")
    main()