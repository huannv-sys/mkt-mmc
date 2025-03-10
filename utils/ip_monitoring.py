"""
Module giám sát và quản lý IP
"""

import os
import time
import logging
import datetime
import sqlite3
from typing import Dict, List, Optional, Tuple

# Khởi tạo logger
logger = logging.getLogger(__name__)

# Kết nối đến cơ sở dữ liệu
DB_PATH = 'data/ip_monitoring.db'
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_database():
    """Khởi tạo cơ sở dữ liệu"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Bảng ip_monitoring
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ip_monitoring (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                interface TEXT NOT NULL,
                mac_address TEXT,
                status TEXT DEFAULT 'inactive',
                monitoring BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Bảng ip_traffic
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ip_traffic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                bytes_in INTEGER DEFAULT 0,
                bytes_out INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Bảng ip_history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ip_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                event TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Đã khởi tạo cơ sở dữ liệu thành công")
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo cơ sở dữ liệu: {str(e)}")

def add_ip_to_monitoring(ip_address: str, interface: str, mac_address: Optional[str] = None):
    """Thêm IP vào danh sách giám sát"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ip_monitoring (ip_address, interface, mac_address, monitoring)
            VALUES (?, ?, ?, 1)
        ''', (ip_address, interface, mac_address))
        
        # Ghi lịch sử
        cursor.execute('''
            INSERT INTO ip_history (ip_address, event, details)
            VALUES (?, 'add', 'Thêm IP vào giám sát')
        ''', (ip_address,))
        
        conn.commit()
        conn.close()
        logger.info(f"Đã thêm IP {ip_address} vào giám sát")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi thêm IP {ip_address} vào giám sát: {str(e)}")
        return False

def remove_ip_from_monitoring(ip_address: str):
    """Xóa IP khỏi danh sách giám sát"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE ip_monitoring
            SET monitoring = 0
            WHERE ip_address = ?
        ''', (ip_address,))
        
        # Ghi lịch sử
        cursor.execute('''
            INSERT INTO ip_history (ip_address, event, details)
            VALUES (?, 'remove', 'Xóa IP khỏi giám sát')
        ''', (ip_address,))
        
        conn.commit()
        conn.close()
        logger.info(f"Đã xóa IP {ip_address} khỏi giám sát")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi xóa IP {ip_address} khỏi giám sát: {str(e)}")
        return False

def is_ip_monitored(ip_address: str) -> bool:
    """Kiểm tra xem IP có đang được giám sát không"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT monitoring
            FROM ip_monitoring
            WHERE ip_address = ?
        ''', (ip_address,))
        
        row = cursor.fetchone()
        conn.close()
        
        return bool(row and row[0])
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra monitoring của IP {ip_address}: {str(e)}")
        return False

def enable_ip_monitoring(ip_address: str) -> bool:
    """Bật giám sát cho một IP"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Kiểm tra xem IP đã tồn tại trong bảng chưa
        cursor.execute('SELECT id FROM ip_monitoring WHERE ip_address = ?', (ip_address,))
        row = cursor.fetchone()
        
        if row:
            # Cập nhật trạng thái monitoring
            cursor.execute('''
                UPDATE ip_monitoring
                SET monitoring = 1
                WHERE ip_address = ?
            ''', (ip_address,))
        else:
            # Thêm mới vào bảng với interface mặc định
            cursor.execute('''
                INSERT INTO ip_monitoring (ip_address, interface, monitoring)
                VALUES (?, 'unknown', 1)
            ''', (ip_address,))
        
        # Ghi lịch sử
        cursor.execute('''
            INSERT INTO ip_history (ip_address, event, details)
            VALUES (?, 'enable_monitoring', 'Bật giám sát')
        ''', (ip_address,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Đã bật monitoring cho IP {ip_address}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi bật monitoring cho IP {ip_address}: {str(e)}")
        return False

def disable_ip_monitoring(ip_address: str) -> bool:
    """Tắt giám sát cho một IP"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE ip_monitoring
            SET monitoring = 0
            WHERE ip_address = ?
        ''', (ip_address,))
        
        # Ghi lịch sử
        cursor.execute('''
            INSERT INTO ip_history (ip_address, event, details)
            VALUES (?, 'disable_monitoring', 'Tắt giám sát')
        ''', (ip_address,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Đã tắt monitoring cho IP {ip_address}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi tắt monitoring cho IP {ip_address}: {str(e)}")
        return False

def update_ip_traffic(ip_address: str, bytes_in: int, bytes_out: int):
    """Cập nhật thông tin traffic của IP"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ip_traffic (ip_address, bytes_in, bytes_out)
            VALUES (?, ?, ?)
        ''', (ip_address, bytes_in, bytes_out))
        
        conn.commit()
        conn.close()
        logger.debug(f"Đã cập nhật traffic cho IP {ip_address}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật traffic cho IP {ip_address}: {str(e)}")
        return False

def get_ip_traffic_history(ip_address: str, hours: int = 24) -> List[Dict]:
    """Lấy lịch sử traffic của IP"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT bytes_in, bytes_out, timestamp
            FROM ip_traffic
            WHERE ip_address = ? AND timestamp >= datetime('now', '-' || ? || ' hours')
            ORDER BY timestamp ASC
        ''', (ip_address, hours))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'bytes_in': row[0],
                'bytes_out': row[1],
                'timestamp': row[2]
            })
        
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Lỗi khi lấy lịch sử traffic cho IP {ip_address}: {str(e)}")
        return []

def get_ip_history(ip_address: str) -> List[Dict]:
    """Lấy lịch sử hoạt động của IP"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT event, details, timestamp
            FROM ip_history
            WHERE ip_address = ?
            ORDER BY timestamp DESC
            LIMIT 100
        ''', (ip_address,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'event': row[0],
                'details': row[1],
                'timestamp': row[2]
            })
        
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Lỗi khi lấy lịch sử cho IP {ip_address}: {str(e)}")
        return []

def check_ip_status(ip_address: str) -> Tuple[bool, Optional[str]]:
    """Kiểm tra trạng thái của IP"""
    try:
        # Ping đến IP
        response = os.system(f"ping -c 1 -W 1 {ip_address} > /dev/null 2>&1")
        status = response == 0
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Lấy trạng thái cũ
        cursor.execute('''
            SELECT status
            FROM ip_monitoring
            WHERE ip_address = ?
        ''', (ip_address,))
        row = cursor.fetchone()
        old_status = row[0] if row else None
        
        # Cập nhật trạng thái mới
        new_status = 'active' if status else 'inactive'
        if old_status != new_status:
            cursor.execute('''
                UPDATE ip_monitoring
                SET status = ?
                WHERE ip_address = ?
            ''', (new_status, ip_address))
            
            # Ghi lịch sử
            cursor.execute('''
                INSERT INTO ip_history (ip_address, event, details)
                VALUES (?, 'status_change', ?)
            ''', (ip_address, f'Trạng thái thay đổi từ {old_status} sang {new_status}'))
            
            conn.commit()
        
        conn.close()
        return status, new_status
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái IP {ip_address}: {str(e)}")
        return False, None

def get_monitoring_stats() -> Dict:
    """Lấy thống kê về giám sát IP"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Tổng số IP đang giám sát
        cursor.execute('SELECT COUNT(*) FROM ip_monitoring WHERE monitoring = 1')
        total_monitored = cursor.fetchone()[0]
        
        # Số IP đang hoạt động
        cursor.execute('SELECT COUNT(*) FROM ip_monitoring WHERE monitoring = 1 AND status = "active"')
        active_ips = cursor.fetchone()[0]
        
        # Số IP không hoạt động
        cursor.execute('SELECT COUNT(*) FROM ip_monitoring WHERE monitoring = 1 AND status = "inactive"')
        inactive_ips = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_monitored': total_monitored,
            'active_ips': active_ips,
            'inactive_ips': inactive_ips
        }
    except Exception as e:
        logger.error(f"Lỗi khi lấy thống kê giám sát IP: {str(e)}")
        return {
            'total_monitored': 0,
            'active_ips': 0,
            'inactive_ips': 0
        }

def monitor_ip_status():
    """Hàm chạy nền để giám sát trạng thái IP"""
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Lấy danh sách IP cần giám sát
            cursor.execute('SELECT ip_address FROM ip_monitoring WHERE monitoring = 1')
            ip_addresses = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            # Kiểm tra từng IP
            for ip in ip_addresses:
                check_ip_status(ip)
            
            # Nghỉ 60 giây trước khi kiểm tra lại
            time.sleep(60)
        except Exception as e:
            logger.error(f"Lỗi trong quá trình giám sát IP: {str(e)}")
            time.sleep(60)  # Nghỉ 60 giây trước khi thử lại

# Khởi tạo cơ sở dữ liệu khi import module
init_database()