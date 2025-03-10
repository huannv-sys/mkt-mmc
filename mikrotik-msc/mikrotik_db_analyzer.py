#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Công cụ phân tích cơ sở dữ liệu MikroTik
Script này đọc và phân tích dữ liệu từ cơ sở dữ liệu mikrotik_traffic.db
"""

import os
import sys
import sqlite3
import argparse
import datetime
import json
from tabulate import tabulate
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates


class Colors:
    """Màu sắc cho đầu ra terminal."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class MikroTikDBAnalyzer:
    """Lớp phân tích cơ sở dữ liệu traffic MikroTik."""

    def __init__(self, db_path='mikrotik_traffic.db'):
        """Khởi tạo với đường dẫn cơ sở dữ liệu."""
        self.db_path = db_path
        
        # Kiểm tra file cơ sở dữ liệu tồn tại
        if not os.path.exists(db_path):
            print(f"{Colors.RED}Lỗi: Không tìm thấy file cơ sở dữ liệu {db_path}{Colors.ENDC}")
            sys.exit(1)
            
        try:
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"{Colors.RED}Lỗi khi kết nối đến cơ sở dữ liệu: {e}{Colors.ENDC}")
            sys.exit(1)
            
        # Kiểm tra cấu trúc cơ sở dữ liệu
        self._check_database_structure()

    def _check_database_structure(self):
        """Kiểm tra các bảng cần thiết có tồn tại không."""
        required_tables = ['devices', 'interfaces', 'traffic_data', 'daily_stats']
        
        # Lấy danh sách các bảng hiện có
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = {row['name'] for row in self.cursor.fetchall()}
        
        # Kiểm tra các bảng cần thiết
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            print(f"{Colors.WARNING}Cảnh báo: Các bảng sau đang thiếu trong cơ sở dữ liệu: {', '.join(missing_tables)}{Colors.ENDC}")
            print(f"{Colors.WARNING}Cơ sở dữ liệu có thể đang bị hỏng hoặc không được khởi tạo đúng.{Colors.ENDC}")

    def get_device_info(self):
        """Lấy thông tin về các thiết bị được ghi log."""
        try:
            self.cursor.execute("SELECT * FROM devices")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"{Colors.RED}Lỗi khi truy vấn bảng devices: {e}{Colors.ENDC}")
            return []

    def get_interfaces(self, device_id=None):
        """Lấy thông tin về các interfaces được ghi log."""
        try:
            if device_id:
                self.cursor.execute("SELECT * FROM interfaces WHERE device_id = ?", (device_id,))
            else:
                self.cursor.execute("SELECT * FROM interfaces")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"{Colors.RED}Lỗi khi truy vấn bảng interfaces: {e}{Colors.ENDC}")
            return []

    def get_traffic_data(self, interface_id, start_time=None, end_time=None, limit=100):
        """Lấy dữ liệu traffic cho một interface cụ thể."""
        try:
            query = "SELECT * FROM traffic_data WHERE interface_id = ?"
            params = [interface_id]
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
                
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
                
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"{Colors.RED}Lỗi khi truy vấn bảng traffic_data: {e}{Colors.ENDC}")
            return []

    def get_daily_stats(self, interface_id=None, days=7):
        """Lấy thống kê hàng ngày cho một hoặc tất cả các interfaces."""
        try:
            if interface_id:
                query = """
                SELECT i.name as interface_name, ds.* 
                FROM daily_stats ds
                JOIN interfaces i ON ds.interface_id = i.id
                WHERE ds.interface_id = ?
                ORDER BY ds.date DESC
                LIMIT ?
                """
                self.cursor.execute(query, (interface_id, days))
            else:
                query = """
                SELECT i.name as interface_name, ds.* 
                FROM daily_stats ds
                JOIN interfaces i ON ds.interface_id = i.id
                ORDER BY ds.date DESC, ds.interface_id
                LIMIT ?
                """
                self.cursor.execute(query, (days * 10,))  # Giả sử không quá 10 interfaces
            
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"{Colors.RED}Lỗi khi truy vấn bảng daily_stats: {e}{Colors.ENDC}")
            return []

    def get_traffic_summary(self, days=7):
        """Lấy tổng hợp lưu lượng cho tất cả các interfaces."""
        try:
            # Tính ngày bắt đầu
            start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            
            query = """
            SELECT 
                i.name as interface_name,
                SUM(total_tx_bytes) as total_tx_bytes,
                SUM(total_rx_bytes) as total_rx_bytes,
                MAX(max_tx_rate) as max_tx_rate,
                MAX(max_rx_rate) as max_rx_rate,
                AVG(avg_tx_rate) as avg_tx_rate,
                AVG(avg_rx_rate) as avg_rx_rate
            FROM daily_stats ds
            JOIN interfaces i ON ds.interface_id = i.id
            WHERE ds.date >= ?
            GROUP BY ds.interface_id
            """
            
            self.cursor.execute(query, (start_date,))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"{Colors.RED}Lỗi khi truy vấn tổng hợp dữ liệu: {e}{Colors.ENDC}")
            return []

    def get_traffic_by_hour(self, interface_id, date=None):
        """Lấy dữ liệu traffic theo giờ cho một ngày cụ thể."""
        try:
            if date is None:
                date = datetime.datetime.now().strftime('%Y-%m-%d')
                
            # Tạo timestamp bắt đầu và kết thúc của ngày
            start_timestamp = f"{date} 00:00:00"
            end_timestamp = f"{date} 23:59:59"
            
            query = """
            SELECT 
                strftime('%H', timestamp) as hour,
                AVG(tx_rate) as avg_tx_rate,
                AVG(rx_rate) as avg_rx_rate,
                MAX(tx_rate) as max_tx_rate,
                MAX(rx_rate) as max_rx_rate
            FROM traffic_data
            WHERE 
                interface_id = ? AND
                timestamp >= ? AND
                timestamp <= ?
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
            """
            
            self.cursor.execute(query, (interface_id, start_timestamp, end_timestamp))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"{Colors.RED}Lỗi khi truy vấn dữ liệu theo giờ: {e}{Colors.ENDC}")
            return []

    def print_database_info(self):
        """In thông tin tổng quan về cơ sở dữ liệu."""
        try:
            # Đếm số thiết bị
            self.cursor.execute("SELECT COUNT(*) as count FROM devices")
            device_count = self.cursor.fetchone()['count']
            
            # Đếm số interfaces
            self.cursor.execute("SELECT COUNT(*) as count FROM interfaces")
            interface_count = self.cursor.fetchone()['count']
            
            # Đếm số bản ghi traffic
            self.cursor.execute("SELECT COUNT(*) as count FROM traffic_data")
            traffic_count = self.cursor.fetchone()['count']
            
            # Lấy thời gian ghi log đầu tiên và cuối cùng
            self.cursor.execute("SELECT MIN(timestamp) as first_log FROM traffic_data")
            first_log = self.cursor.fetchone()['first_log']
            
            self.cursor.execute("SELECT MAX(timestamp) as last_log FROM traffic_data")
            last_log = self.cursor.fetchone()['last_log']
            
            # Tính kích thước file DB
            db_size = os.path.getsize(self.db_path) / (1024 * 1024)  # Chuyển sang MB
            
            print(f"\n{Colors.HEADER}{Colors.BOLD}=== THÔNG TIN CƠ SỞ DỮ LIỆU ==={Colors.ENDC}")
            print(f"File: {self.db_path} ({db_size:.2f} MB)")
            print(f"Số thiết bị: {device_count}")
            print(f"Số interfaces: {interface_count}")
            print(f"Số bản ghi traffic: {traffic_count}")
            
            if first_log and last_log:
                print(f"Thời gian bắt đầu: {first_log}")
                print(f"Thời gian gần nhất: {last_log}")
                
                # Tính thời gian giám sát
                try:
                    first_dt = datetime.datetime.strptime(first_log, '%Y-%m-%d %H:%M:%S')
                    last_dt = datetime.datetime.strptime(last_log, '%Y-%m-%d %H:%M:%S')
                    duration = last_dt - first_dt
                    days, seconds = duration.days, duration.seconds
                    hours = seconds // 3600
                    minutes = (seconds % 3600) // 60
                    seconds = seconds % 60
                    
                    duration_str = ""
                    if days > 0:
                        duration_str += f"{days} ngày "
                    if hours > 0:
                        duration_str += f"{hours} giờ "
                    if minutes > 0:
                        duration_str += f"{minutes} phút "
                    if seconds > 0 or duration_str == "":
                        duration_str += f"{seconds} giây"
                        
                    print(f"Thời gian giám sát: {duration_str}")
                except ValueError:
                    # Bỏ qua nếu không thể phân tích chuỗi thời gian
                    pass
            
        except sqlite3.Error as e:
            print(f"{Colors.RED}Lỗi khi truy vấn thông tin cơ sở dữ liệu: {e}{Colors.ENDC}")

    def print_devices(self):
        """In thông tin về các thiết bị được ghi log."""
        devices = self.get_device_info()
        
        if not devices:
            print(f"{Colors.WARNING}Không có thiết bị nào trong cơ sở dữ liệu.{Colors.ENDC}")
            return
            
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH THIẾT BỊ ==={Colors.ENDC}")
        
        # Chuẩn bị dữ liệu cho bảng
        table_data = []
        for device in devices:
            # Lấy số interfaces cho thiết bị này
            self.cursor.execute("SELECT COUNT(*) as count FROM interfaces WHERE device_id = ?", (device['id'],))
            interface_count = self.cursor.fetchone()['count']
            
            table_data.append([
                device['id'],
                device['hostname'],
                device['model'],
                device['ip_address'],
                device['ros_version'],
                interface_count
            ])
            
        headers = ["ID", "Tên", "Model", "Địa chỉ", "Phiên bản", "Số interfaces"]
        print(tabulate(table_data, headers=headers, tablefmt="pretty"))

    def print_interfaces(self, device_id=None):
        """In thông tin về các interfaces được ghi log."""
        if device_id:
            devices = [{'id': device_id}]
        else:
            devices = self.get_device_info()
            
        if not devices:
            print(f"{Colors.WARNING}Không có thiết bị nào trong cơ sở dữ liệu.{Colors.ENDC}")
            return
            
        for device in devices:
            device_id = device['id']
            
            # Lấy thông tin thiết bị
            if 'hostname' not in device:
                self.cursor.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
                device = self.cursor.fetchone()
                
            interfaces = self.get_interfaces(device_id)
            
            if not interfaces:
                print(f"\n{Colors.WARNING}Không có interface nào cho thiết bị {device['hostname']} (ID: {device_id}).{Colors.ENDC}")
                continue
                
            print(f"\n{Colors.HEADER}{Colors.BOLD}=== INTERFACES CỦA {device['hostname']} (ID: {device_id}) ==={Colors.ENDC}")
            
            # Chuẩn bị dữ liệu cho bảng
            table_data = []
            for interface in interfaces:
                # Đếm số bản ghi traffic cho interface này
                self.cursor.execute("SELECT COUNT(*) as count FROM traffic_data WHERE interface_id = ?", (interface['id'],))
                record_count = self.cursor.fetchone()['count']
                
                # Kiểm tra xem cột 'active' có tồn tại không
                active_status = "N/A"
                if 'active' in interface:
                    active_status = "Có" if interface['active'] else "Không"
                
                table_data.append([
                    interface['id'],
                    interface['name'],
                    interface['type'],
                    active_status,
                    record_count
                ])
                
            headers = ["ID", "Tên", "Loại", "Hoạt động", "Số bản ghi"]
            print(tabulate(table_data, headers=headers, tablefmt="pretty"))

    def print_traffic_summary(self, days=7):
        """In tổng hợp lưu lượng cho tất cả các interfaces."""
        summary = self.get_traffic_summary(days)
        
        if not summary:
            print(f"{Colors.WARNING}Không có dữ liệu tổng hợp nào cho {days} ngày qua.{Colors.ENDC}")
            return
            
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== TỔNG HỢP LƯU LƯỢNG ({days} NGÀY QUA) ==={Colors.ENDC}")
        
        # Chuẩn bị dữ liệu cho bảng
        table_data = []
        for row in summary:
            # Chuyển byte sang MB hoặc GB
            tx_total = row['total_tx_bytes']
            rx_total = row['total_rx_bytes']
            
            if tx_total > 1024 * 1024 * 1024:
                tx_str = f"{tx_total / (1024 * 1024 * 1024):.2f} GB"
            else:
                tx_str = f"{tx_total / (1024 * 1024):.2f} MB"
                
            if rx_total > 1024 * 1024 * 1024:
                rx_str = f"{rx_total / (1024 * 1024 * 1024):.2f} GB"
            else:
                rx_str = f"{rx_total / (1024 * 1024):.2f} MB"
                
            table_data.append([
                row['interface_name'],
                tx_str,
                rx_str,
                f"{row['max_tx_rate']:.2f} KB/s",
                f"{row['max_rx_rate']:.2f} KB/s",
                f"{row['avg_tx_rate']:.2f} KB/s",
                f"{row['avg_rx_rate']:.2f} KB/s"
            ])
            
        headers = ["Interface", "TX Tổng", "RX Tổng", "TX Cao nhất", "RX Cao nhất", "TX Trung bình", "RX Trung bình"]
        print(tabulate(table_data, headers=headers, tablefmt="pretty"))

    def print_daily_stats(self, interface_id=None, days=7):
        """In thống kê hàng ngày cho một hoặc tất cả các interfaces."""
        stats = self.get_daily_stats(interface_id, days)
        
        if not stats:
            if interface_id:
                print(f"{Colors.WARNING}Không có dữ liệu thống kê hàng ngày nào cho interface ID {interface_id}.{Colors.ENDC}")
            else:
                print(f"{Colors.WARNING}Không có dữ liệu thống kê hàng ngày nào.{Colors.ENDC}")
            return
            
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== THỐNG KÊ HÀNG NGÀY ({days} NGÀY QUA) ==={Colors.ENDC}")
        
        # Chuẩn bị dữ liệu cho bảng
        table_data = []
        for row in stats:
            # Chuyển byte sang MB hoặc GB
            tx_total = row['total_tx_bytes']
            rx_total = row['total_rx_bytes']
            
            if tx_total > 1024 * 1024 * 1024:
                tx_str = f"{tx_total / (1024 * 1024 * 1024):.2f} GB"
            else:
                tx_str = f"{tx_total / (1024 * 1024):.2f} MB"
                
            if rx_total > 1024 * 1024 * 1024:
                rx_str = f"{rx_total / (1024 * 1024 * 1024):.2f} GB"
            else:
                rx_str = f"{rx_total / (1024 * 1024):.2f} MB"
                
            table_data.append([
                row['interface_name'],
                row['date'],
                tx_str,
                rx_str,
                f"{row['max_tx_rate']:.2f} KB/s",
                f"{row['max_rx_rate']:.2f} KB/s",
                f"{row['avg_tx_rate']:.2f} KB/s",
                f"{row['avg_rx_rate']:.2f} KB/s"
            ])
            
        headers = ["Interface", "Ngày", "TX Tổng", "RX Tổng", "TX Cao nhất", "RX Cao nhất", "TX Trung bình", "RX Trung bình"]
        print(tabulate(table_data, headers=headers, tablefmt="pretty"))

    def plot_traffic_history(self, interface_id, hours=24, output_file=None):
        """Vẽ biểu đồ lịch sử traffic cho một interface."""
        # Tính thời gian bắt đầu dựa trên số giờ
        start_time = (datetime.datetime.now() - datetime.timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            # Truy vấn dữ liệu
            query = """
            SELECT timestamp, tx_rate, rx_rate
            FROM traffic_data
            WHERE interface_id = ? AND timestamp >= ?
            ORDER BY timestamp
            """
            
            self.cursor.execute(query, (interface_id, start_time))
            data = self.cursor.fetchall()
            
            if not data:
                print(f"{Colors.WARNING}Không có dữ liệu traffic nào cho interface ID {interface_id} trong {hours} giờ qua.{Colors.ENDC}")
                return
                
            # Lấy tên interface
            self.cursor.execute("SELECT name FROM interfaces WHERE id = ?", (interface_id,))
            interface_name = self.cursor.fetchone()['name']
            
            # Chuẩn bị dữ liệu cho biểu đồ
            timestamps = []
            tx_rates = []
            rx_rates = []
            
            for row in data:
                try:
                    timestamp = datetime.datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                    timestamps.append(timestamp)
                    tx_rates.append(row['tx_rate'])
                    rx_rates.append(row['rx_rate'])
                except ValueError:
                    continue
            
            # Tạo biểu đồ
            plt.figure(figsize=(10, 6))
            plt.plot(timestamps, tx_rates, label='TX (KB/s)', color='blue')
            plt.plot(timestamps, rx_rates, label='RX (KB/s)', color='green')
            
            plt.title(f'Lịch sử traffic cho {interface_name} ({hours} giờ qua)')
            plt.xlabel('Thời gian')
            plt.ylabel('Tốc độ (KB/s)')
            plt.grid(True)
            plt.legend()
            
            # Định dạng trục thời gian
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            if hours > 24:
                plt.gca().xaxis.set_major_locator(mdates.DayLocator())
                plt.gcf().autofmt_xdate()
            else:
                plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=2))
            
            if output_file:
                plt.savefig(output_file)
                print(f"{Colors.GREEN}Đã lưu biểu đồ vào {output_file}{Colors.ENDC}")
            else:
                plt.tight_layout()
                plt.show()
                
        except sqlite3.Error as e:
            print(f"{Colors.RED}Lỗi khi truy vấn dữ liệu cho biểu đồ: {e}{Colors.ENDC}")
            
    def plot_daily_stats(self, interface_id, days=7, output_file=None):
        """Vẽ biểu đồ thống kê hàng ngày cho một interface."""
        try:
            # Truy vấn dữ liệu
            query = """
            SELECT date, total_tx_bytes, total_rx_bytes, avg_tx_rate, avg_rx_rate
            FROM daily_stats
            WHERE interface_id = ?
            ORDER BY date
            LIMIT ?
            """
            
            self.cursor.execute(query, (interface_id, days))
            data = self.cursor.fetchall()
            
            if not data:
                print(f"{Colors.WARNING}Không có dữ liệu thống kê hàng ngày nào cho interface ID {interface_id}.{Colors.ENDC}")
                return
                
            # Lấy tên interface
            self.cursor.execute("SELECT name FROM interfaces WHERE id = ?", (interface_id,))
            interface_name = self.cursor.fetchone()['name']
            
            # Chuẩn bị dữ liệu cho biểu đồ
            dates = []
            tx_totals_mb = []
            rx_totals_mb = []
            avg_tx_rates = []
            avg_rx_rates = []
            
            for row in data:
                dates.append(row['date'])
                # Chuyển byte sang MB
                tx_totals_mb.append(row['total_tx_bytes'] / (1024 * 1024))
                rx_totals_mb.append(row['total_rx_bytes'] / (1024 * 1024))
                avg_tx_rates.append(row['avg_tx_rate'])
                avg_rx_rates.append(row['avg_rx_rate'])
            
            # Tạo hai biểu đồ: một cho tổng lượng dữ liệu, một cho tốc độ trung bình
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
            
            # Biểu đồ tổng lượng dữ liệu
            ax1.bar(dates, tx_totals_mb, label='TX (MB)', color='blue', alpha=0.7)
            ax1.bar(dates, rx_totals_mb, label='RX (MB)', color='green', alpha=0.7)
            
            ax1.set_title(f'Tổng lượng dữ liệu hàng ngày cho {interface_name}')
            ax1.set_xlabel('Ngày')
            ax1.set_ylabel('Dữ liệu (MB)')
            ax1.grid(True, axis='y')
            ax1.legend()
            
            # Định dạng trục thời gian cho biểu đồ 1
            if len(dates) > 10:
                for label in ax1.xaxis.get_ticklabels():
                    label.set_rotation(45)
            
            # Biểu đồ tốc độ trung bình
            ax2.plot(dates, avg_tx_rates, marker='o', label='TX Trung bình (KB/s)', color='blue')
            ax2.plot(dates, avg_rx_rates, marker='o', label='RX Trung bình (KB/s)', color='green')
            
            ax2.set_title(f'Tốc độ trung bình hàng ngày cho {interface_name}')
            ax2.set_xlabel('Ngày')
            ax2.set_ylabel('Tốc độ (KB/s)')
            ax2.grid(True)
            ax2.legend()
            
            # Định dạng trục thời gian cho biểu đồ 2
            if len(dates) > 10:
                for label in ax2.xaxis.get_ticklabels():
                    label.set_rotation(45)
            
            plt.tight_layout()
            
            if output_file:
                plt.savefig(output_file)
                print(f"{Colors.GREEN}Đã lưu biểu đồ vào {output_file}{Colors.ENDC}")
            else:
                plt.show()
                
        except sqlite3.Error as e:
            print(f"{Colors.RED}Lỗi khi truy vấn dữ liệu cho biểu đồ: {e}{Colors.ENDC}")
    
    def plot_hourly_stats(self, interface_id, date=None, output_file=None):
        """Vẽ biểu đồ thống kê theo giờ cho một ngày cụ thể."""
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
            
        data = self.get_traffic_by_hour(interface_id, date)
        
        if not data:
            print(f"{Colors.WARNING}Không có dữ liệu traffic theo giờ nào cho interface ID {interface_id} vào ngày {date}.{Colors.ENDC}")
            return
            
        # Lấy tên interface
        self.cursor.execute("SELECT name FROM interfaces WHERE id = ?", (interface_id,))
        interface_name = self.cursor.fetchone()['name']
        
        # Chuẩn bị dữ liệu cho biểu đồ
        hours = []
        avg_tx_rates = []
        avg_rx_rates = []
        max_tx_rates = []
        max_rx_rates = []
        
        for row in data:
            hours.append(int(row['hour']))
            avg_tx_rates.append(row['avg_tx_rate'])
            avg_rx_rates.append(row['avg_rx_rate'])
            max_tx_rates.append(row['max_tx_rate'])
            max_rx_rates.append(row['max_rx_rate'])
        
        # Tạo hai biểu đồ: một cho tốc độ trung bình, một cho tốc độ cao nhất
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
        
        # Biểu đồ tốc độ trung bình
        ax1.plot(hours, avg_tx_rates, marker='o', label='TX Trung bình (KB/s)', color='blue')
        ax1.plot(hours, avg_rx_rates, marker='o', label='RX Trung bình (KB/s)', color='green')
        
        ax1.set_title(f'Tốc độ trung bình theo giờ cho {interface_name} ({date})')
        ax1.set_xlabel('Giờ')
        ax1.set_ylabel('Tốc độ (KB/s)')
        ax1.set_xticks(range(0, 24))
        ax1.grid(True)
        ax1.legend()
        
        # Biểu đồ tốc độ cao nhất
        ax2.plot(hours, max_tx_rates, marker='o', label='TX Cao nhất (KB/s)', color='blue')
        ax2.plot(hours, max_rx_rates, marker='o', label='RX Cao nhất (KB/s)', color='green')
        
        ax2.set_title(f'Tốc độ cao nhất theo giờ cho {interface_name} ({date})')
        ax2.set_xlabel('Giờ')
        ax2.set_ylabel('Tốc độ (KB/s)')
        ax2.set_xticks(range(0, 24))
        ax2.grid(True)
        ax2.legend()
        
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file)
            print(f"{Colors.GREEN}Đã lưu biểu đồ vào {output_file}{Colors.ENDC}")
        else:
            plt.show()
    
    def export_data_to_json(self, output_file, days=7):
        """Xuất dữ liệu sang định dạng JSON."""
        try:
            # Lấy thông tin thiết bị
            devices = self.get_device_info()
            
            if not devices:
                print(f"{Colors.WARNING}Không có thiết bị nào trong cơ sở dữ liệu.{Colors.ENDC}")
                return
            
            # Tính thời gian bắt đầu dựa trên số ngày
            start_time = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Chuẩn bị cấu trúc dữ liệu
            export_data = {
                "devices": [],
                "generated_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "period_days": days
            }
            
            for device in devices:
                device_data = {
                    "id": device['id'],
                    "name": device['hostname'],
                    "model": device['model'],
                    "address": device['ip_address'],
                    "version": device['ros_version'],
                    "interfaces": []
                }
                
                # Lấy interfaces của thiết bị
                interfaces = self.get_interfaces(device['id'])
                
                for interface in interfaces:
                    # Kiểm tra xem trường active có tồn tại không
                    is_active = False
                    if 'active' in interface:
                        is_active = bool(interface['active'])
                    
                    interface_data = {
                        "id": interface['id'],
                        "name": interface['name'],
                        "type": interface['type'],
                        "active": is_active,
                        "daily_stats": []
                    }
                    
                    # Lấy thống kê hàng ngày
                    query = """
                    SELECT * FROM daily_stats 
                    WHERE interface_id = ? AND date >= ?
                    ORDER BY date
                    """
                    
                    self.cursor.execute(query, (interface['id'], start_time))
                    daily_stats = self.cursor.fetchall()
                    
                    for stat in daily_stats:
                        stat_data = {
                            "date": stat['date'],
                            "total_tx_bytes": stat['total_tx_bytes'],
                            "total_rx_bytes": stat['total_rx_bytes'],
                            "max_tx_rate": stat['max_tx_rate'],
                            "max_rx_rate": stat['max_rx_rate'],
                            "avg_tx_rate": stat['avg_tx_rate'],
                            "avg_rx_rate": stat['avg_rx_rate']
                        }
                        interface_data["daily_stats"].append(stat_data)
                    
                    device_data["interfaces"].append(interface_data)
                
                export_data["devices"].append(device_data)
            
            # Ghi dữ liệu ra file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            print(f"{Colors.GREEN}Đã xuất dữ liệu sang {output_file}{Colors.ENDC}")
            
        except (sqlite3.Error, IOError) as e:
            print(f"{Colors.RED}Lỗi khi xuất dữ liệu: {e}{Colors.ENDC}")
    
    def close(self):
        """Đóng kết nối cơ sở dữ liệu."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()


def main():
    """Hàm chính để phân tích cơ sở dữ liệu."""
    parser = argparse.ArgumentParser(description='Công cụ phân tích cơ sở dữ liệu MikroTik')
    
    parser.add_argument('--db', default='mikrotik_traffic.db', help='Đường dẫn đến file cơ sở dữ liệu (mặc định: mikrotik_traffic.db)')
    
    # Các lệnh chính
    subparsers = parser.add_subparsers(dest='command', help='Lệnh')
    
    # Lệnh hiển thị thông tin
    info_parser = subparsers.add_parser('info', help='Hiển thị thông tin cơ sở dữ liệu')
    
    # Lệnh liệt kê thiết bị
    devices_parser = subparsers.add_parser('devices', help='Liệt kê thiết bị')
    
    # Lệnh liệt kê interfaces
    interfaces_parser = subparsers.add_parser('interfaces', help='Liệt kê interfaces')
    interfaces_parser.add_argument('--device', type=int, help='ID của thiết bị cần liệt kê interfaces')
    
    # Lệnh hiển thị tổng quan traffic
    summary_parser = subparsers.add_parser('summary', help='Hiển thị tổng quan traffic')
    summary_parser.add_argument('--days', type=int, default=7, help='Số ngày cần phân tích (mặc định: 7)')
    
    # Lệnh hiển thị thống kê hàng ngày
    daily_parser = subparsers.add_parser('daily', help='Hiển thị thống kê hàng ngày')
    daily_parser.add_argument('--interface', type=int, help='ID của interface cần hiển thị thống kê')
    daily_parser.add_argument('--days', type=int, default=7, help='Số ngày cần hiển thị (mặc định: 7)')
    
    # Lệnh vẽ biểu đồ
    plot_parser = subparsers.add_parser('plot', help='Vẽ biểu đồ')
    plot_parser.add_argument('--type', choices=['history', 'daily', 'hourly'], required=True, help='Loại biểu đồ')
    plot_parser.add_argument('--interface', type=int, required=True, help='ID của interface cần vẽ biểu đồ')
    plot_parser.add_argument('--hours', type=int, default=24, help='Số giờ để hiển thị lịch sử (chỉ cho loại history, mặc định: 24)')
    plot_parser.add_argument('--days', type=int, default=7, help='Số ngày để hiển thị thống kê hàng ngày (chỉ cho loại daily, mặc định: 7)')
    plot_parser.add_argument('--date', help='Ngày để hiển thị thống kê theo giờ, định dạng YYYY-MM-DD (chỉ cho loại hourly)')
    plot_parser.add_argument('--output', help='Tên file để lưu biểu đồ (ví dụ: plot.png)')
    
    # Lệnh xuất dữ liệu
    export_parser = subparsers.add_parser('export', help='Xuất dữ liệu')
    export_parser.add_argument('--format', choices=['json'], default='json', help='Định dạng xuất (mặc định: json)')
    export_parser.add_argument('--output', required=True, help='Tên file để lưu dữ liệu xuất')
    export_parser.add_argument('--days', type=int, default=7, help='Số ngày dữ liệu cần xuất (mặc định: 7)')
    
    args = parser.parse_args()
    
    # Nếu không có lệnh nào được cung cấp, hiển thị trợ giúp
    if not args.command:
        parser.print_help()
        return
    
    analyzer = MikroTikDBAnalyzer(args.db)
    
    try:
        if args.command == 'info':
            analyzer.print_database_info()
            
        elif args.command == 'devices':
            analyzer.print_devices()
            
        elif args.command == 'interfaces':
            analyzer.print_interfaces(args.device)
            
        elif args.command == 'summary':
            analyzer.print_traffic_summary(args.days)
            
        elif args.command == 'daily':
            analyzer.print_daily_stats(args.interface, args.days)
            
        elif args.command == 'plot':
            if args.type == 'history':
                analyzer.plot_traffic_history(args.interface, args.hours, args.output)
            elif args.type == 'daily':
                analyzer.plot_daily_stats(args.interface, args.days, args.output)
            elif args.type == 'hourly':
                analyzer.plot_hourly_stats(args.interface, args.date, args.output)
                
        elif args.command == 'export':
            if args.format == 'json':
                analyzer.export_data_to_json(args.output, args.days)
    
    finally:
        analyzer.close()


if __name__ == "__main__":
    main()