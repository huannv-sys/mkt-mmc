#!/usr/bin/env python3
"""
Logger lưu trữ và phân tích dữ liệu traffic MikroTik
Script này thu thập và lưu trữ dữ liệu traffic từ thiết bị MikroTik vào cơ sở dữ liệu SQLite
"""

import os
import sys
import time
import json
import sqlite3
import logging
import argparse
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mikrotik_traffic_logger")

# Load biến môi trường
load_dotenv()

# Kiểm tra xem gói routeros-api đã được cài đặt
try:
    import routeros_api
except ImportError:
    logger.error("Không thể import routeros_api. Chạy: pip install routeros-api")
    sys.exit(1)


class MikroTikTrafficLogger:
    """Lớp thu thập và lưu trữ dữ liệu traffic từ MikroTik."""
    
    def __init__(self, host, username, password, db_file='mikrotik_traffic.db'):
        """Khởi tạo với thông tin kết nối và database."""
        self.host = host
        self.username = username
        self.password = password
        self.connection = None
        self.api = None
        self.db_file = db_file
        self.running = False
        self.interfaces_data = {}  # Dữ liệu về mỗi interface
        
        # Tạo cơ sở dữ liệu nếu chưa tồn tại
        self.init_database()
    
    def init_database(self):
        """Khởi tạo cơ sở dữ liệu SQLite."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Tạo bảng lưu trữ thông tin thiết bị
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT,
                ip_address TEXT,
                model TEXT,
                ros_version TEXT,
                last_seen TIMESTAMP
            )
            ''')
            
            # Tạo bảng lưu trữ thông tin interface
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS interfaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER,
                name TEXT,
                type TEXT,
                mac_address TEXT,
                FOREIGN KEY (device_id) REFERENCES devices (id)
            )
            ''')
            
            # Tạo bảng lưu trữ dữ liệu traffic
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS traffic_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interface_id INTEGER,
                timestamp TIMESTAMP,
                tx_bytes BIGINT,
                rx_bytes BIGINT,
                tx_packets INTEGER,
                rx_packets INTEGER,
                tx_rate_kbps REAL,
                rx_rate_kbps REAL,
                FOREIGN KEY (interface_id) REFERENCES interfaces (id)
            )
            ''')
            
            # Tạo bảng lưu trữ thống kê hàng ngày
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interface_id INTEGER,
                date DATE,
                avg_tx_kbps REAL,
                avg_rx_kbps REAL,
                max_tx_kbps REAL,
                max_rx_kbps REAL,
                total_tx_mb REAL,
                total_rx_mb REAL,
                FOREIGN KEY (interface_id) REFERENCES interfaces (id)
            )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"Đã khởi tạo cơ sở dữ liệu {self.db_file}")
        
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo cơ sở dữ liệu: {e}")
            sys.exit(1)
    
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
            
            # Lưu thông tin thiết bị vào database
            self.store_device_info()
            
            return self.api
        except Exception as e:
            logger.error(f"Lỗi kết nối đến {self.host}: {e}")
            return None
    
    def disconnect(self):
        """Ngắt kết nối."""
        if self.connection:
            self.connection.disconnect()
            logger.info(f"Đã ngắt kết nối từ {self.host}")
    
    def store_device_info(self):
        """Lưu trữ thông tin thiết bị vào database."""
        if not self.api:
            return
        
        try:
            # Lấy thông tin thiết bị
            resource = self.api.get_resource('/system/resource')
            identity = self.api.get_resource('/system/identity')
            
            resource_data = resource.get()[0]
            identity_data = identity.get()[0]
            
            hostname = identity_data.get('name', 'Unknown')
            model = resource_data.get('board-name', 'Unknown')
            ros_version = resource_data.get('version', 'Unknown')
            
            # Kiểm tra xem thiết bị đã tồn tại chưa
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM devices WHERE ip_address = ?", (self.host,))
            existing_device = cursor.fetchone()
            
            if existing_device:
                # Cập nhật thông tin thiết bị hiện có
                device_id = existing_device[0]
                cursor.execute('''
                UPDATE devices 
                SET hostname = ?, model = ?, ros_version = ?, last_seen = CURRENT_TIMESTAMP
                WHERE id = ?
                ''', (hostname, model, ros_version, device_id))
                logger.info(f"Đã cập nhật thông tin thiết bị: {hostname} ({model})")
            else:
                # Thêm thiết bị mới
                cursor.execute('''
                INSERT INTO devices (hostname, ip_address, model, ros_version, last_seen)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (hostname, self.host, model, ros_version))
                device_id = cursor.lastrowid
                logger.info(f"Đã thêm thiết bị mới: {hostname} ({model})")
            
            conn.commit()
            conn.close()
            
            # Lưu thông tin interfaces
            self.store_interfaces_info(device_id)
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu thông tin thiết bị: {e}")
    
    def store_interfaces_info(self, device_id):
        """Lưu trữ thông tin interfaces vào database."""
        if not self.api:
            return
        
        try:
            # Lấy danh sách interfaces
            interfaces = self.api.get_resource('/interface')
            interface_list = interfaces.get()
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            for iface in interface_list:
                name = iface.get('name', 'Unknown')
                iface_type = iface.get('type', 'Unknown')
                mac_address = iface.get('mac-address', '')
                
                # Kiểm tra xem interface đã tồn tại chưa
                cursor.execute(
                    "SELECT id FROM interfaces WHERE device_id = ? AND name = ?", 
                    (device_id, name)
                )
                existing_interface = cursor.fetchone()
                
                if existing_interface:
                    # Cập nhật thông tin interface hiện có
                    interface_id = existing_interface[0]
                    cursor.execute('''
                    UPDATE interfaces 
                    SET type = ?, mac_address = ?
                    WHERE id = ?
                    ''', (iface_type, mac_address, interface_id))
                else:
                    # Thêm interface mới
                    cursor.execute('''
                    INSERT INTO interfaces (device_id, name, type, mac_address)
                    VALUES (?, ?, ?, ?)
                    ''', (device_id, name, iface_type, mac_address))
            
            conn.commit()
            conn.close()
            logger.info(f"Đã lưu thông tin interfaces cho thiết bị {device_id}")
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu thông tin interfaces: {e}")
    
    def get_interface_id(self, interface_name):
        """Lấy ID của interface từ database."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT i.id FROM interfaces i
            JOIN devices d ON i.device_id = d.id
            WHERE d.ip_address = ? AND i.name = ?
            ''', (self.host, interface_name))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            else:
                logger.warning(f"Không tìm thấy interface {interface_name} trong database")
                return None
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy ID interface: {e}")
            return None
    
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
                current_tx_bytes = int(iface_data[0].get('tx-byte', '0'))
                current_rx_bytes = int(iface_data[0].get('rx-byte', '0'))
                current_tx_packets = int(iface_data[0].get('tx-packet', '0'))
                current_rx_packets = int(iface_data[0].get('rx-packet', '0'))
                
                return {
                    'tx_bytes': current_tx_bytes,
                    'rx_bytes': current_rx_bytes,
                    'tx_packets': current_tx_packets,
                    'rx_packets': current_rx_packets
                }
            else:
                return None
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu traffic cho {interface_name}: {e}")
            return None
    
    def monitor_interface(self, interface_name, interval=5):
        """Thread function để giám sát và ghi log một interface cụ thể."""
        logger.info(f"Bắt đầu ghi log traffic cho interface {interface_name}")
        
        # Lấy interface_id
        interface_id = self.get_interface_id(interface_name)
        if not interface_id:
            logger.error(f"Không thể giám sát {interface_name}: không tìm thấy trong database")
            return
        
        # Khởi tạo giá trị trước đó
        previous_data = self.get_interface_traffic(interface_name)
        if not previous_data:
            logger.error(f"Không thể đọc dữ liệu traffic cho {interface_name}")
            return
        
        last_save_time = datetime.now()
        
        while self.running:
            current_time = datetime.now()
            
            # Lấy dữ liệu traffic hiện tại
            current_data = self.get_interface_traffic(interface_name)
            
            if current_data and previous_data:
                # Tính toán tốc độ dựa trên sự khác biệt
                tx_bytes = current_data['tx_bytes'] - previous_data['tx_bytes']
                rx_bytes = current_data['rx_bytes'] - previous_data['rx_bytes']
                tx_packets = current_data['tx_packets'] - previous_data['tx_packets']
                rx_packets = current_data['rx_packets'] - previous_data['rx_packets']
                
                # Bytes/giây
                tx_bytes_per_second = tx_bytes / interval
                rx_bytes_per_second = rx_bytes / interval
                
                # Bits/giây (1 byte = 8 bits)
                tx_bits_per_second = tx_bytes_per_second * 8
                rx_bits_per_second = rx_bytes_per_second * 8
                
                # Chuyển đổi sang KB/s
                tx_kbps = tx_bits_per_second / 1024
                rx_kbps = rx_bits_per_second / 1024
                
                # Lưu vào cơ sở dữ liệu
                self.store_traffic_data(
                    interface_id, 
                    current_time,
                    current_data['tx_bytes'],
                    current_data['rx_bytes'],
                    current_data['tx_packets'],
                    current_data['rx_packets'],
                    tx_kbps,
                    rx_kbps
                )
                
                # In thông tin debug
                logger.debug(f"{interface_name}: TX: {tx_kbps:.2f} KB/s, RX: {rx_kbps:.2f} KB/s")
                
                # Cập nhật thống kê hàng ngày mỗi 15 phút
                if (current_time - last_save_time).total_seconds() >= 900:  # 15 phút
                    self.update_daily_stats(interface_id, current_time.date())
                    last_save_time = current_time
            
            # Lưu giá trị hiện tại cho lần sau
            previous_data = current_data
            
            # Ngủ đến lần cập nhật tiếp theo
            time.sleep(interval)
        
        logger.info(f"Đã dừng ghi log traffic cho interface {interface_name}")
    
    def store_traffic_data(self, interface_id, timestamp, tx_bytes, rx_bytes, tx_packets, rx_packets, tx_rate_kbps, rx_rate_kbps):
        """Lưu dữ liệu traffic vào cơ sở dữ liệu."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO traffic_data 
            (interface_id, timestamp, tx_bytes, rx_bytes, tx_packets, rx_packets, tx_rate_kbps, rx_rate_kbps)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                interface_id, 
                timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                tx_bytes,
                rx_bytes,
                tx_packets,
                rx_packets,
                tx_rate_kbps,
                rx_rate_kbps
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu traffic: {e}")
    
    def update_daily_stats(self, interface_id, date):
        """Cập nhật thống kê hàng ngày."""
        try:
            # Chuyển đổi ngày thành string format
            date_str = date.strftime('%Y-%m-%d')
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Lấy dữ liệu traffic trong ngày
            cursor.execute('''
            SELECT 
                AVG(tx_rate_kbps), 
                AVG(rx_rate_kbps),
                MAX(tx_rate_kbps),
                MAX(rx_rate_kbps),
                (MAX(tx_bytes) - MIN(tx_bytes)) / 1048576.0, -- Đổi thành MB
                (MAX(rx_bytes) - MIN(rx_bytes)) / 1048576.0  -- Đổi thành MB
            FROM traffic_data
            WHERE interface_id = ? AND date(timestamp) = ?
            ''', (interface_id, date_str))
            
            result = cursor.fetchone()
            
            if result and result[0] is not None:
                avg_tx_kbps, avg_rx_kbps, max_tx_kbps, max_rx_kbps, total_tx_mb, total_rx_mb = result
                
                # Kiểm tra xem đã có thống kê cho ngày này chưa
                cursor.execute('''
                SELECT id FROM daily_stats
                WHERE interface_id = ? AND date = ?
                ''', (interface_id, date_str))
                
                existing_stat = cursor.fetchone()
                
                if existing_stat:
                    # Cập nhật thống kê hiện có
                    cursor.execute('''
                    UPDATE daily_stats
                    SET avg_tx_kbps = ?, avg_rx_kbps = ?, 
                        max_tx_kbps = ?, max_rx_kbps = ?,
                        total_tx_mb = ?, total_rx_mb = ?
                    WHERE interface_id = ? AND date = ?
                    ''', (
                        avg_tx_kbps, avg_rx_kbps, 
                        max_tx_kbps, max_rx_kbps,
                        total_tx_mb, total_rx_mb,
                        interface_id, date_str
                    ))
                else:
                    # Thêm thống kê mới
                    cursor.execute('''
                    INSERT INTO daily_stats
                    (interface_id, date, avg_tx_kbps, avg_rx_kbps, max_tx_kbps, max_rx_kbps, total_tx_mb, total_rx_mb)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        interface_id, date_str, 
                        avg_tx_kbps, avg_rx_kbps, 
                        max_tx_kbps, max_rx_kbps,
                        total_tx_mb, total_rx_mb
                    ))
            
            conn.commit()
            conn.close()
            logger.info(f"Đã cập nhật thống kê ngày {date_str} cho interface {interface_id}")
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật thống kê hàng ngày: {e}")
    
    def start_logging(self, interface_names=None, interval=5, duration=None):
        """Bắt đầu ghi log nhiều interface."""
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
            print(f"\nĐã chọn tự động {len(interface_names)} interface để ghi log")
        
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
        
        print(f"\n=== ĐÃ BẮT ĐẦU GHI LOG TRAFFIC ===")
        print(f"Đang ghi log cho {len(interface_names)} interface(s) với chu kỳ {interval} giây")
        print(f"Dữ liệu được lưu vào: {self.db_file}")
        print("Ấn Ctrl+C để dừng ghi log.")
        
        try:
            # Nếu có thời lượng, chờ đợi và sau đó dừng
            if duration:
                time.sleep(duration)
                self.running = False
                print("\nĐã hoàn thành thời gian ghi log.")
            else:
                # Nếu không, chờ cho đến khi người dùng dừng bằng Ctrl+C
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            print("\nĐã nhận tín hiệu dừng ghi log.")
        finally:
            # Dừng tất cả các thread
            self.running = False
            
            # Chờ cho tất cả các thread kết thúc (với timeout)
            for thread in threads:
                thread.join(timeout=1)
            
            print("\n=== THỐNG KÊ GHI LOG ===")
            self.print_logging_stats()
    
    def print_logging_stats(self):
        """In thông tin thống kê về dữ liệu đã ghi log."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Lấy số lượng mẫu đã ghi
            cursor.execute("SELECT COUNT(*) FROM traffic_data")
            total_samples = cursor.fetchone()[0]
            
            # Lấy thời gian mẫu đầu tiên và mẫu cuối cùng
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM traffic_data")
            min_time, max_time = cursor.fetchone()
            
            # Lấy thống kê theo interface
            cursor.execute('''
            SELECT i.name, COUNT(*), AVG(t.tx_rate_kbps), AVG(t.rx_rate_kbps)
            FROM traffic_data t
            JOIN interfaces i ON t.interface_id = i.id
            GROUP BY t.interface_id
            ''')
            interface_stats = cursor.fetchall()
            
            conn.close()
            
            # In thống kê
            print(f"Tổng số mẫu đã ghi: {total_samples}")
            if min_time and max_time:
                print(f"Thời gian bắt đầu: {min_time}")
                print(f"Thời gian kết thúc: {max_time}")
            
            print("\nThống kê theo interface:")
            for name, count, avg_tx, avg_rx in interface_stats:
                print(f"  - {name}: {count} mẫu, TB: {avg_tx:.2f} KB/s (TX), {avg_rx:.2f} KB/s (RX)")
            
            print(f"\nDữ liệu được lưu trong: {self.db_file}")
            print("Sử dụng công cụ phân tích để xem các báo cáo chi tiết và biểu đồ.")
            
        except Exception as e:
            logger.error(f"Lỗi khi in thống kê ghi log: {e}")
    
    def generate_report(self, days=1, output_format='text'):
        """Tạo báo cáo từ dữ liệu đã ghi log."""
        try:
            # Tính toán ngày bắt đầu
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row  # Để truy cập kết quả bằng tên cột
            cursor = conn.cursor()
            
            # Lấy thông tin thiết bị
            cursor.execute('''
            SELECT hostname, ip_address, model, ros_version
            FROM devices 
            WHERE ip_address = ?
            ''', (self.host,))
            device = cursor.fetchone()
            
            if not device:
                print(f"Không tìm thấy thông tin thiết bị {self.host} trong database")
                return
            
            # Lấy thống kê hàng ngày cho mỗi interface
            cursor.execute('''
            SELECT 
                i.name,
                ds.date,
                ds.avg_tx_kbps,
                ds.avg_rx_kbps,
                ds.max_tx_kbps,
                ds.max_rx_kbps,
                ds.total_tx_mb,
                ds.total_rx_mb
            FROM daily_stats ds
            JOIN interfaces i ON ds.interface_id = i.id
            JOIN devices d ON i.device_id = d.id
            WHERE d.ip_address = ? AND ds.date BETWEEN ? AND ?
            ORDER BY ds.date DESC, i.name
            ''', (self.host, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            daily_stats = cursor.fetchall()
            
            # Tính tổng lưu lượng cho mỗi interface
            cursor.execute('''
            SELECT 
                i.name,
                SUM(ds.total_tx_mb) as total_tx,
                SUM(ds.total_rx_mb) as total_rx
            FROM daily_stats ds
            JOIN interfaces i ON ds.interface_id = i.id
            JOIN devices d ON i.device_id = d.id
            WHERE d.ip_address = ? AND ds.date BETWEEN ? AND ?
            GROUP BY i.id
            ORDER BY i.name
            ''', (self.host, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            interface_totals = cursor.fetchall()
            
            conn.close()
            
            # Tạo báo cáo
            if output_format == 'text':
                self.print_text_report(device, daily_stats, interface_totals, days)
            elif output_format == 'json':
                return self.generate_json_report(device, daily_stats, interface_totals, days)
            else:
                print(f"Định dạng báo cáo không hỗ trợ: {output_format}")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo: {e}")
    
    def print_text_report(self, device, daily_stats, interface_totals, days):
        """In báo cáo dạng text."""
        print("\n" + "="*80)
        print(f"BÁO CÁO TRAFFIC MIKROTIK - {days} NGÀY GẦN NHẤT")
        print("="*80)
        print(f"Thiết bị: {device['hostname']} ({device['ip_address']})")
        print(f"Model: {device['model']}")
        print(f"RouterOS: {device['ros_version']}")
        print("-"*80)
        
        # In tổng lưu lượng theo interface
        print("\nTỔNG LƯU LƯỢNG THEO INTERFACE:")
        for iface in interface_totals:
            print(f"  - {iface['name']}: {iface['total_tx']:.2f} MB (TX), {iface['total_rx']:.2f} MB (RX)")
        
        # In thống kê hàng ngày
        if daily_stats:
            print("\nTHỐNG KÊ HÀNG NGÀY:")
            current_date = None
            
            for stat in daily_stats:
                if current_date != stat['date']:
                    current_date = stat['date']
                    print(f"\n  {current_date}:")
                
                print(f"    {stat['name']}: Trung bình {stat['avg_tx_kbps']:.2f}/{stat['avg_rx_kbps']:.2f} KB/s (TX/RX), " +
                      f"Cao nhất {stat['max_tx_kbps']:.2f}/{stat['max_rx_kbps']:.2f} KB/s, " +
                      f"Tổng {stat['total_tx_mb']:.2f}/{stat['total_rx_mb']:.2f} MB")
        else:
            print("\nKhông có dữ liệu thống kê hàng ngày.")
        
        print("\n" + "="*80)
    
    def generate_json_report(self, device, daily_stats, interface_totals, days):
        """Tạo báo cáo dạng JSON."""
        report = {
            'report_type': 'MikroTik Traffic Report',
            'period': f'{days} days',
            'device': {
                'hostname': device['hostname'],
                'ip_address': device['ip_address'],
                'model': device['model'],
                'ros_version': device['ros_version']
            },
            'interface_totals': [],
            'daily_stats': []
        }
        
        # Thêm tổng lưu lượng theo interface
        for iface in interface_totals:
            report['interface_totals'].append({
                'name': iface['name'],
                'total_tx_mb': round(iface['total_tx'], 2),
                'total_rx_mb': round(iface['total_rx'], 2)
            })
        
        # Thêm thống kê hàng ngày
        current_date = None
        daily_entry = None
        
        for stat in daily_stats:
            date = stat['date']
            
            if current_date != date:
                current_date = date
                daily_entry = {
                    'date': date,
                    'interfaces': []
                }
                report['daily_stats'].append(daily_entry)
            
            daily_entry['interfaces'].append({
                'name': stat['name'],
                'avg_tx_kbps': round(stat['avg_tx_kbps'], 2),
                'avg_rx_kbps': round(stat['avg_rx_kbps'], 2),
                'max_tx_kbps': round(stat['max_tx_kbps'], 2),
                'max_rx_kbps': round(stat['max_rx_kbps'], 2),
                'total_tx_mb': round(stat['total_tx_mb'], 2),
                'total_rx_mb': round(stat['total_rx_mb'], 2)
            })
        
        return report


def main():
    """Hàm chính để chạy logger."""
    parser = argparse.ArgumentParser(description='MikroTik Traffic Logger')
    parser.add_argument('--log', action='store_true', help='Ghi log dữ liệu traffic')
    parser.add_argument('--report', action='store_true', help='Tạo báo cáo từ dữ liệu đã ghi log')
    parser.add_argument('--days', type=int, default=1, help='Số ngày để tạo báo cáo (mặc định: 1)')
    parser.add_argument('--interval', type=int, default=5, help='Chu kỳ ghi log in giây (mặc định: 5)')
    parser.add_argument('--db', type=str, default='mikrotik_traffic.db', help='Tên file database (mặc định: mikrotik_traffic.db)')
    parser.add_argument('--json', action='store_true', help='Xuất báo cáo dạng JSON thay vì text')
    parser.add_argument('--duration', type=int, help='Thời gian ghi log (giây), nếu không cung cấp thì ghi đến khi bị dừng')
    args = parser.parse_args()
    
    # Lấy thông tin kết nối từ biến môi trường
    host = os.getenv('MIKROTIK_HOST')
    username = os.getenv('MIKROTIK_USER')
    password = os.getenv('MIKROTIK_PASSWORD')
    
    if not host or not username or not password:
        logger.error("Không tìm thấy thông tin kết nối MikroTik trong file .env")
        logger.info("Vui lòng kiểm tra file .env và đảm bảo đã cấu hình MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASSWORD")
        sys.exit(1)
    
    # Tạo đối tượng logger
    traffic_logger = MikroTikTrafficLogger(host, username, password, db_file=args.db)
    
    # Nếu chỉ tạo báo cáo thì không cần kết nối
    if args.report and not args.log:
        print(f"=== TẠO BÁO CÁO TRAFFIC MIKROTIK ===")
        traffic_logger.generate_report(days=args.days, output_format='json' if args.json else 'text')
        return
    
    # Kết nối đến thiết bị
    api = traffic_logger.connect()
    if not api:
        sys.exit(1)
    
    try:
        if args.log:
            # Bắt đầu ghi log
            traffic_logger.start_logging(interval=args.interval, duration=args.duration)
        
        if args.report:
            # Tạo báo cáo
            traffic_logger.generate_report(days=args.days, output_format='json' if args.json else 'text')
    
    finally:
        # Đảm bảo luôn ngắt kết nối
        traffic_logger.disconnect()


if __name__ == "__main__":
    print("=== MikroTik Traffic Logger ===")
    main()