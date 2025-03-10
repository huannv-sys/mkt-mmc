#!/usr/bin/env python3
"""
Giám sát traffic MikroTik với biểu đồ
Script này giám sát lưu lượng mạng trên một interface của thiết bị MikroTik và hiển thị biểu đồ
"""

import os
import sys
import time
import json
import logging
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from dotenv import load_dotenv

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mikrotik_chart_monitor")

# Load biến môi trường
load_dotenv()

# Kiểm tra xem gói routeros-api đã được cài đặt
try:
    import routeros_api
except ImportError:
    logger.error("Không thể import routeros_api. Chạy: pip install routeros-api")
    sys.exit(1)


class MikroTikChartMonitor:
    """Lớp giám sát traffic trên interface của thiết bị MikroTik với biểu đồ."""
    
    def __init__(self, host, username, password):
        """Khởi tạo với thông tin kết nối."""
        self.host = host
        self.username = username
        self.password = password
        self.connection = None
        self.api = None
        self.selected_interface = None
        
        # Dữ liệu cho biểu đồ
        self.times = []
        self.tx_values = []
        self.rx_values = []
        
        # Settings
        self.max_points = 30  # Số điểm tối đa trên biểu đồ
        self.interval = 2  # Giây
    
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
        """Lấy danh sách interfaces."""
        if not self.api:
            return None
        
        try:
            interfaces = self.api.get_resource('/interface')
            interface_list = interfaces.get()
            
            result = []
            for iface in interface_list:
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
    
    def get_traffic_data(self):
        """Lấy dữ liệu traffic từ interface đã chọn."""
        if not self.api or not self.selected_interface:
            return None
        
        try:
            # Lấy resource interfaces
            interfaces = self.api.get_resource('/interface')
            
            # Lấy thông tin hiện tại của interface
            iface_data = interfaces.get(name=self.selected_interface)
            
            if iface_data and len(iface_data) > 0:
                current_tx = int(iface_data[0].get('tx-byte', '0'))
                current_rx = int(iface_data[0].get('rx-byte', '0'))
                return current_tx, current_rx
            else:
                return None
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu traffic: {e}")
            return None
    
    def setup_chart(self):
        """Thiết lập biểu đồ ban đầu."""
        plt.style.use('seaborn-v0_8-darkgrid')
        self.fig, self.ax = plt.subplots(figsize=(12, 6))
        self.fig.suptitle(f'Giám sát Traffic Interface {self.selected_interface} - {self.host}', fontsize=14)
        
        # Khởi tạo đường cho TX và RX
        self.tx_line, = self.ax.plot([], [], 'r-', label='TX (KB/s)', linewidth=2)
        self.rx_line, = self.ax.plot([], [], 'b-', label='RX (KB/s)', linewidth=2)
        
        # Thiết lập trục và khung
        self.ax.set_xlabel('Thời gian (giây)')
        self.ax.set_ylabel('Tốc độ (KB/s)')
        self.ax.set_title(f'Tốc độ mạng theo thời gian')
        self.ax.legend(loc='upper left')
        self.ax.grid(True)
        
        # Khởi tạo trục x và y
        self.ax.set_xlim(0, self.max_points * self.interval)
        self.ax.set_ylim(0, 10)  # Sẽ được điều chỉnh tự động
        
        return self.fig
    
    def update_chart(self, frame):
        """Cập nhật biểu đồ với dữ liệu mới."""
        # Lấy dữ liệu mới
        data = self.get_traffic_data()
        if not data:
            return self.tx_line, self.rx_line
        
        current_tx, current_rx = data
        
        # Thêm vào mảng dữ liệu
        if len(self.times) > 0:
            # Tính toán tốc độ dựa trên sự khác biệt
            time_diff = self.interval
            tx_bytes = current_tx - self.last_tx
            rx_bytes = current_rx - self.last_rx
            
            # Bytes/giây
            tx_bytes_per_second = tx_bytes / time_diff
            rx_bytes_per_second = rx_bytes / time_diff
            
            # Bits/giây (1 byte = 8 bits)
            tx_bits_per_second = tx_bytes_per_second * 8
            rx_bits_per_second = rx_bytes_per_second * 8
            
            # Chuyển đổi sang KB/s
            tx_kbps = tx_bits_per_second / 1024
            rx_kbps = rx_bits_per_second / 1024
            
            # Thêm vào mảng dữ liệu
            current_time = len(self.times) * self.interval
            self.times.append(current_time)
            self.tx_values.append(tx_kbps)
            self.rx_values.append(rx_kbps)
            
            # Giới hạn số lượng điểm
            if len(self.times) > self.max_points:
                self.times = self.times[-self.max_points:]
                self.tx_values = self.tx_values[-self.max_points:]
                self.rx_values = self.rx_values[-self.max_points:]
            
            # Cập nhật dữ liệu cho đường
            self.tx_line.set_data(self.times, self.tx_values)
            self.rx_line.set_data(self.times, self.rx_values)
            
            # Điều chỉnh trục y để phù hợp với dữ liệu
            max_value = max(max(self.tx_values) if self.tx_values else 0, 
                           max(self.rx_values) if self.rx_values else 0)
            if max_value > 0:
                self.ax.set_ylim(0, max_value * 1.2)  # Thêm 20% lề trên
            
            # Điều chỉnh trục x để cuộn theo thời gian
            if current_time > self.max_points * self.interval:
                self.ax.set_xlim(current_time - self.max_points * self.interval, current_time)
            
            # In thông tin ra console
            print(f"Thời gian: {current_time}s | TX: {tx_kbps:.2f} KB/s | RX: {rx_kbps:.2f} KB/s")
        
        # Lưu giá trị hiện tại cho lần sau
        self.last_tx = current_tx
        self.last_rx = current_rx
        
        if len(self.times) == 0:
            # Lần đầu tiên, chỉ lưu giá trị hiện tại
            self.times.append(0)
            self.tx_values.append(0)
            self.rx_values.append(0)
            self.last_tx = current_tx
            self.last_rx = current_rx
        
        return self.tx_line, self.rx_line
    
    def start_monitoring(self, interface_name=None, interval=2, duration=None):
        """Bắt đầu giám sát và hiển thị biểu đồ."""
        if not self.api:
            logger.error("Không có kết nối API. Vui lòng kết nối trước.")
            return
        
        # Nếu không chỉ định interface, lấy danh sách và chọn cái đầu tiên
        if not interface_name:
            interfaces = self.get_interfaces()
            if not interfaces or len(interfaces) == 0:
                logger.error("Không tìm thấy interface nào đang hoạt động.")
                return
            
            print("\n=== DANH SÁCH INTERFACES ===")
            for i, iface in enumerate(interfaces):
                status = "Hoạt động" if iface['running'] == 'true' else "Không hoạt động"
                disabled = "Đã vô hiệu hóa" if iface['disabled'] == 'true' else "Đã bật"
                print(f"{i+1}. {iface['name']} ({iface['type']}) - {status}, {disabled}")
            
            print("\nĐã tự động chọn interface đầu tiên:", interfaces[0]['name'])
            interface_name = interfaces[0]['name']
        
        self.selected_interface = interface_name
        self.interval = interval
        
        # Khởi tạo biểu đồ
        print(f"\n=== GIÁM SÁT TRAFFIC TRÊN {self.selected_interface} ===")
        fig = self.setup_chart()
        
        # Thiết lập animation
        ani = FuncAnimation(fig, self.update_chart, frames=None, 
                            interval=self.interval*1000, blit=True, cache_frame_data=False, repeat=False)
        
        # Nếu có thời lượng, tự động dừng sau khi hoàn thành
        if duration:
            # Đặt một hẹn giờ để dừng animation
            def close_after_duration():
                time.sleep(duration)
                plt.close(fig)
            
            import threading
            timer_thread = threading.Thread(target=close_after_duration)
            timer_thread.daemon = True
            timer_thread.start()
        
        # Hiển thị biểu đồ
        plt.tight_layout()
        plt.show()
        
        # Sau khi đóng biểu đồ, hiển thị thống kê
        if len(self.tx_values) > 0 and len(self.rx_values) > 0:
            print("\n=== KẾT QUẢ GIÁM SÁT ===")
            print(f"Interface: {self.selected_interface}")
            print(f"Thời gian giám sát: {len(self.tx_values) * self.interval} giây")
            
            # Tính trung bình và giá trị lớn nhất
            avg_tx = sum(self.tx_values) / len(self.tx_values)
            avg_rx = sum(self.rx_values) / len(self.rx_values)
            max_tx = max(self.tx_values)
            max_rx = max(self.rx_values)
            
            print(f"TX trung bình: {avg_tx:.2f} KB/s ({avg_tx/1024:.2f} MB/s)")
            print(f"RX trung bình: {avg_rx:.2f} KB/s ({avg_rx/1024:.2f} MB/s)")
            print(f"TX lớn nhất: {max_tx:.2f} KB/s ({max_tx/1024:.2f} MB/s)")
            print(f"RX lớn nhất: {max_rx:.2f} KB/s ({max_rx/1024:.2f} MB/s)")
            
            # Lưu biểu đồ thành hình ảnh
            plt.figure(figsize=(12, 6))
            plt.plot(self.times, self.tx_values, 'r-', label='TX (KB/s)', linewidth=2)
            plt.plot(self.times, self.rx_values, 'b-', label='RX (KB/s)', linewidth=2)
            plt.xlabel('Thời gian (giây)')
            plt.ylabel('Tốc độ (KB/s)')
            plt.title(f'Tốc độ mạng trên {self.selected_interface} - {self.host}')
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            
            # Tạo tên file với timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"traffic_{self.selected_interface}_{timestamp}.png"
            plt.savefig(filename)
            print(f"Đã lưu biểu đồ vào file: {filename}")


def main():
    """Hàm chính để chạy demo."""
    # Lấy thông tin kết nối từ biến môi trường
    host = os.getenv('MIKROTIK_HOST')
    username = os.getenv('MIKROTIK_USER')
    password = os.getenv('MIKROTIK_PASSWORD')
    
    if not host or not username or not password:
        logger.error("Không tìm thấy thông tin kết nối MikroTik trong file .env")
        logger.info("Vui lòng kiểm tra file .env và đảm bảo đã cấu hình MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASSWORD")
        sys.exit(1)
    
    # Tạo đối tượng monitor
    monitor = MikroTikChartMonitor(host, username, password)
    
    # Kết nối đến thiết bị
    api = monitor.connect()
    if not api:
        sys.exit(1)
    
    try:
        # Bắt đầu giám sát với biểu đồ
        monitor.start_monitoring(interval=2, duration=60)  # Giám sát trong 60 giây
    
    finally:
        # Đảm bảo luôn ngắt kết nối
        monitor.disconnect()


if __name__ == "__main__":
    print("=== MikroTik Interface Traffic Chart Monitor ===")
    main()