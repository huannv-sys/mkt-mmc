#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quản lý Firewall trên thiết bị MikroTik
Script này giúp quản lý các rule firewall, NAT và filter trên thiết bị MikroTik
"""

import os
import sys
import time
import json
import logging
import argparse
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
logger = logging.getLogger('mikrotik_firewall')

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


class MikroTikFirewallManager:
    """Lớp quản lý Firewall trên thiết bị MikroTik."""

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

    def get_filter_rules(self):
        """Lấy danh sách các filter rules."""
        if not self.api:
            return []
            
        try:
            rules = self.api.get_resource('/ip/firewall/filter').get()
            return rules
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách filter rules: {e}")
            return []

    def get_nat_rules(self):
        """Lấy danh sách các NAT rules."""
        if not self.api:
            return []
            
        try:
            rules = self.api.get_resource('/ip/firewall/nat').get()
            return rules
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách NAT rules: {e}")
            return []

    def get_mangle_rules(self):
        """Lấy danh sách các mangle rules."""
        if not self.api:
            return []
            
        try:
            rules = self.api.get_resource('/ip/firewall/mangle').get()
            return rules
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách mangle rules: {e}")
            return []

    def get_address_lists(self):
        """Lấy danh sách các address lists."""
        if not self.api:
            return []
            
        try:
            address_lists = self.api.get_resource('/ip/firewall/address-list').get()
            return address_lists
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách address lists: {e}")
            return []

    def get_connection_tracking(self):
        """Lấy thông tin connection tracking."""
        if not self.api:
            return None
            
        try:
            connection_tracking = self.api.get_resource('/ip/firewall/connection').get()
            return connection_tracking
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin connection tracking: {e}")
            return None

    def add_filter_rule(self, chain="forward", action="accept", src_address=None, dst_address=None, 
                    protocol=None, src_port=None, dst_port=None, comment=None, disabled=False,
                    position=None):
        """Thêm một filter rule mới."""
        if not self.api:
            return False
            
        try:
            # Lấy resource
            filter_resource = self.api.get_resource('/ip/firewall/filter')
            
            # Params cơ bản
            params = {
                "chain": chain,
                "action": action
            }
            
            # Thêm các tham số khác nếu được chỉ định
            if src_address:
                params["src-address"] = src_address
            if dst_address:
                params["dst-address"] = dst_address
            if protocol:
                params["protocol"] = protocol
            if src_port:
                params["src-port"] = str(src_port)
            if dst_port:
                params["dst-port"] = str(dst_port)
            if comment:
                params["comment"] = comment
            if disabled:
                params["disabled"] = "yes"
                
            # Thêm rule
            if position is not None:
                filter_resource.insert(position=position, **params)
                logger.info(f"Đã thêm filter rule tại vị trí {position}")
            else:
                filter_resource.add(**params)
                logger.info("Đã thêm filter rule")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm filter rule: {e}")
            return False

    def add_nat_rule(self, chain="srcnat", action="masquerade", src_address=None, dst_address=None, 
                  to_addresses=None, protocol=None, dst_port=None, to_ports=None, 
                  comment=None, disabled=False, position=None, out_interface=None, in_interface=None):
        """Thêm một NAT rule mới."""
        if not self.api:
            return False
            
        try:
            # Lấy resource
            nat_resource = self.api.get_resource('/ip/firewall/nat')
            
            # Params cơ bản
            params = {
                "chain": chain,
                "action": action
            }
            
            # Thêm các tham số khác nếu được chỉ định
            if src_address:
                params["src-address"] = src_address
            if dst_address:
                params["dst-address"] = dst_address
            if to_addresses:
                params["to-addresses"] = to_addresses
            if protocol:
                params["protocol"] = protocol
            if dst_port:
                params["dst-port"] = str(dst_port)
            if to_ports:
                params["to-ports"] = str(to_ports)
            if out_interface:
                params["out-interface"] = out_interface
            if in_interface:
                params["in-interface"] = in_interface
            if comment:
                params["comment"] = comment
            if disabled:
                params["disabled"] = "yes"
                
            # Thêm rule
            if position is not None:
                nat_resource.insert(position=position, **params)
                logger.info(f"Đã thêm NAT rule tại vị trí {position}")
            else:
                nat_resource.add(**params)
                logger.info("Đã thêm NAT rule")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm NAT rule: {e}")
            return False

    def add_port_forward(self, dst_port, to_address, to_port=None, protocol="tcp", comment=None, disabled=False):
        """Thêm một rule chuyển tiếp cổng (dstnat)."""
        to_port = to_port or dst_port
        comment = comment or f"Port forward {dst_port} to {to_address}:{to_port}"
        
        return self.add_nat_rule(
            chain="dstnat",
            action="dst-nat",
            protocol=protocol,
            dst_port=dst_port,
            to_addresses=to_address,
            to_ports=to_port,
            comment=comment,
            disabled=disabled
        )

    def remove_firewall_rule(self, rule_type, rule_id):
        """Xóa một firewall rule."""
        if not self.api:
            return False
            
        try:
            # Xác định resource dựa vào loại rule
            if rule_type == "filter":
                resource = self.api.get_resource('/ip/firewall/filter')
            elif rule_type == "nat":
                resource = self.api.get_resource('/ip/firewall/nat')
            elif rule_type == "mangle":
                resource = self.api.get_resource('/ip/firewall/mangle')
            else:
                logger.error(f"Loại rule không hợp lệ: {rule_type}")
                return False
                
            # Xóa rule
            resource.remove(id=rule_id)
            logger.info(f"Đã xóa {rule_type} rule với ID: {rule_id}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi xóa {rule_type} rule: {e}")
            return False

    def enable_disable_rule(self, rule_type, rule_id, enabled=True):
        """Bật hoặc tắt một firewall rule."""
        if not self.api:
            return False
            
        try:
            # Xác định resource dựa vào loại rule
            if rule_type == "filter":
                resource = self.api.get_resource('/ip/firewall/filter')
            elif rule_type == "nat":
                resource = self.api.get_resource('/ip/firewall/nat')
            elif rule_type == "mangle":
                resource = self.api.get_resource('/ip/firewall/mangle')
            else:
                logger.error(f"Loại rule không hợp lệ: {rule_type}")
                return False
                
            # Bật/tắt rule
            resource.set(id=rule_id, disabled="no" if enabled else "yes")
            status = "bật" if enabled else "tắt"
            logger.info(f"Đã {status} {rule_type} rule với ID: {rule_id}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thay đổi trạng thái {rule_type} rule: {e}")
            return False

    def add_to_address_list(self, address, list_name, comment=None, timeout=None):
        """Thêm một địa chỉ vào address list."""
        if not self.api:
            return False
            
        try:
            # Lấy resource
            address_list_resource = self.api.get_resource('/ip/firewall/address-list')
            
            # Params cơ bản
            params = {
                "address": address,
                "list": list_name
            }
            
            # Thêm các tham số khác nếu được chỉ định
            if comment:
                params["comment"] = comment
            if timeout:
                params["timeout"] = timeout
                
            # Thêm địa chỉ vào list
            address_list_resource.add(**params)
            logger.info(f"Đã thêm địa chỉ {address} vào address list {list_name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm địa chỉ vào address list: {e}")
            return False

    def remove_from_address_list(self, address, list_name=None):
        """Xóa một địa chỉ khỏi address list."""
        if not self.api:
            return False
            
        try:
            # Lấy resource
            address_list_resource = self.api.get_resource('/ip/firewall/address-list')
            
            # Tìm entries phù hợp
            if list_name:
                entries = address_list_resource.get(address=address, list=list_name)
            else:
                entries = address_list_resource.get(address=address)
            
            if not entries:
                logger.warning(f"Không tìm thấy địa chỉ {address} trong address list")
                return False
                
            # Xóa các entries tìm được
            for entry in entries:
                address_list_resource.remove(id=entry.get('.id'))
                logger.info(f"Đã xóa địa chỉ {address} khỏi address list {entry.get('list')}")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi xóa địa chỉ khỏi address list: {e}")
            return False

    def create_basic_firewall(self):
        """Tạo một bộ firewall cơ bản với các quy tắc bảo mật."""
        if not self.api:
            return False
            
        try:
            # Lấy các resources
            filter_resource = self.api.get_resource('/ip/firewall/filter')
            
            # Tạo các address lists
            self.add_to_address_list("0.0.0.0/8", "bogons", "Bogon network")
            self.add_to_address_list("10.0.0.0/8", "bogons", "Bogon network")
            self.add_to_address_list("100.64.0.0/10", "bogons", "Bogon network")
            self.add_to_address_list("127.0.0.0/8", "bogons", "Bogon network")
            self.add_to_address_list("169.254.0.0/16", "bogons", "Bogon network")
            self.add_to_address_list("172.16.0.0/12", "bogons", "Bogon network")
            self.add_to_address_list("192.0.0.0/24", "bogons", "Bogon network")
            self.add_to_address_list("192.0.2.0/24", "bogons", "Bogon network")
            self.add_to_address_list("192.168.0.0/16", "bogons", "Bogon network")
            self.add_to_address_list("198.18.0.0/15", "bogons", "Bogon network")
            self.add_to_address_list("198.51.100.0/24", "bogons", "Bogon network")
            self.add_to_address_list("203.0.113.0/24", "bogons", "Bogon network")
            self.add_to_address_list("224.0.0.0/4", "bogons", "Bogon network")
            self.add_to_address_list("240.0.0.0/4", "bogons", "Bogon network")
            
            # Chain input
            # Allow established and related
            filter_resource.add(
                chain="input",
                action="accept",
                connection_state="established,related",
                comment="Allow established and related"
            )
            
            # Allow ICMP
            filter_resource.add(
                chain="input",
                action="accept",
                protocol="icmp",
                comment="Allow ICMP"
            )
            
            # Allow from LAN
            filter_resource.add(
                chain="input",
                action="accept",
                src_address="192.168.0.0/16",
                comment="Allow from LAN"
            )
            
            # Allow SSH from specific address if provided
            ssh_admin_address = input("Nhập địa chỉ IP để cho phép SSH từ xa (để trống nếu không cần): ")
            if ssh_admin_address:
                filter_resource.add(
                    chain="input",
                    action="accept",
                    protocol="tcp",
                    dst_port="22",
                    src_address=ssh_admin_address,
                    comment="Allow SSH from admin"
                )
            
            # Block Bogons
            filter_resource.add(
                chain="input",
                action="drop",
                src_address_list="bogons",
                comment="Drop bogon networks"
            )
            
            # Default drop for input
            filter_resource.add(
                chain="input",
                action="drop",
                comment="Default drop rule"
            )
            
            # Chain forward
            # Allow established and related
            filter_resource.add(
                chain="forward",
                action="accept",
                connection_state="established,related",
                comment="Allow established and related"
            )
            
            # Allow from LAN to WAN
            filter_resource.add(
                chain="forward",
                action="accept",
                src_address="192.168.0.0/16",
                connection_state="new",
                comment="Allow LAN to WAN"
            )
            
            # Block Bogons
            filter_resource.add(
                chain="forward",
                action="drop",
                src_address_list="bogons",
                comment="Drop bogon networks"
            )
            
            # Default drop for forward
            filter_resource.add(
                chain="forward",
                action="drop",
                comment="Default drop rule"
            )
            
            logger.info("Đã tạo các quy tắc firewall cơ bản")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tạo firewall cơ bản: {e}")
            return False
    
    def setup_basic_nat(self, wan_interface="ether1"):
        """Thiết lập NAT cơ bản với masquerade."""
        if not self.api:
            return False
            
        try:
            # Kiểm tra xem interface có tồn tại không
            interfaces = self.api.get_resource('/interface').get()
            interface_exists = any(intf['name'] == wan_interface for intf in interfaces)
            
            if not interface_exists:
                logger.error(f"Interface {wan_interface} không tồn tại")
                return False
                
            # Thêm rule masquerade
            return self.add_nat_rule(
                chain="srcnat",
                action="masquerade",
                out_interface=wan_interface,
                comment=f"Masquerade traffic through {wan_interface}"
            )
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập NAT cơ bản: {e}")
            return False
            
    def add_snat_rule(self, src_address, to_address, out_interface=None, protocol=None, 
                     src_port=None, to_ports=None, comment=None, disabled=False):
        """Thêm một rule source NAT (SNAT) để thay đổi địa chỉ nguồn."""
        try:
            return self.add_nat_rule(
                chain="srcnat",
                action="src-nat",
                src_address=src_address,
                protocol=protocol,
                dst_port=src_port,  # Trong trường hợp SNAT, thông thường không dùng src_port
                to_addresses=to_address,
                to_ports=to_ports,
                out_interface=out_interface,
                comment=comment or f"SNAT {src_address} -> {to_address}",
                disabled=disabled
            )
        except Exception as e:
            logger.error(f"Lỗi khi thêm SNAT rule: {e}")
            return False
            
    def add_dnat_rule(self, dst_address, to_address, in_interface=None, protocol="tcp", 
                     dst_port=None, to_ports=None, comment=None, disabled=False):
        """Thêm một rule destination NAT (DNAT) để thay đổi địa chỉ đích."""
        try:
            return self.add_nat_rule(
                chain="dstnat",
                action="dst-nat",
                dst_address=dst_address,
                protocol=protocol,
                dst_port=dst_port,
                to_addresses=to_address,
                to_ports=to_ports,
                in_interface=in_interface,
                comment=comment or f"DNAT {dst_address}:{dst_port or '*'} -> {to_address}:{to_ports or dst_port or '*'}",
                disabled=disabled
            )
        except Exception as e:
            logger.error(f"Lỗi khi thêm DNAT rule: {e}")
            return False
            
    def add_masquerade_rule(self, src_address, out_interface=None, comment=None, disabled=False):
        """Thêm một rule masquerade cho mạng nội bộ."""
        try:
            return self.add_nat_rule(
                chain="srcnat",
                action="masquerade",
                src_address=src_address,
                out_interface=out_interface,
                comment=comment or f"Masquerade {src_address}",
                disabled=disabled
            )
        except Exception as e:
            logger.error(f"Lỗi khi thêm masquerade rule: {e}")
            return False
            
    def add_hairpin_nat(self, external_ip, internal_ip, port, protocol="tcp", comment=None):
        """Thêm hairpin NAT (NAT reflection) để có thể truy cập server nội bộ bằng IP external từ mạng nội bộ."""
        try:
            # 1. Thêm rule DNAT từ bên ngoài vào server nội bộ
            self.add_dnat_rule(
                dst_address=external_ip,
                to_address=internal_ip,
                protocol=protocol,
                dst_port=port,
                comment=comment or f"Hairpin NAT External: {external_ip}:{port} -> {internal_ip}:{port}"
            )
            
            # 2. Thêm rule DNAT cho phép truy cập từ mạng nội bộ ra server nội bộ thông qua IP public
            self.add_dnat_rule(
                dst_address=external_ip,
                to_address=internal_ip,
                protocol=protocol,
                dst_port=port,
                comment=comment or f"Hairpin NAT Internal: {external_ip}:{port} -> {internal_ip}:{port}"
            )
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm hairpin NAT: {e}")
            return False
            
    def add_1to1_nat(self, public_ip, private_ip, comment=None):
        """Thêm NAT 1:1 (ánh xạ toàn bộ IP public vào IP private)."""
        try:
            # 1. DNAT để chuyển hướng traffic từ public IP vào private IP
            self.add_dnat_rule(
                dst_address=public_ip,
                to_address=private_ip,
                comment=comment or f"1:1 NAT DNAT: {public_ip} -> {private_ip}"
            )
            
            # 2. SNAT để traffic từ private IP ra ngoài có IP nguồn là public IP
            self.add_snat_rule(
                src_address=private_ip,
                to_address=public_ip,
                comment=comment or f"1:1 NAT SNAT: {private_ip} -> {public_ip}"
            )
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm 1:1 NAT: {e}")
            return False


def main():
    """Hàm chính để chạy công cụ quản lý Firewall."""
    # Load environment variables
    load_dotenv()
    
    # Lấy thông tin kết nối từ biến môi trường hoặc command line arguments
    parser = argparse.ArgumentParser(description='Công cụ quản lý Firewall trên MikroTik')
    parser.add_argument('--host', default=os.getenv('MIKROTIK_HOST'), help='Địa chỉ IP của thiết bị MikroTik')
    parser.add_argument('--user', default=os.getenv('MIKROTIK_USER'), help='Tên đăng nhập')
    parser.add_argument('--password', default=os.getenv('MIKROTIK_PASSWORD'), help='Mật khẩu')
    
    # Các lệnh
    subparsers = parser.add_subparsers(dest='command', help='Lệnh')
    
    # Lệnh list filter rules
    list_filter_parser = subparsers.add_parser('list-filter', help='Liệt kê filter rules')
    
    # Lệnh list NAT rules
    list_nat_parser = subparsers.add_parser('list-nat', help='Liệt kê NAT rules')
    
    # Lệnh list address lists
    list_address_parser = subparsers.add_parser('list-address', help='Liệt kê address lists')
    
    # Lệnh add filter rule
    add_filter_parser = subparsers.add_parser('add-filter', help='Thêm filter rule')
    add_filter_parser.add_argument('--chain', default='forward', choices=['input', 'forward', 'output'], help='Chain (mặc định: forward)')
    add_filter_parser.add_argument('--action', default='accept', choices=['accept', 'drop', 'reject', 'log'], help='Action (mặc định: accept)')
    add_filter_parser.add_argument('--src-address', help='Source address')
    add_filter_parser.add_argument('--dst-address', help='Destination address')
    add_filter_parser.add_argument('--protocol', choices=['tcp', 'udp', 'icmp'], help='Protocol')
    add_filter_parser.add_argument('--src-port', help='Source port')
    add_filter_parser.add_argument('--dst-port', help='Destination port')
    add_filter_parser.add_argument('--comment', help='Comment')
    add_filter_parser.add_argument('--disabled', action='store_true', help='Disable rule')
    add_filter_parser.add_argument('--position', type=int, help='Position')
    
    # Lệnh add port forward
    add_forward_parser = subparsers.add_parser('add-forward', help='Thêm port forward rule')
    add_forward_parser.add_argument('--dst-port', required=True, help='Destination port')
    add_forward_parser.add_argument('--to-address', required=True, help='Forward to address')
    add_forward_parser.add_argument('--to-port', help='Forward to port (mặc định: giống dst-port)')
    add_forward_parser.add_argument('--protocol', default='tcp', choices=['tcp', 'udp'], help='Protocol (mặc định: tcp)')
    add_forward_parser.add_argument('--comment', help='Comment')
    add_forward_parser.add_argument('--disabled', action='store_true', help='Disable rule')
    
    # Lệnh remove rule
    remove_rule_parser = subparsers.add_parser('remove-rule', help='Xóa rule')
    remove_rule_parser.add_argument('--type', required=True, choices=['filter', 'nat', 'mangle'], help='Loại rule')
    remove_rule_parser.add_argument('--id', required=True, help='ID của rule')
    
    # Lệnh enable/disable rule
    toggle_rule_parser = subparsers.add_parser('toggle-rule', help='Bật/tắt rule')
    toggle_rule_parser.add_argument('--type', required=True, choices=['filter', 'nat', 'mangle'], help='Loại rule')
    toggle_rule_parser.add_argument('--id', required=True, help='ID của rule')
    toggle_rule_parser.add_argument('--enable', action='store_true', default=True, help='Bật rule (mặc định)')
    toggle_rule_parser.add_argument('--disable', action='store_true', help='Tắt rule')
    
    # Lệnh add address to address list
    add_address_parser = subparsers.add_parser('add-address', help='Thêm địa chỉ vào address list')
    add_address_parser.add_argument('--address', required=True, help='Địa chỉ IP hoặc network')
    add_address_parser.add_argument('--list', required=True, help='Tên address list')
    add_address_parser.add_argument('--comment', help='Comment')
    add_address_parser.add_argument('--timeout', help='Timeout (ví dụ: 1d, 2h, 30m)')
    
    # Lệnh remove address from address list
    remove_address_parser = subparsers.add_parser('remove-address', help='Xóa địa chỉ khỏi address list')
    remove_address_parser.add_argument('--address', required=True, help='Địa chỉ IP hoặc network')
    remove_address_parser.add_argument('--list', help='Tên address list (để trống để xóa khỏi tất cả các list)')
    
    # Lệnh create basic firewall
    basic_firewall_parser = subparsers.add_parser('basic-firewall', help='Tạo firewall cơ bản')
    
    # Lệnh setup basic NAT
    basic_nat_parser = subparsers.add_parser('basic-nat', help='Thiết lập NAT cơ bản')
    basic_nat_parser.add_argument('--interface', default='ether1', help='Interface WAN (mặc định: ether1)')
    
    args = parser.parse_args()
    
    # Kiểm tra thông tin kết nối
    if not args.host or not args.user or not args.password:
        print(f"{Colors.RED}Lỗi: Thiếu thông tin kết nối MikroTik.{Colors.ENDC}")
        print(f"{Colors.RED}Vui lòng cung cấp thông tin qua biến môi trường hoặc command line arguments.{Colors.ENDC}")
        parser.print_help()
        return
    
    # Khởi tạo đối tượng quản lý Firewall
    firewall = MikroTikFirewallManager(args.host, args.user, args.password)
    api = firewall.connect()
    
    if not api:
        print(f"{Colors.RED}Lỗi: Không thể kết nối đến MikroTik.{Colors.ENDC}")
        return
    
    try:
        # Xử lý các lệnh
        if args.command == 'list-filter':
            rules = firewall.get_filter_rules()
            if rules:
                print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH FILTER RULES ==={Colors.ENDC}")
                for i, rule in enumerate(rules):
                    disabled = " [disabled]" if rule.get('disabled') == "true" else ""
                    print(f"{i+1}. {rule.get('chain')} | {rule.get('action')}{disabled}")
                    
                    # Hiển thị các thông số quan trọng
                    if rule.get('src-address'):
                        print(f"   Src: {rule.get('src-address')}")
                    if rule.get('dst-address'):
                        print(f"   Dst: {rule.get('dst-address')}")
                    if rule.get('protocol'):
                        ports = ""
                        if rule.get('dst-port'):
                            ports = f" (port {rule.get('dst-port')})"
                        print(f"   Protocol: {rule.get('protocol')}{ports}")
                    if rule.get('comment'):
                        print(f"   Comment: {rule.get('comment')}")
                    print(f"   ID: {rule.get('.id')}")
                    print()
            else:
                print(f"{Colors.WARNING}Không có filter rule nào.{Colors.ENDC}")
                
        elif args.command == 'list-nat':
            rules = firewall.get_nat_rules()
            if rules:
                print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH NAT RULES ==={Colors.ENDC}")
                for i, rule in enumerate(rules):
                    disabled = " [disabled]" if rule.get('disabled') == "true" else ""
                    print(f"{i+1}. {rule.get('chain')} | {rule.get('action')}{disabled}")
                    
                    # Hiển thị các thông số quan trọng
                    if rule.get('src-address'):
                        print(f"   Src: {rule.get('src-address')}")
                    if rule.get('dst-address'):
                        print(f"   Dst: {rule.get('dst-address')}")
                    if rule.get('to-addresses'):
                        print(f"   To: {rule.get('to-addresses')}")
                    if rule.get('protocol'):
                        src_port = f" src-port: {rule.get('src-port')}" if rule.get('src-port') else ""
                        dst_port = f" dst-port: {rule.get('dst-port')}" if rule.get('dst-port') else ""
                        to_ports = f" to-ports: {rule.get('to-ports')}" if rule.get('to-ports') else ""
                        print(f"   Protocol: {rule.get('protocol')}{src_port}{dst_port}{to_ports}")
                    if rule.get('comment'):
                        print(f"   Comment: {rule.get('comment')}")
                    print(f"   ID: {rule.get('.id')}")
                    print()
            else:
                print(f"{Colors.WARNING}Không có NAT rule nào.{Colors.ENDC}")
                
        elif args.command == 'list-address':
            address_lists = firewall.get_address_lists()
            if address_lists:
                # Tổ chức lại theo list name
                lists = {}
                for entry in address_lists:
                    list_name = entry.get('list')
                    if list_name not in lists:
                        lists[list_name] = []
                    lists[list_name].append(entry)
                
                print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH ADDRESS LISTS ==={Colors.ENDC}")
                for list_name, entries in lists.items():
                    print(f"{Colors.BOLD}{list_name}{Colors.ENDC} ({len(entries)} entries)")
                    for entry in entries:
                        timeout = f" (timeout: {entry.get('timeout')})" if entry.get('timeout') else ""
                        comment = f" - {entry.get('comment')}" if entry.get('comment') else ""
                        print(f"   {entry.get('address')}{timeout}{comment}")
                    print()
            else:
                print(f"{Colors.WARNING}Không có address list nào.{Colors.ENDC}")
                
        elif args.command == 'add-filter':
            if firewall.add_filter_rule(
                chain=args.chain,
                action=args.action,
                src_address=args.src_address,
                dst_address=args.dst_address,
                protocol=args.protocol,
                src_port=args.src_port,
                dst_port=args.dst_port,
                comment=args.comment,
                disabled=args.disabled,
                position=args.position
            ):
                print(f"{Colors.GREEN}Đã thêm filter rule thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thêm filter rule.{Colors.ENDC}")
                
        elif args.command == 'add-forward':
            if firewall.add_port_forward(
                dst_port=args.dst_port,
                to_address=args.to_address,
                to_port=args.to_port,
                protocol=args.protocol,
                comment=args.comment,
                disabled=args.disabled
            ):
                print(f"{Colors.GREEN}Đã thêm port forward thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thêm port forward.{Colors.ENDC}")
                
        elif args.command == 'remove-rule':
            if firewall.remove_firewall_rule(args.type, args.id):
                print(f"{Colors.GREEN}Đã xóa {args.type} rule thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể xóa {args.type} rule.{Colors.ENDC}")
                
        elif args.command == 'toggle-rule':
            # Xác định trạng thái bật/tắt
            enabled = not args.disable if args.disable else args.enable
            
            if firewall.enable_disable_rule(args.type, args.id, enabled):
                status = "bật" if enabled else "tắt"
                print(f"{Colors.GREEN}Đã {status} {args.type} rule thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thay đổi trạng thái {args.type} rule.{Colors.ENDC}")
                
        elif args.command == 'add-address':
            if firewall.add_to_address_list(args.address, args.list, args.comment, args.timeout):
                print(f"{Colors.GREEN}Đã thêm địa chỉ {args.address} vào address list {args.list} thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thêm địa chỉ vào address list.{Colors.ENDC}")
                
        elif args.command == 'remove-address':
            if firewall.remove_from_address_list(args.address, args.list):
                list_text = f"address list {args.list}" if args.list else "tất cả address lists"
                print(f"{Colors.GREEN}Đã xóa địa chỉ {args.address} khỏi {list_text} thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể xóa địa chỉ khỏi address list.{Colors.ENDC}")
                
        elif args.command == 'basic-firewall':
            confirm = input("Cảnh báo: Lệnh này sẽ tạo các quy tắc firewall mới. Tiếp tục? (y/n): ")
            if confirm.lower() == 'y':
                if firewall.create_basic_firewall():
                    print(f"{Colors.GREEN}Đã tạo firewall cơ bản thành công.{Colors.ENDC}")
                else:
                    print(f"{Colors.RED}Không thể tạo firewall cơ bản.{Colors.ENDC}")
            else:
                print("Đã hủy lệnh.")
                
        elif args.command == 'basic-nat':
            if firewall.setup_basic_nat(args.interface):
                print(f"{Colors.GREEN}Đã thiết lập NAT cơ bản trên interface {args.interface} thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thiết lập NAT cơ bản.{Colors.ENDC}")
                
        else:
            # Nếu không có lệnh nào được chỉ định, hiển thị trợ giúp
            parser.print_help()
    
    finally:
        # Đảm bảo luôn ngắt kết nối
        firewall.disconnect()


if __name__ == "__main__":
    main()