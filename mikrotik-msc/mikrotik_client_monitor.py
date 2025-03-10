#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Giám sát và quản lý client trên thiết bị MikroTik
Script này giúp theo dõi và quản lý các client kết nối đến thiết bị MikroTik
"""

import os
import sys
import time
import json
import logging
import argparse
import datetime
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
import routeros_api

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('mikrotik_client_monitor')

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


class MikroTikClientMonitor:
    """Lớp giám sát và quản lý client trên thiết bị MikroTik."""

    def __init__(self, host, username, password):
        """Khởi tạo với thông tin kết nối."""
        self.host = host
        self.username = username
        self.password = password
        self.connection = None
        self.api = None

    def connect(self):
        """Kết nối đến thiết bị MikroTik và trả về API object."""
        logger.info(f"Đang kết nối đến {self.host}...")
        try:
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

    def get_wireless_clients(self):
        """Lấy danh sách các client kết nối không dây với thông tin băng tần."""
        if not self.api:
            return []
            
        try:
            # Kiểm tra xem có package wireless không
            packages = self.api.get_resource('/system/package').get()
            if not any(pkg.get('name') == 'wireless' for pkg in packages):
                logger.warning("Package wireless không được cài đặt trên thiết bị")
                return []
            
            clients_with_frequency = []
            
            # Thử lấy client từ wireless registration table
            try:
                # Lấy thông tin về wireless interfaces
                wireless_interfaces = self.api.get_resource('/interface/wireless').get()
                wireless_info = {}
                
                for iface in wireless_interfaces:
                    wireless_info[iface.get('name')] = {
                        'frequency': iface.get('frequency'),
                        'band': iface.get('band', 'unknown'),
                        'channel-width': iface.get('channel-width', 'unknown'),
                        'ssid': iface.get('ssid', 'unknown')
                    }
                
                # Lấy danh sách client
                registration = self.api.get_resource('/interface/wireless/registration-table').get()
                
                # Bổ sung thông tin băng tần và channel cho mỗi client
                for client in registration:
                    interface_name = client.get('interface', '')
                    if interface_name in wireless_info:
                        # Đây là thông tin của interface mà client kết nối
                        freq_info = wireless_info[interface_name]
                        
                        # Xác định băng tần (2.4GHz, 5GHz, 6GHz)
                        frequency = freq_info.get('frequency')
                        if frequency:
                            freq_mhz = int(frequency.strip('MHz'))
                            if freq_mhz < 3000:
                                band = "2.4GHz"
                            elif freq_mhz < 6000:
                                band = "5GHz"
                            else:
                                band = "6GHz"
                        else:
                            band = freq_info.get('band', 'unknown')
                        
                        # Bổ sung thông tin vào client
                        client['frequency'] = frequency
                        client['band'] = band
                        client['channel-width'] = freq_info.get('channel-width')
                        client['ssid'] = freq_info.get('ssid')
                        client['connection-type'] = 'regular wireless'
                        
                    clients_with_frequency.append(client)
                
                return clients_with_frequency
            except Exception as e:
                logger.warning(f"Không thể lấy client từ wireless registration table: {e}")
                
                # Kiểm tra xem có CAPsMAN không
                try:
                    # Lấy thông tin về CAPsMAN configurations
                    capsman_configs = self.api.get_resource('/caps-man/configuration').get()
                    configs_info = {}
                    
                    for config in capsman_configs:
                        configs_info[config.get('name')] = {
                            'ssid': config.get('ssid', 'unknown'),
                            'channel-width': config.get('channel-width', '20MHz')
                        }
                    
                    # Lấy thông tin về CAPsMAN channels
                    capsman_channels = self.api.get_resource('/caps-man/channel').get()
                    channels_info = {}
                    
                    for channel in capsman_channels:
                        channels_info[channel.get('name')] = {
                            'frequency': channel.get('frequency'),
                            'band': channel.get('band', 'unknown')
                        }
                    
                    # Lấy danh sách client
                    capsman_clients = self.api.get_resource('/caps-man/registration-table').get()
                    
                    # Bổ sung thông tin băng tần và channel cho mỗi client
                    for client in capsman_clients:
                        config_name = client.get('configuration', '')
                        channel_name = client.get('channel', '')
                        
                        config_info = configs_info.get(config_name, {})
                        channel_info = channels_info.get(channel_name, {})
                        
                        # Xác định băng tần (2.4GHz, 5GHz, 6GHz)
                        frequency = channel_info.get('frequency')
                        
                        if frequency:
                            # Frequency có thể có định dạng như "2412,2417,2422,..."
                            # Lấy giá trị đầu tiên
                            if ',' in frequency:
                                first_freq = frequency.split(',')[0]
                                freq_mhz = int(first_freq)
                            else:
                                freq_mhz = int(frequency.strip('MHz'))
                                
                            if freq_mhz < 3000:
                                band = "2.4GHz"
                            elif freq_mhz < 6000:
                                band = "5GHz"
                            else:
                                band = "6GHz"
                        else:
                            band = channel_info.get('band', 'unknown')
                        
                        # Bổ sung thông tin vào client
                        client['frequency'] = frequency
                        client['band'] = band
                        client['channel-width'] = config_info.get('channel-width')
                        client['ssid'] = config_info.get('ssid')
                        client['connection-type'] = 'CAPsMAN'
                        
                        clients_with_frequency.append(client)
                    
                    return clients_with_frequency
                except Exception as e:
                    logger.warning(f"Không thể lấy client từ CAPsMAN: {e}")
                    return []
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách wireless clients: {e}")
            return []

    def get_dhcp_leases(self):
        """Lấy danh sách các DHCP leases."""
        if not self.api:
            return []
            
        try:
            leases = self.api.get_resource('/ip/dhcp-server/lease').get()
            return leases
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách DHCP leases: {e}")
            return []

    def get_active_connections(self):
        """Lấy danh sách các kết nối đang hoạt động."""
        if not self.api:
            return []
            
        try:
            connections = self.api.get_resource('/ip/firewall/connection').get()
            return connections
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách active connections: {e}")
            return []

    def get_hotspot_users(self):
        """Lấy danh sách người dùng Hotspot."""
        if not self.api:
            return []
            
        try:
            # Thử lấy active users
            try:
                active_users = self.api.get_resource('/ip/hotspot/active').get()
                for user in active_users:
                    user['status'] = 'active'
                return active_users
            except:
                logger.warning("Không có hotspot đang hoạt động")
                return []
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách hotspot users: {e}")
            return []

    def get_arp_table(self):
        """Lấy bảng ARP."""
        if not self.api:
            return []
            
        try:
            arp_entries = self.api.get_resource('/ip/arp').get()
            return arp_entries
        except Exception as e:
            logger.error(f"Lỗi khi lấy bảng ARP: {e}")
            return []

    def get_client_traffic(self, ip_address=None, mac_address=None):
        """Lấy thông tin traffic của một client cụ thể."""
        if not self.api:
            return None
            
        try:
            # Lấy danh sách tất cả các kết nối đang hoạt động
            connections = self.get_active_connections()
            client_connections = []
            
            # Lọc theo địa chỉ IP hoặc MAC
            if ip_address:
                client_connections = [conn for conn in connections 
                                    if conn.get('src-address') == ip_address or 
                                       conn.get('dst-address') == ip_address]
            elif mac_address:
                # Tìm IP của MAC trong bảng ARP
                arp_entries = self.get_arp_table()
                ip_for_mac = None
                for entry in arp_entries:
                    if entry.get('mac-address') == mac_address:
                        ip_for_mac = entry.get('address')
                        break
                
                if ip_for_mac:
                    client_connections = [conn for conn in connections 
                                        if conn.get('src-address') == ip_for_mac or 
                                           conn.get('dst-address') == ip_for_mac]
            
            # Tính toán thống kê
            if client_connections:
                total_tx_bytes = sum(int(conn.get('orig-bytes', 0)) for conn in client_connections)
                total_rx_bytes = sum(int(conn.get('repl-bytes', 0)) for conn in client_connections)
                
                return {
                    'connections': len(client_connections),
                    'tx_bytes': total_tx_bytes,
                    'rx_bytes': total_rx_bytes,
                    'total_bytes': total_tx_bytes + total_rx_bytes
                }
            else:
                return {
                    'connections': 0,
                    'tx_bytes': 0,
                    'rx_bytes': 0,
                    'total_bytes': 0
                }
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin traffic của client: {e}")
            return None

    def block_client(self, ip_address=None, mac_address=None, comment=None):
        """Block một client bằng cách thêm vào address list."""
        if not self.api:
            return False
            
        try:
            # Nếu chỉ có MAC address, tìm IP tương ứng
            if mac_address and not ip_address:
                arp_entries = self.get_arp_table()
                for entry in arp_entries:
                    if entry.get('mac-address') == mac_address:
                        ip_address = entry.get('address')
                        break
            
            if not ip_address:
                logger.error("Không thể block client: Thiếu địa chỉ IP")
                return False
                
            # Thêm vào address list
            address_list_resource = self.api.get_resource('/ip/firewall/address-list')
            
            # Params cơ bản
            params = {
                "address": ip_address,
                "list": "blocked_clients",
                "comment": comment or f"Blocked client: {mac_address or ip_address}"
            }
            
            # Thêm vào address list
            address_list_resource.add(**params)
            logger.info(f"Đã block client {ip_address}")
            
            # Tạo rule drop nếu chưa có
            filter_resource = self.api.get_resource('/ip/firewall/filter')
            
            # Kiểm tra xem rule đã tồn tại chưa
            rules = filter_resource.get()
            rule_exists = False
            
            for rule in rules:
                if (rule.get('chain') == 'forward' and 
                    rule.get('action') == 'drop' and 
                    rule.get('src-address-list') == 'blocked_clients'):
                    rule_exists = True
                    break
            
            # Nếu rule chưa tồn tại, thêm mới
            if not rule_exists:
                filter_resource.add(
                    chain="forward",
                    action="drop",
                    src_address_list="blocked_clients",
                    comment="Drop blocked clients"
                )
                logger.info("Đã tạo rule drop cho blocked_clients")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi block client: {e}")
            return False

    def unblock_client(self, ip_address=None, mac_address=None):
        """Unblock một client bằng cách xóa khỏi address list."""
        if not self.api:
            return False
            
        try:
            # Nếu chỉ có MAC address, tìm IP tương ứng
            if mac_address and not ip_address:
                arp_entries = self.get_arp_table()
                for entry in arp_entries:
                    if entry.get('mac-address') == mac_address:
                        ip_address = entry.get('address')
                        break
            
            if not ip_address:
                logger.error("Không thể unblock client: Thiếu địa chỉ IP")
                return False
                
            # Xóa khỏi address list
            address_list_resource = self.api.get_resource('/ip/firewall/address-list')
            
            # Tìm entry phù hợp
            entries = address_list_resource.get(address=ip_address, list="blocked_clients")
            
            if not entries:
                logger.warning(f"Không tìm thấy client {ip_address} trong blocked_clients")
                return False
                
            # Xóa các entries tìm được
            for entry in entries:
                address_list_resource.remove(id=entry.get('.id'))
                logger.info(f"Đã unblock client {ip_address}")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi unblock client: {e}")
            return False

    def get_all_clients(self):
        """Lấy danh sách tất cả các client đang kết nối."""
        # Danh sách lưu kết quả
        clients = []
        
        # Lấy dữ liệu từ các nguồn khác nhau
        wireless_clients = self.get_wireless_clients()
        dhcp_leases = self.get_dhcp_leases()
        arp_entries = self.get_arp_table()
        hotspot_users = self.get_hotspot_users()
        
        # Bảng ARP để ánh xạ MAC -> IP
        mac_to_ip = {}
        for entry in arp_entries:
            mac = entry.get('mac-address')
            ip = entry.get('address')
            if mac and ip:
                mac_to_ip[mac] = ip
        
        # Bảng DHCP để ánh xạ MAC -> hostname
        mac_to_hostname = {}
        for lease in dhcp_leases:
            mac = lease.get('mac-address')
            hostname = lease.get('host-name', '')
            if mac:
                mac_to_hostname[mac] = hostname
        
        # Xử lý wireless clients
        for client in wireless_clients:
            mac = client.get('mac-address')
            if not mac:
                continue
                
            ip = mac_to_ip.get(mac, '')
            hostname = mac_to_hostname.get(mac, '')
            
            # Thông tin mới về băng tần
            band = client.get('band', '')
            frequency = client.get('frequency', '')
            channel_width = client.get('channel-width', '')
            ssid = client.get('ssid', '')
            connection_type = client.get('connection-type', 'wireless')
            
            # Định dạng lại thông tin tín hiệu
            signal_strength = client.get('signal-strength', '')
            if signal_strength:
                # Signal strength thường là giá trị âm, ví dụ: -60dBm
                try:
                    signal_value = int(signal_strength)
                    # Đánh giá chất lượng tín hiệu
                    if signal_value >= -50:
                        signal_quality = "Rất tốt"
                    elif signal_value >= -60:
                        signal_quality = "Tốt"
                    elif signal_value >= -70:
                        signal_quality = "Trung bình"
                    else:
                        signal_quality = "Yếu"
                except:
                    signal_quality = "Không xác định"
            else:
                signal_quality = ""
                
            clients.append({
                'mac_address': mac,
                'ip_address': ip,
                'hostname': hostname,
                'interface': client.get('interface', ''),
                'signal': signal_strength,
                'signal_quality': signal_quality,
                'tx_rate': client.get('tx-rate', ''),
                'rx_rate': client.get('rx-rate', ''),
                'band': band,
                'frequency': frequency,
                'channel_width': channel_width,
                'ssid': ssid,
                'connection_type': connection_type,
                'type': 'wireless'
            })
        
        # Xử lý DHCP leases (chỉ thêm những client chưa có)
        for lease in dhcp_leases:
            mac = lease.get('mac-address')
            if not mac:
                continue
                
            # Kiểm tra xem client đã được thêm chưa
            if not any(client['mac_address'] == mac for client in clients):
                ip = lease.get('address', '')
                hostname = lease.get('host-name', '')
                
                clients.append({
                    'mac_address': mac,
                    'ip_address': ip,
                    'hostname': hostname,
                    'interface': '',
                    'signal': '',
                    'signal_quality': '',
                    'tx_rate': '',
                    'rx_rate': '',
                    'band': '',
                    'frequency': '',
                    'channel_width': '',
                    'ssid': '',
                    'connection_type': '',
                    'type': 'wired'
                })
        
        # Xử lý Hotspot users (chỉ thêm những client chưa có)
        for user in hotspot_users:
            mac = user.get('mac-address')
            if not mac:
                continue
                
            # Kiểm tra xem client đã được thêm chưa
            if not any(client['mac_address'] == mac for client in clients):
                ip = user.get('address', '')
                hostname = mac_to_hostname.get(mac, '')
                
                clients.append({
                    'mac_address': mac,
                    'ip_address': ip,
                    'hostname': hostname,
                    'interface': user.get('server', ''),
                    'signal': '',
                    'signal_quality': '',
                    'tx_rate': '',
                    'rx_rate': '',
                    'band': '',
                    'frequency': '',
                    'channel_width': '',
                    'ssid': user.get('server', ''),  # Sử dụng tên server làm SSID cho hotspot
                    'connection_type': 'hotspot',
                    'type': 'hotspot'
                })
                
        # Lấy thông tin traffic cho mỗi client
        for client in clients:
            if client['ip_address']:
                traffic = self.get_client_traffic(ip_address=client['ip_address'])
                if traffic:
                    client['connections'] = traffic['connections']
                    client['tx_bytes'] = traffic['tx_bytes']
                    client['rx_bytes'] = traffic['rx_bytes']
                    client['total_bytes'] = traffic['total_bytes']
        
        return clients

    def get_blocked_clients(self):
        """Lấy danh sách các client đã bị block."""
        if not self.api:
            return []
            
        try:
            # Lấy address list
            address_list_resource = self.api.get_resource('/ip/firewall/address-list')
            
            # Lấy các entry trong blocked_clients
            blocked = address_list_resource.get(list="blocked_clients")
            
            # Bổ sung thông tin về hostname và MAC
            arp_entries = self.get_arp_table()
            dhcp_leases = self.get_dhcp_leases()
            
            # Tạo bảng IP -> MAC và IP -> hostname
            ip_to_mac = {}
            ip_to_hostname = {}
            
            for entry in arp_entries:
                ip = entry.get('address')
                if ip:
                    ip_to_mac[ip] = entry.get('mac-address', '')
            
            for lease in dhcp_leases:
                ip = lease.get('address')
                if ip:
                    ip_to_hostname[ip] = lease.get('host-name', '')
            
            # Bổ sung thông tin
            for entry in blocked:
                ip = entry.get('address')
                if ip:
                    entry['mac-address'] = ip_to_mac.get(ip, '')
                    entry['host-name'] = ip_to_hostname.get(ip, '')
                    
            return blocked
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách blocked clients: {e}")
            return []

    def monitor_clients(self, interval=5, duration=None):
        """Giám sát client theo thời gian thực."""
        if not self.api:
            return
            
        print(f"{Colors.HEADER}{Colors.BOLD}=== GIÁM SÁT CLIENT MIKROTIK ==={Colors.ENDC}")
        
        start_time = time.time()
        end_time = start_time + duration if duration else None
        
        try:
            while True:
                current_time = time.time()
                
                # Kiểm tra thời gian kết thúc
                if end_time and current_time >= end_time:
                    print("\nĐã hoàn thành thời gian giám sát.")
                    break
                
                # Lấy danh sách client hiện tại
                clients = self.get_all_clients()
                
                # Hiển thị
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"{Colors.HEADER}{Colors.BOLD}=== GIÁM SÁT CLIENT MIKROTIK ==={Colors.ENDC}")
                print(f"Thời gian: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Tổng số client: {len(clients)}")
                print()
                
                # Sắp xếp theo traffic
                clients.sort(key=lambda c: c.get('total_bytes', 0), reverse=True)
                
                # Hiển thị table
                header = f"{'IP':<15} {'MAC':<17} {'Hostname':<20} {'Type':<10} {'Interface':<10} {'Signal':<8} {'TX/RX Rate':<15} {'Connections':<11} {'Traffic':<15}"
                print(header)
                print("-" * 120)
                
                for client in clients:
                    ip = client.get('ip_address', '')
                    mac = client.get('mac_address', '')
                    hostname = client.get('hostname', '')[:20]
                    client_type = client.get('type', '')
                    interface = client.get('interface', '')[:10]
                    signal = client.get('signal', '')
                    
                    tx_rate = client.get('tx_rate', '')
                    rx_rate = client.get('rx_rate', '')
                    tx_rx_rate = f"{tx_rate}/{rx_rate}" if tx_rate and rx_rate else ""
                    
                    connections = client.get('connections', 0)
                    
                    # Format traffic
                    total_bytes = client.get('total_bytes', 0)
                    if total_bytes >= 1024 * 1024 * 1024:  # GB
                        traffic = f"{total_bytes / (1024 * 1024 * 1024):.2f} GB"
                    elif total_bytes >= 1024 * 1024:  # MB
                        traffic = f"{total_bytes / (1024 * 1024):.2f} MB"
                    elif total_bytes >= 1024:  # KB
                        traffic = f"{total_bytes / 1024:.2f} KB"
                    else:
                        traffic = f"{total_bytes} B"
                    
                    row = f"{ip:<15} {mac:<17} {hostname:<20} {client_type:<10} {interface:<10} {signal:<8} {tx_rx_rate:<15} {connections:<11} {traffic:<15}"
                    print(row)
                
                # Đã hiển thị xong, đợi đến interval tiếp theo
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nĐã dừng giám sát.")

    def export_clients_to_json(self, output_file):
        """Xuất danh sách client sang file JSON."""
        clients = self.get_all_clients()
        blocked = self.get_blocked_clients()
        
        # Chuyển blocked list sang dạng dễ sử dụng
        blocked_ips = [entry.get('address') for entry in blocked]
        
        # Bổ sung thông tin về trạng thái blocked
        for client in clients:
            client['blocked'] = client.get('ip_address') in blocked_ips
        
        # Chuẩn bị dữ liệu để xuất
        export_data = {
            "clients": clients,
            "blocked_clients": blocked,
            "generated_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_clients": len(clients),
            "total_blocked": len(blocked)
        }
        
        # Ghi dữ liệu ra file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            print(f"{Colors.GREEN}Đã xuất danh sách client sang {output_file}{Colors.ENDC}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi xuất dữ liệu: {e}")
            return False


def main():
    """Hàm chính để chạy công cụ giám sát client."""
    # Load environment variables
    load_dotenv()
    
    # Lấy thông tin kết nối từ biến môi trường hoặc command line arguments
    parser = argparse.ArgumentParser(description='Công cụ giám sát client trên MikroTik')
    parser.add_argument('--host', default=os.getenv('MIKROTIK_HOST'), help='Địa chỉ IP của thiết bị MikroTik')
    parser.add_argument('--user', default=os.getenv('MIKROTIK_USER'), help='Tên đăng nhập')
    parser.add_argument('--password', default=os.getenv('MIKROTIK_PASSWORD'), help='Mật khẩu')
    
    # Các lệnh
    subparsers = parser.add_subparsers(dest='command', help='Lệnh')
    
    # Lệnh list clients
    list_parser = subparsers.add_parser('list', help='Liệt kê clients')
    
    # Lệnh list wireless clients
    wireless_parser = subparsers.add_parser('wireless', help='Liệt kê wireless clients')
    
    # Lệnh list dhcp leases
    dhcp_parser = subparsers.add_parser('dhcp', help='Liệt kê DHCP leases')
    
    # Lệnh list hotspot users
    hotspot_parser = subparsers.add_parser('hotspot', help='Liệt kê hotspot users')
    
    # Lệnh list blocked clients
    blocked_parser = subparsers.add_parser('blocked', help='Liệt kê blocked clients')
    
    # Lệnh block client
    block_parser = subparsers.add_parser('block', help='Block client')
    block_parser.add_argument('--ip', help='Địa chỉ IP của client')
    block_parser.add_argument('--mac', help='MAC address của client')
    block_parser.add_argument('--comment', help='Ghi chú')
    
    # Lệnh unblock client
    unblock_parser = subparsers.add_parser('unblock', help='Unblock client')
    unblock_parser.add_argument('--ip', help='Địa chỉ IP của client')
    unblock_parser.add_argument('--mac', help='MAC address của client')
    
    # Lệnh get traffic
    traffic_parser = subparsers.add_parser('traffic', help='Lấy thông tin traffic của client')
    traffic_parser.add_argument('--ip', help='Địa chỉ IP của client')
    traffic_parser.add_argument('--mac', help='MAC address của client')
    
    # Lệnh monitor
    monitor_parser = subparsers.add_parser('monitor', help='Giám sát client theo thời gian thực')
    monitor_parser.add_argument('--interval', type=int, default=5, help='Khoảng thời gian cập nhật (giây, mặc định: 5)')
    monitor_parser.add_argument('--duration', type=int, help='Thời gian giám sát (giây, để trống để giám sát vô thời hạn)')
    
    # Lệnh export
    export_parser = subparsers.add_parser('export', help='Xuất danh sách client')
    export_parser.add_argument('--output', default='clients.json', help='Tên file output (mặc định: clients.json)')
    
    args = parser.parse_args()
    
    # Kiểm tra thông tin kết nối
    if not args.host or not args.user or not args.password:
        print(f"{Colors.RED}Lỗi: Thiếu thông tin kết nối MikroTik.{Colors.ENDC}")
        print(f"{Colors.RED}Vui lòng cung cấp thông tin qua biến môi trường hoặc command line arguments.{Colors.ENDC}")
        parser.print_help()
        return
    
    # Khởi tạo đối tượng giám sát client
    client_monitor = MikroTikClientMonitor(args.host, args.user, args.password)
    api = client_monitor.connect()
    
    if not api:
        print(f"{Colors.RED}Lỗi: Không thể kết nối đến MikroTik.{Colors.ENDC}")
        return
    
    try:
        # Xử lý các lệnh
        if args.command == 'list':
            clients = client_monitor.get_all_clients()
            if clients:
                print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH CLIENT ==={Colors.ENDC}")
                print(f"Tổng số client: {len(clients)}")
                print()
                
                # Hiển thị table
                header = f"{'IP':<15} {'MAC':<17} {'Hostname':<20} {'Type':<10} {'Interface':<10} {'Signal':<8} {'Connections':<11} {'Traffic':<15}"
                print(header)
                print("-" * 100)
                
                for client in clients:
                    ip = client.get('ip_address', '')
                    mac = client.get('mac_address', '')
                    hostname = client.get('hostname', '')[:20]
                    client_type = client.get('type', '')
                    interface = client.get('interface', '')[:10]
                    signal = client.get('signal', '')
                    connections = client.get('connections', 0)
                    
                    # Format traffic
                    total_bytes = client.get('total_bytes', 0)
                    if total_bytes >= 1024 * 1024 * 1024:  # GB
                        traffic = f"{total_bytes / (1024 * 1024 * 1024):.2f} GB"
                    elif total_bytes >= 1024 * 1024:  # MB
                        traffic = f"{total_bytes / (1024 * 1024):.2f} MB"
                    elif total_bytes >= 1024:  # KB
                        traffic = f"{total_bytes / 1024:.2f} KB"
                    else:
                        traffic = f"{total_bytes} B"
                    
                    row = f"{ip:<15} {mac:<17} {hostname:<20} {client_type:<10} {interface:<10} {signal:<8} {connections:<11} {traffic:<15}"
                    print(row)
            else:
                print(f"{Colors.WARNING}Không có client nào được tìm thấy.{Colors.ENDC}")
                
        elif args.command == 'wireless':
            clients = client_monitor.get_wireless_clients()
            if clients:
                print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH WIRELESS CLIENT ==={Colors.ENDC}")
                print(f"Tổng số client: {len(clients)}")
                print()
                
                for i, client in enumerate(clients):
                    print(f"{i+1}. MAC: {client.get('mac-address', '')}")
                    if client.get('interface'):
                        print(f"   Interface: {client.get('interface')}")
                    if client.get('signal-strength'):
                        print(f"   Signal: {client.get('signal-strength')}")
                    if client.get('tx-rate') and client.get('rx-rate'):
                        print(f"   TX/RX Rate: {client.get('tx-rate')}/{client.get('rx-rate')}")
                    print()
            else:
                print(f"{Colors.WARNING}Không có wireless client nào được tìm thấy.{Colors.ENDC}")
                
        elif args.command == 'dhcp':
            leases = client_monitor.get_dhcp_leases()
            if leases:
                print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH DHCP LEASES ==={Colors.ENDC}")
                print(f"Tổng số: {len(leases)}")
                print()
                
                for i, lease in enumerate(leases):
                    print(f"{i+1}. IP: {lease.get('address', '')}")
                    print(f"   MAC: {lease.get('mac-address', '')}")
                    if lease.get('host-name'):
                        print(f"   Hostname: {lease.get('host-name')}")
                    if lease.get('server'):
                        print(f"   Server: {lease.get('server')}")
                    if lease.get('expires-after'):
                        print(f"   Expires: {lease.get('expires-after')}")
                    print()
            else:
                print(f"{Colors.WARNING}Không có DHCP lease nào được tìm thấy.{Colors.ENDC}")
                
        elif args.command == 'hotspot':
            users = client_monitor.get_hotspot_users()
            if users:
                print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH HOTSPOT USERS ==={Colors.ENDC}")
                print(f"Tổng số: {len(users)}")
                print()
                
                for i, user in enumerate(users):
                    print(f"{i+1}. IP: {user.get('address', '')}")
                    print(f"   MAC: {user.get('mac-address', '')}")
                    if user.get('user'):
                        print(f"   User: {user.get('user')}")
                    if user.get('uptime'):
                        print(f"   Uptime: {user.get('uptime')}")
                    if user.get('server'):
                        print(f"   Server: {user.get('server')}")
                    print()
            else:
                print(f"{Colors.WARNING}Không có hotspot user nào được tìm thấy.{Colors.ENDC}")
                
        elif args.command == 'blocked':
            blocked = client_monitor.get_blocked_clients()
            if blocked:
                print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH BLOCKED CLIENTS ==={Colors.ENDC}")
                print(f"Tổng số: {len(blocked)}")
                print()
                
                for i, entry in enumerate(blocked):
                    print(f"{i+1}. IP: {entry.get('address', '')}")
                    if entry.get('mac-address'):
                        print(f"   MAC: {entry.get('mac-address')}")
                    if entry.get('host-name'):
                        print(f"   Hostname: {entry.get('host-name')}")
                    if entry.get('comment'):
                        print(f"   Comment: {entry.get('comment')}")
                    if entry.get('timeout'):
                        print(f"   Timeout: {entry.get('timeout')}")
                    print()
            else:
                print(f"{Colors.WARNING}Không có client nào bị block.{Colors.ENDC}")
                
        elif args.command == 'block':
            if not args.ip and not args.mac:
                print(f"{Colors.RED}Lỗi: Phải cung cấp địa chỉ IP hoặc MAC.{Colors.ENDC}")
                return
                
            if client_monitor.block_client(args.ip, args.mac, args.comment):
                target = args.ip or args.mac
                print(f"{Colors.GREEN}Đã block client {target} thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể block client.{Colors.ENDC}")
                
        elif args.command == 'unblock':
            if not args.ip and not args.mac:
                print(f"{Colors.RED}Lỗi: Phải cung cấp địa chỉ IP hoặc MAC.{Colors.ENDC}")
                return
                
            if client_monitor.unblock_client(args.ip, args.mac):
                target = args.ip or args.mac
                print(f"{Colors.GREEN}Đã unblock client {target} thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể unblock client.{Colors.ENDC}")
                
        elif args.command == 'traffic':
            if not args.ip and not args.mac:
                print(f"{Colors.RED}Lỗi: Phải cung cấp địa chỉ IP hoặc MAC.{Colors.ENDC}")
                return
                
            traffic = client_monitor.get_client_traffic(args.ip, args.mac)
            if traffic:
                target = args.ip or args.mac
                print(f"{Colors.HEADER}{Colors.BOLD}=== THÔNG TIN TRAFFIC CỦA {target} ==={Colors.ENDC}")
                print(f"Số kết nối: {traffic['connections']}")
                
                # TX
                tx_bytes = traffic['tx_bytes']
                if tx_bytes >= 1024 * 1024 * 1024:  # GB
                    tx_str = f"{tx_bytes / (1024 * 1024 * 1024):.2f} GB"
                elif tx_bytes >= 1024 * 1024:  # MB
                    tx_str = f"{tx_bytes / (1024 * 1024):.2f} MB"
                elif tx_bytes >= 1024:  # KB
                    tx_str = f"{tx_bytes / 1024:.2f} KB"
                else:
                    tx_str = f"{tx_bytes} B"
                print(f"TX: {tx_str}")
                
                # RX
                rx_bytes = traffic['rx_bytes']
                if rx_bytes >= 1024 * 1024 * 1024:  # GB
                    rx_str = f"{rx_bytes / (1024 * 1024 * 1024):.2f} GB"
                elif rx_bytes >= 1024 * 1024:  # MB
                    rx_str = f"{rx_bytes / (1024 * 1024):.2f} MB"
                elif rx_bytes >= 1024:  # KB
                    rx_str = f"{rx_bytes / 1024:.2f} KB"
                else:
                    rx_str = f"{rx_bytes} B"
                print(f"RX: {rx_str}")
                
                # Tổng
                total_bytes = traffic['total_bytes']
                if total_bytes >= 1024 * 1024 * 1024:  # GB
                    total_str = f"{total_bytes / (1024 * 1024 * 1024):.2f} GB"
                elif total_bytes >= 1024 * 1024:  # MB
                    total_str = f"{total_bytes / (1024 * 1024):.2f} MB"
                elif total_bytes >= 1024:  # KB
                    total_str = f"{total_bytes / 1024:.2f} KB"
                else:
                    total_str = f"{total_bytes} B"
                print(f"Tổng: {total_str}")
            else:
                print(f"{Colors.WARNING}Không thể lấy thông tin traffic cho client.{Colors.ENDC}")
                
        elif args.command == 'monitor':
            client_monitor.monitor_clients(args.interval, args.duration)
                
        elif args.command == 'export':
            client_monitor.export_clients_to_json(args.output)
                
        else:
            # Nếu không có lệnh nào được chỉ định, hiển thị trợ giúp
            parser.print_help()
    
    finally:
        # Đảm bảo luôn ngắt kết nối
        client_monitor.disconnect()


if __name__ == "__main__":
    main()