"""
Module chứa các hàm tiện ích cho MikroTik
"""

import os
import time
import logging
import datetime
import sqlite3
from typing import Optional, Dict, List, Any, Tuple

# Khởi tạo logger
logger = logging.getLogger(__name__)

def get_mikrotik_connection(max_retries=3, retry_delay=2):
    """Lấy kết nối đến thiết bị MikroTik với cơ chế retry
    
    Args:
        max_retries (int): Số lần thử lại tối đa
        retry_delay (int): Thời gian chờ giữa các lần thử (giây)
        
    Returns:
        RouterOS API object hoặc None nếu không thể kết nối
    """
    try:
        from librouteros import connect
        from librouteros.query import Key
        from librouteros.exceptions import ConnectionError, LoginError
        
        # Lấy thông tin kết nối từ biến môi trường
        host = os.getenv('MIKROTIK_HOST', '192.168.88.1')
        username = os.getenv('MIKROTIK_USERNAME', 'admin')
        password = os.getenv('MIKROTIK_PASSWORD', '')
        port = int(os.getenv('MIKROTIK_API_PORT', 8728))
        timeout = int(os.getenv('MIKROTIK_TIMEOUT', 10))
        
        # Thử kết nối với số lần thử lại
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                # Kết nối đến thiết bị với timeout
                api = connect(
                    username=username,
                    password=password,
                    host=host,
                    port=port,
                    timeout=timeout
                )
                
                # Thực hiện một câu lệnh đơn giản để kiểm tra kết nối
                api.path('/system/identity').get()
                
                logger.info(f"Đã kết nối thành công đến MikroTik {host}:{port}")
                return api
                
            except (ConnectionError, LoginError) as e:
                retry_count += 1
                last_error = e
                logger.warning(f"Lần thử {retry_count}/{max_retries} kết nối đến MikroTik thất bại: {str(e)}")
                
                if retry_count < max_retries:
                    time.sleep(retry_delay)
                    # Tăng thời gian chờ cho mỗi lần thử lại
                    retry_delay *= 1.5
        
        # Sau khi thử hết số lần, vẫn không thành công
        logger.error(f"Không thể kết nối đến MikroTik sau {max_retries} lần thử: {str(last_error)}")
        return None
        
    except Exception as e:
        logger.error(f"Lỗi khi kết nối đến MikroTik: {str(e)}")
        return None

def get_mac_address(interface: str) -> Optional[str]:
    """Lấy địa chỉ MAC của interface"""
    try:
        api = get_mikrotik_connection()
        if not api:
            return None
        
        # Lấy thông tin interface
        interface_data = api.path('interface').select('mac-address').where(Key('name') == interface).get()
        if interface_data:
            return interface_data[0].get('mac-address')
        
        return None
    except Exception as e:
        logger.error(f"Lỗi khi lấy MAC address của interface {interface}: {str(e)}")
        return None

def is_ip_active(ip_address: str) -> bool:
    """Kiểm tra xem IP có đang hoạt động không"""
    try:
        # Ping để kiểm tra
        response = os.system(f"ping -c 1 -W 1 {ip_address} > /dev/null 2>&1")
        return response == 0
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái IP {ip_address}: {str(e)}")
        return False

def get_interface_traffic(interface: str, direction: str = 'both') -> Dict[str, int]:
    """Lấy thông tin traffic của interface"""
    try:
        api = get_mikrotik_connection()
        if not api:
            return {'in': 0, 'out': 0} if direction == 'both' else 0
        
        # Lấy thống kê interface
        interface_data = api.path('interface').select('rx-byte', 'tx-byte').where(Key('name') == interface).get()
        if not interface_data:
            return {'in': 0, 'out': 0} if direction == 'both' else 0
        
        data = interface_data[0]
        if direction == 'in':
            return data.get('rx-byte', 0)
        elif direction == 'out':
            return data.get('tx-byte', 0)
        else:
            return {
                'in': data.get('rx-byte', 0),
                'out': data.get('tx-byte', 0)
            }
    except Exception as e:
        logger.error(f"Lỗi khi lấy traffic của interface {interface}: {str(e)}")
        return {'in': 0, 'out': 0} if direction == 'both' else 0

def get_last_seen(ip_address: str) -> Optional[str]:
    """Lấy thời điểm cuối cùng IP được nhìn thấy"""
    try:
        # Lấy từ bảng ARP
        api = get_mikrotik_connection()
        if not api:
            return None
        
        arp_data = api.path('ip', 'arp').select('last-seen').where(Key('address') == ip_address).get()
        if arp_data:
            return arp_data[0].get('last-seen')
        
        return None
    except Exception as e:
        logger.error(f"Lỗi khi lấy last seen của IP {ip_address}: {str(e)}")
        return None

def is_ip_monitored(ip_address: str) -> bool:
    """Kiểm tra xem IP có đang được giám sát không"""
    try:
        conn = sqlite3.connect('data/ip_monitoring.db')
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
        conn = sqlite3.connect('data/ip_monitoring.db')
        cursor = conn.cursor()
        
        # Cập nhật hoặc thêm mới
        cursor.execute('''
            INSERT OR REPLACE INTO ip_monitoring (ip_address, monitoring)
            VALUES (?, 1)
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
        conn = sqlite3.connect('data/ip_monitoring.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE ip_monitoring
            SET monitoring = 0
            WHERE ip_address = ?
        ''', (ip_address,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Đã tắt monitoring cho IP {ip_address}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi tắt monitoring cho IP {ip_address}: {str(e)}")
        return False

def get_traffic_chart_data() -> Dict[str, List[Dict[str, Any]]]:
    """Lấy dữ liệu cho biểu đồ traffic"""
    try:
        conn = sqlite3.connect('data/ip_monitoring.db')
        cursor = conn.cursor()
        
        # Lấy dữ liệu traffic trong 24 giờ qua
        cursor.execute('''
            SELECT ip_address, bytes_in, bytes_out, timestamp
            FROM ip_traffic
            WHERE timestamp >= datetime('now', '-24 hours')
            ORDER BY timestamp ASC
        ''')
        
        data = cursor.fetchall()
        conn.close()
        
        # Xử lý dữ liệu cho biểu đồ
        result = {
            'labels': [],
            'datasets': []
        }
        
        if data:
            # Tạo nhãn thời gian
            result['labels'] = [row[3] for row in data]
            
            # Tạo datasets cho bytes in/out
            result['datasets'] = [
                {
                    'label': 'Traffic In',
                    'data': [row[1] for row in data],
                    'borderColor': '#2196f3',
                    'backgroundColor': 'rgba(33, 150, 243, 0.1)',
                    'fill': True
                },
                {
                    'label': 'Traffic Out',
                    'data': [row[2] for row in data],
                    'borderColor': '#4caf50',
                    'backgroundColor': 'rgba(76, 175, 80, 0.1)',
                    'fill': True
                }
            ]
        
        return result
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu biểu đồ traffic: {str(e)}")
        return {'labels': [], 'datasets': []}

def get_ip_distribution_data() -> Dict[str, List[Any]]:
    """Lấy dữ liệu phân bố IP"""
    try:
        conn = sqlite3.connect('data/ip_monitoring.db')
        cursor = conn.cursor()
        
        # Lấy thống kê trạng thái
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM ip_monitoring
            WHERE monitoring = 1
            GROUP BY status
        ''')
        
        data = cursor.fetchall()
        conn.close()
        
        # Xử lý dữ liệu cho biểu đồ
        labels = []
        values = []
        colors = []
        
        status_colors = {
            'active': '#4caf50',
            'inactive': '#f44336',
            'unknown': '#9e9e9e'
        }
        
        for status, count in data:
            labels.append(status.capitalize())
            values.append(count)
            colors.append(status_colors.get(status, '#9e9e9e'))
        
        return {
            'labels': labels,
            'datasets': [{
                'data': values,
                'backgroundColor': colors
            }]
        }
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu phân bố IP: {str(e)}")
        return {'labels': [], 'datasets': [{'data': [], 'backgroundColor': []}]}