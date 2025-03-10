#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quản lý CAPsMAN trên thiết bị MikroTik
Script này quản lý các Access Point thông qua CAPsMAN (Controlled Access Point Management)
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
logger = logging.getLogger('mikrotik_capsman')

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


class MikroTikCAPsMANManager:
    """Lớp quản lý CAPsMAN trên thiết bị MikroTik."""

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

    def get_device_info(self):
        """Lấy thông tin cơ bản về thiết bị."""
        if not self.api:
            return None
            
        try:
            identity = self.api.get_resource('/system/identity').get()[0]['name']
            resource = self.api.get_resource('/system/resource').get()[0]
            
            return {
                'hostname': identity,
                'model': resource.get('board-name', 'Unknown'),
                'version': resource.get('version', 'Unknown'),
                'uptime': resource.get('uptime', 'Unknown'),
                'cpu_load': resource.get('cpu-load', '0') + '%'
            }
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin thiết bị: {e}")
            return None

    def check_capsman_enabled(self):
        """Kiểm tra xem CAPsMAN có được bật trên thiết bị không."""
        if not self.api:
            return False
            
        try:
            # Kiểm tra xem CAPsMAN package có được cài đặt không
            packages = self.api.get_resource('/system/package').get()
            capsman_installed = any(pkg.get('name') == 'wireless' for pkg in packages)
            
            if not capsman_installed:
                return False
            
            # Kiểm tra xem CAPsMAN có được bật không
            capsman_enabled = False
            try:
                capsman_config = self.api.get_resource('/caps-man/manager').get()
                capsman_enabled = True
            except:
                # Nếu API path không tồn tại, CAPsMAN không được bật
                pass
                
            return capsman_enabled
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra CAPsMAN: {e}")
            return False

    def enable_capsman(self, enabled=True):
        """Bật hoặc tắt CAPsMAN trên thiết bị."""
        if not self.api:
            return False
            
        try:
            # Kiểm tra xem CAPsMAN package có được cài đặt không
            packages = self.api.get_resource('/system/package').get()
            capsman_installed = any(pkg.get('name') == 'wireless' for pkg in packages)
            
            if not capsman_installed:
                logger.error("Package wireless không được cài đặt trên thiết bị")
                return False
            
            # Kiểm tra trạng thái hiện tại
            capsman_enabled = self.check_capsman_enabled()
            
            # Nếu trạng thái hiện tại đã đúng như mong muốn
            if capsman_enabled == enabled:
                return True
                
            # Thay đổi trạng thái
            if enabled:
                # Bật CAPsMAN
                self.api.get_resource('/caps-man/manager').add(
                    enabled="yes",
                    upgrade_policy="suggest-same-version"
                )
                logger.info("Đã bật CAPsMAN")
            else:
                # Tắt CAPsMAN
                manager_resource = self.api.get_resource('/caps-man/manager')
                manager_entries = manager_resource.get()
                if manager_entries:
                    manager_resource.set(
                        id=manager_entries[0].get('id'),
                        enabled="no"
                    )
                logger.info("Đã tắt CAPsMAN")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thay đổi trạng thái CAPsMAN: {e}")
            return False

    def get_configuration_profiles(self):
        """Lấy danh sách các configuration profiles."""
        if not self.api:
            return []
            
        try:
            if not self.check_capsman_enabled():
                logger.warning("CAPsMAN không được bật trên thiết bị")
                return []
                
            profiles = self.api.get_resource('/caps-man/configuration').get()
            return profiles
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách configuration profiles: {e}")
            return []

    def add_configuration_profile(self, name, ssid, security="wpa2-psk", passphrase=None, datapath=None):
        """Thêm một configuration profile mới."""
        if not self.api:
            return False
            
        try:
            if not self.check_capsman_enabled():
                logger.warning("CAPsMAN không được bật trên thiết bị")
                return False
                
            config_resource = self.api.get_resource('/caps-man/configuration')
            
            # Params cơ bản
            params = {
                "name": name,
                "ssid": ssid,
                "mode": "ap",
                "country": "vietnam"
            }
            
            # Thêm security settings nếu được chỉ định
            if security == "wpa2-psk" and passphrase:
                params.update({
                    "security": security,
                    "encryption": "aes-ccm",
                    "passphrase": passphrase
                })
            elif security == "none":
                params.update({
                    "security": "none",
                })
                
            # Thêm datapath settings nếu được chỉ định
            if datapath:
                params.update({
                    "datapath": datapath
                })
                
            # Thêm configuration profile
            config_resource.add(**params)
            logger.info(f"Đã thêm configuration profile: {name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm configuration profile: {e}")
            return False

    def delete_configuration_profile(self, name):
        """Xóa một configuration profile."""
        if not self.api:
            return False
            
        try:
            if not self.check_capsman_enabled():
                logger.warning("CAPsMAN không được bật trên thiết bị")
                return False
                
            config_resource = self.api.get_resource('/caps-man/configuration')
            profiles = config_resource.get()
            
            for profile in profiles:
                if profile.get('name') == name:
                    config_resource.remove(id=profile.get('.id'))
                    logger.info(f"Đã xóa configuration profile: {name}")
                    return True
                    
            logger.warning(f"Không tìm thấy configuration profile: {name}")
            return False
        except Exception as e:
            logger.error(f"Lỗi khi xóa configuration profile: {e}")
            return False

    def get_access_points(self):
        """Lấy danh sách các Access Point đã đăng ký."""
        if not self.api:
            return []
            
        try:
            if not self.check_capsman_enabled():
                logger.warning("CAPsMAN không được bật trên thiết bị")
                return []
                
            aps = self.api.get_resource('/caps-man/registration-table').get()
            return aps
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách Access Points: {e}")
            return []

    def get_access_point_status(self, ap_mac):
        """Lấy thông tin chi tiết về một Access Point cụ thể."""
        if not self.api:
            return None
            
        try:
            if not self.check_capsman_enabled():
                logger.warning("CAPsMAN không được bật trên thiết bị")
                return None
                
            # Tìm AP trong registration table
            aps = self.api.get_resource('/caps-man/registration-table').get()
            ap_info = None
            
            for ap in aps:
                if ap.get('mac-address') == ap_mac:
                    ap_info = ap
                    break
            
            if not ap_info:
                logger.warning(f"Không tìm thấy Access Point với MAC: {ap_mac}")
                return None
                
            # Lấy thêm thông tin từ interface list
            try:
                interfaces = self.api.get_resource('/caps-man/interface').get()
                ap_interfaces = []
                
                for interface in interfaces:
                    if interface.get('master-interface') == ap_info.get('interface'):
                        ap_interfaces.append(interface)
                        
                ap_info['interfaces'] = ap_interfaces
            except:
                pass
                
            return ap_info
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin Access Point: {e}")
            return None

    def reboot_access_point(self, ap_mac):
        """Khởi động lại một Access Point."""
        if not self.api:
            return False
            
        try:
            if not self.check_capsman_enabled():
                logger.warning("CAPsMAN không được bật trên thiết bị")
                return False
                
            # Tìm AP trong registration table
            aps = self.api.get_resource('/caps-man/registration-table').get()
            ap_id = None
            
            for ap in aps:
                if ap.get('mac-address') == ap_mac:
                    ap_id = ap.get('.id')
                    break
            
            if not ap_id:
                logger.warning(f"Không tìm thấy Access Point với MAC: {ap_mac}")
                return False
                
            # Khởi động lại AP
            self.api.get_resource('/caps-man/remote-cap').call('reset', {'mac-address': ap_mac})
            logger.info(f"Đã gửi lệnh khởi động lại Access Point: {ap_mac}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi khởi động lại Access Point: {e}")
            return False

    def get_clients(self):
        """Lấy danh sách các client đang kết nối."""
        if not self.api:
            return []
            
        try:
            if not self.check_capsman_enabled():
                logger.warning("CAPsMAN không được bật trên thiết bị")
                return []
                
            clients = self.api.get_resource('/caps-man/registration-table').get()
            return clients
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách clients: {e}")
            return []

    def create_access_list(self, name, interfaces=None, action="accept", comment=None):
        """Tạo access list mới."""
        if not self.api:
            return False
            
        try:
            if not self.check_capsman_enabled():
                logger.warning("CAPsMAN không được bật trên thiết bị")
                return False
                
            acl_resource = self.api.get_resource('/caps-man/access-list')
            
            # Params cơ bản
            params = {
                "comment": comment or f"ACL: {name}"
            }
            
            # Thêm interfaces nếu được chỉ định
            if interfaces:
                if isinstance(interfaces, list):
                    interfaces_str = ",".join(interfaces)
                else:
                    interfaces_str = interfaces
                    
                params.update({
                    "interface": interfaces_str
                })
                
            # Thêm action
            params.update({
                "action": action
            })
                
            # Thêm access list
            acl_resource.add(**params)
            logger.info(f"Đã tạo access list: {name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tạo access list: {e}")
            return False

    def add_mac_to_access_list(self, mac_address, allow=True, comment=None):
        """Thêm MAC address vào access list."""
        if not self.api:
            return False
            
        try:
            if not self.check_capsman_enabled():
                logger.warning("CAPsMAN không được bật trên thiết bị")
                return False
                
            acl_resource = self.api.get_resource('/caps-man/access-list')
            
            # Params cơ bản
            params = {
                "mac-address": mac_address,
                "action": "accept" if allow else "reject",
                "comment": comment or f"MAC: {mac_address}"
            }
                
            # Thêm vào access list
            acl_resource.add(**params)
            logger.info(f"Đã thêm MAC address {mac_address} vào access list")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm MAC address vào access list: {e}")
            return False

    def remove_mac_from_access_list(self, mac_address):
        """Xóa MAC address khỏi access list."""
        if not self.api:
            return False
            
        try:
            if not self.check_capsman_enabled():
                logger.warning("CAPsMAN không được bật trên thiết bị")
                return False
                
            acl_resource = self.api.get_resource('/caps-man/access-list')
            acl_entries = acl_resource.get()
            
            for entry in acl_entries:
                if entry.get('mac-address') == mac_address:
                    acl_resource.remove(id=entry.get('.id'))
                    logger.info(f"Đã xóa MAC address {mac_address} khỏi access list")
                    return True
                    
            logger.warning(f"Không tìm thấy MAC address {mac_address} trong access list")
            return False
        except Exception as e:
            logger.error(f"Lỗi khi xóa MAC address khỏi access list: {e}")
            return False

    def get_access_list(self):
        """Lấy danh sách access list."""
        if not self.api:
            return []
            
        try:
            if not self.check_capsman_enabled():
                logger.warning("CAPsMAN không được bật trên thiết bị")
                return []
                
            acl_entries = self.api.get_resource('/caps-man/access-list').get()
            return acl_entries
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách access list: {e}")
            return []


def main():
    """Hàm chính để chạy công cụ quản lý CAPsMAN."""
    # Load environment variables
    load_dotenv()
    
    # Lấy thông tin kết nối từ biến môi trường hoặc command line arguments
    parser = argparse.ArgumentParser(description='Công cụ quản lý CAPsMAN trên MikroTik')
    parser.add_argument('--host', default=os.getenv('MIKROTIK_HOST'), help='Địa chỉ IP của thiết bị MikroTik')
    parser.add_argument('--user', default=os.getenv('MIKROTIK_USER'), help='Tên đăng nhập')
    parser.add_argument('--password', default=os.getenv('MIKROTIK_PASSWORD'), help='Mật khẩu')
    
    # Các lệnh
    subparsers = parser.add_subparsers(dest='command', help='Lệnh')
    
    # Lệnh check
    check_parser = subparsers.add_parser('check', help='Kiểm tra CAPsMAN')
    
    # Lệnh enable/disable
    enable_parser = subparsers.add_parser('enable', help='Bật CAPsMAN')
    disable_parser = subparsers.add_parser('disable', help='Tắt CAPsMAN')
    
    # Lệnh list profiles
    list_profiles_parser = subparsers.add_parser('list-profiles', help='Liệt kê configuration profiles')
    
    # Lệnh add profile
    add_profile_parser = subparsers.add_parser('add-profile', help='Thêm configuration profile')
    add_profile_parser.add_argument('--name', required=True, help='Tên profile')
    add_profile_parser.add_argument('--ssid', required=True, help='SSID')
    add_profile_parser.add_argument('--security', default='wpa2-psk', choices=['none', 'wpa2-psk'], help='Phương thức bảo mật')
    add_profile_parser.add_argument('--passphrase', help='Passphrase (cho WPA2-PSK)')
    
    # Lệnh delete profile
    delete_profile_parser = subparsers.add_parser('delete-profile', help='Xóa configuration profile')
    delete_profile_parser.add_argument('--name', required=True, help='Tên profile')
    
    # Lệnh list APs
    list_aps_parser = subparsers.add_parser('list-aps', help='Liệt kê Access Points')
    
    # Lệnh get AP status
    ap_status_parser = subparsers.add_parser('ap-status', help='Xem thông tin Access Point')
    ap_status_parser.add_argument('--mac', required=True, help='MAC address của AP')
    
    # Lệnh reboot AP
    reboot_ap_parser = subparsers.add_parser('reboot-ap', help='Khởi động lại Access Point')
    reboot_ap_parser.add_argument('--mac', required=True, help='MAC address của AP')
    
    # Lệnh list clients
    list_clients_parser = subparsers.add_parser('list-clients', help='Liệt kê clients')
    
    # Lệnh list access list
    list_acl_parser = subparsers.add_parser('list-acl', help='Liệt kê access list')
    
    # Lệnh add MAC to access list
    add_mac_parser = subparsers.add_parser('add-mac', help='Thêm MAC vào access list')
    add_mac_parser.add_argument('--mac', required=True, help='MAC address')
    add_mac_parser.add_argument('--allow', action='store_true', default=True, help='Cho phép (mặc định)')
    add_mac_parser.add_argument('--deny', action='store_true', help='Từ chối')
    add_mac_parser.add_argument('--comment', help='Ghi chú')
    
    # Lệnh remove MAC from access list
    remove_mac_parser = subparsers.add_parser('remove-mac', help='Xóa MAC khỏi access list')
    remove_mac_parser.add_argument('--mac', required=True, help='MAC address')
    
    args = parser.parse_args()
    
    # Kiểm tra thông tin kết nối
    if not args.host or not args.user or not args.password:
        print(f"{Colors.RED}Lỗi: Thiếu thông tin kết nối MikroTik.{Colors.ENDC}")
        print(f"{Colors.RED}Vui lòng cung cấp thông tin qua biến môi trường hoặc command line arguments.{Colors.ENDC}")
        parser.print_help()
        return
    
    # Khởi tạo đối tượng quản lý CAPsMAN
    capsman = MikroTikCAPsMANManager(args.host, args.user, args.password)
    api = capsman.connect()
    
    if not api:
        print(f"{Colors.RED}Lỗi: Không thể kết nối đến MikroTik.{Colors.ENDC}")
        return
    
    try:
        # Xử lý các lệnh
        if args.command == 'check':
            enabled = capsman.check_capsman_enabled()
            if enabled:
                print(f"{Colors.GREEN}CAPsMAN đang được bật trên thiết bị.{Colors.ENDC}")
            else:
                print(f"{Colors.WARNING}CAPsMAN đang bị tắt trên thiết bị.{Colors.ENDC}")
                
        elif args.command == 'enable':
            if capsman.enable_capsman(True):
                print(f"{Colors.GREEN}Đã bật CAPsMAN thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể bật CAPsMAN.{Colors.ENDC}")
                
        elif args.command == 'disable':
            if capsman.enable_capsman(False):
                print(f"{Colors.GREEN}Đã tắt CAPsMAN thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể tắt CAPsMAN.{Colors.ENDC}")
                
        elif args.command == 'list-profiles':
            profiles = capsman.get_configuration_profiles()
            if profiles:
                print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH CONFIGURATION PROFILES ==={Colors.ENDC}")
                for i, profile in enumerate(profiles):
                    print(f"{i+1}. {profile.get('name')}")
                    print(f"   SSID: {profile.get('ssid')}")
                    print(f"   Security: {profile.get('security', 'none')}")
                    print(f"   Mode: {profile.get('mode', 'ap')}")
                    print()
            else:
                print(f"{Colors.WARNING}Không có configuration profile nào.{Colors.ENDC}")
                
        elif args.command == 'add-profile':
            if capsman.add_configuration_profile(
                args.name, 
                args.ssid, 
                args.security, 
                args.passphrase
            ):
                print(f"{Colors.GREEN}Đã thêm configuration profile {args.name} thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thêm configuration profile.{Colors.ENDC}")
                
        elif args.command == 'delete-profile':
            if capsman.delete_configuration_profile(args.name):
                print(f"{Colors.GREEN}Đã xóa configuration profile {args.name} thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể xóa configuration profile.{Colors.ENDC}")
                
        elif args.command == 'list-aps':
            aps = capsman.get_access_points()
            if aps:
                print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH ACCESS POINTS ==={Colors.ENDC}")
                for i, ap in enumerate(aps):
                    print(f"{i+1}. {ap.get('name', ap.get('mac-address', 'Unknown'))}")
                    print(f"   MAC: {ap.get('mac-address')}")
                    print(f"   State: {ap.get('state', 'Unknown')}")
                    print(f"   Interface: {ap.get('interface', 'Unknown')}")
                    print()
            else:
                print(f"{Colors.WARNING}Không có Access Point nào đăng ký.{Colors.ENDC}")
                
        elif args.command == 'ap-status':
            ap_info = capsman.get_access_point_status(args.mac)
            if ap_info:
                print(f"{Colors.HEADER}{Colors.BOLD}=== THÔNG TIN ACCESS POINT ==={Colors.ENDC}")
                print(f"Tên: {ap_info.get('name', 'Unknown')}")
                print(f"MAC: {ap_info.get('mac-address')}")
                print(f"State: {ap_info.get('state', 'Unknown')}")
                print(f"Interface: {ap_info.get('interface', 'Unknown')}")
                print(f"Model: {ap_info.get('board', 'Unknown')}")
                print(f"Version: {ap_info.get('version', 'Unknown')}")
                print(f"Radio: {ap_info.get('radio-name', 'Unknown')}")
                
                if 'interfaces' in ap_info and ap_info['interfaces']:
                    print(f"\n{Colors.BOLD}Virtual Interfaces:{Colors.ENDC}")
                    for intf in ap_info['interfaces']:
                        print(f"  - {intf.get('name')}: {intf.get('configuration')}")
            else:
                print(f"{Colors.WARNING}Không tìm thấy Access Point với MAC: {args.mac}{Colors.ENDC}")
                
        elif args.command == 'reboot-ap':
            if capsman.reboot_access_point(args.mac):
                print(f"{Colors.GREEN}Đã gửi lệnh khởi động lại Access Point: {args.mac}{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể khởi động lại Access Point.{Colors.ENDC}")
                
        elif args.command == 'list-clients':
            clients = capsman.get_clients()
            if clients:
                print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH CLIENTS ==={Colors.ENDC}")
                for i, client in enumerate(clients):
                    print(f"{i+1}. {client.get('mac-address')}")
                    print(f"   SSID: {client.get('ssid', 'Unknown')}")
                    print(f"   Signal: {client.get('signal-strength', 'Unknown')}")
                    print(f"   Interface: {client.get('interface', 'Unknown')}")
                    print(f"   TX/RX Rate: {client.get('tx-rate', '0')} / {client.get('rx-rate', '0')}")
                    print()
            else:
                print(f"{Colors.WARNING}Không có client nào đang kết nối.{Colors.ENDC}")
                
        elif args.command == 'list-acl':
            acl_entries = capsman.get_access_list()
            if acl_entries:
                print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH ACCESS LIST ==={Colors.ENDC}")
                for i, entry in enumerate(acl_entries):
                    print(f"{i+1}. MAC: {entry.get('mac-address', 'Any')}")
                    print(f"   Action: {entry.get('action', 'Accept')}")
                    if entry.get('interface'):
                        print(f"   Interface: {entry.get('interface')}")
                    if entry.get('comment'):
                        print(f"   Comment: {entry.get('comment')}")
                    print()
            else:
                print(f"{Colors.WARNING}Không có entry nào trong access list.{Colors.ENDC}")
                
        elif args.command == 'add-mac':
            allow = not args.deny if args.deny else args.allow
            if capsman.add_mac_to_access_list(args.mac, allow, args.comment):
                action = "cho phép" if allow else "từ chối"
                print(f"{Colors.GREEN}Đã thêm MAC address {args.mac} vào access list với action {action}.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thêm MAC address vào access list.{Colors.ENDC}")
                
        elif args.command == 'remove-mac':
            if capsman.remove_mac_from_access_list(args.mac):
                print(f"{Colors.GREEN}Đã xóa MAC address {args.mac} khỏi access list.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể xóa MAC address khỏi access list.{Colors.ENDC}")
                
        else:
            # Nếu không có lệnh nào được chỉ định, hiển thị trợ giúp
            parser.print_help()
    
    finally:
        # Đảm bảo luôn ngắt kết nối
        capsman.disconnect()


if __name__ == "__main__":
    main()