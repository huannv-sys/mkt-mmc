#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quản lý nhiều site (thiết bị MikroTik)
Script này giúp quản lý nhiều thiết bị MikroTik từ một giao diện duy nhất
"""

import os
import sys
import json
import time
import logging
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('mikrotik_site_manager')

# Import các module quản lý nếu có
try:
    from mikrotik_web_monitor import MikroTikMonitor
    from mikrotik_client_monitor import MikroTikClientMonitor
    from mikrotik_firewall_manager import MikroTikFirewallManager
    from mikrotik_capsman_manager import MikroTikCAPsMANManager
    from mikrotik_backup_manager import MikroTikBackupManager
except ImportError as e:
    logger.warning(f"Không thể import một số module: {e}")


class Site:
    """Lớp đại diện cho một site (thiết bị MikroTik)."""
    
    def __init__(self, name, host, username, password, description=None):
        """Khởi tạo site với thông tin kết nối."""
        self.name = name
        self.host = host
        self.username = username
        self.password = password
        self.description = description or f"Site {name}"
        self.location = None
        self.contact = None
        self.tags = []
        self.last_seen = None
        self.status = "offline"
        
        # Các module quản lý
        self.monitor = None
        self.client_monitor = None
        self.firewall_manager = None
        self.capsman_manager = None
        self.backup_manager = None
        
        self.lock = threading.Lock()
        self.connection_thread = None
        self._connected = False
        
    def connect(self):
        """Kết nối đến site."""
        # Khởi tạo monitor chính
        if 'MikroTikMonitor' in globals():
            self.monitor = MikroTikMonitor(self.host, self.username, self.password)
            api = self.monitor.connect()
            if api:
                self._connected = True
                self.status = "online"
                self.last_seen = datetime.now()
                self.monitor.start_monitoring(interval=2)
            else:
                self._connected = False
                self.status = "error"
                return False
        else:
            logger.warning("Module MikroTikMonitor không khả dụng")
            return False
            
        # Khởi tạo các module khác nếu có
        if self._connected:
            try:
                if 'MikroTikClientMonitor' in globals():
                    self.client_monitor = MikroTikClientMonitor(self.host, self.username, self.password)
                    self.client_monitor.connect()
                
                if 'MikroTikFirewallManager' in globals():
                    self.firewall_manager = MikroTikFirewallManager(self.host, self.username, self.password)
                    self.firewall_manager.connect()
                
                if 'MikroTikCAPsMANManager' in globals():
                    self.capsman_manager = MikroTikCAPsMANManager(self.host, self.username, self.password)
                    self.capsman_manager.connect()
                
                if 'MikroTikBackupManager' in globals():
                    self.backup_manager = MikroTikBackupManager(self.host, self.username, self.password)
                    self.backup_manager.connect()
                    
                logger.info(f"Đã kết nối đến site {self.name} ({self.host})")
                return True
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo các module cho site {self.name}: {e}")
                return False
        else:
            return False
            
    def disconnect(self):
        """Ngắt kết nối khỏi site."""
        try:
            if self.monitor:
                self.monitor.stop_monitoring()
                self.monitor.disconnect()
                
            if self.client_monitor:
                self.client_monitor.disconnect()
                
            if self.firewall_manager:
                self.firewall_manager.disconnect()
                
            if self.capsman_manager:
                self.capsman_manager.disconnect()
                
            if self.backup_manager:
                self.backup_manager.disconnect()
                
            self._connected = False
            self.status = "offline"
            logger.info(f"Đã ngắt kết nối khỏi site {self.name} ({self.host})")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi ngắt kết nối khỏi site {self.name}: {e}")
            return False
            
    def is_connected(self):
        """Kiểm tra xem site có đang kết nối không."""
        return self._connected
        
    def get_info(self):
        """Lấy thông tin cơ bản về site."""
        result = {
            "name": self.name,
            "host": self.host,
            "description": self.description,
            "location": self.location,
            "contact": self.contact,
            "tags": self.tags,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "status": self.status
        }
        
        # Thêm thông tin thiết bị từ monitor nếu có
        if self.monitor and self._connected:
            result["device_info"] = self.monitor.device_info
            
        return result


class SiteManager:
    """Lớp quản lý nhiều site MikroTik."""
    
    def __init__(self, config_file=None):
        """Khởi tạo với file cấu hình các site."""
        self.sites = {}  # name -> Site object
        self.active_site = None
        self.config_file = config_file or "sites.json"
        
        # Tạo file cấu hình mặc định nếu chưa có
        if not os.path.exists(self.config_file):
            self._create_default_config()
        
        # Load cấu hình site
        self.load_sites()
    
    def _create_default_config(self):
        """Tạo file cấu hình mặc định."""
        # Lấy thông tin từ env mặc định
        host = os.getenv('MIKROTIK_HOST', '')
        username = os.getenv('MIKROTIK_USER', '')
        password = os.getenv('MIKROTIK_PASSWORD', '')
        
        default_config = {
            "sites": [
                {
                    "name": "Default",
                    "host": host,
                    "username": username,
                    "password": password,
                    "description": "Site mặc định",
                    "location": "",
                    "contact": "",
                    "tags": ["default"]
                }
            ]
        }
        
        # Ghi file cấu hình
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
            
        logger.info(f"Đã tạo file cấu hình mặc định: {self.config_file}")
    
    def load_sites(self):
        """Load cấu hình các site từ file."""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                
            # Xóa các site hiện tại nếu đang kết nối
            for site in self.sites.values():
                if site.is_connected():
                    site.disconnect()
            
            self.sites = {}
            
            # Khởi tạo các site từ cấu hình
            for site_config in config.get("sites", []):
                name = site_config.get("name")
                host = site_config.get("host")
                username = site_config.get("username")
                password = site_config.get("password")
                
                if name and host and username and password:
                    site = Site(name, host, username, password)
                    site.description = site_config.get("description", f"Site {name}")
                    site.location = site_config.get("location")
                    site.contact = site_config.get("contact")
                    site.tags = site_config.get("tags", [])
                    
                    self.sites[name] = site
                    
            logger.info(f"Đã load {len(self.sites)} site từ cấu hình")
            
            # Nếu chỉ có một site, đặt làm active site
            if len(self.sites) == 1:
                self.active_site = list(self.sites.keys())[0]
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi load cấu hình site: {e}")
            return False
    
    def save_sites(self):
        """Lưu cấu hình các site vào file."""
        try:
            config = {"sites": []}
            
            for name, site in self.sites.items():
                site_config = {
                    "name": site.name,
                    "host": site.host,
                    "username": site.username,
                    "password": site.password,
                    "description": site.description,
                    "location": site.location,
                    "contact": site.contact,
                    "tags": site.tags
                }
                
                config["sites"].append(site_config)
                
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
            logger.info(f"Đã lưu {len(self.sites)} site vào cấu hình")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình site: {e}")
            return False
    
    def add_site(self, name, host, username, password, description=None, connect=False):
        """Thêm một site mới."""
        if name in self.sites:
            logger.warning(f"Site {name} đã tồn tại")
            return False
            
        site = Site(name, host, username, password, description)
        self.sites[name] = site
        
        # Kết nối đến site nếu yêu cầu
        if connect:
            site.connect()
            
        # Lưu cấu hình
        self.save_sites()
        
        logger.info(f"Đã thêm site {name} ({host})")
        return True
    
    def remove_site(self, name):
        """Xóa một site."""
        if name not in self.sites:
            logger.warning(f"Site {name} không tồn tại")
            return False
            
        # Ngắt kết nối nếu đang kết nối
        site = self.sites[name]
        if site.is_connected():
            site.disconnect()
            
        # Xóa site
        del self.sites[name]
        
        # Cập nhật active site nếu cần
        if self.active_site == name:
            if self.sites:
                self.active_site = list(self.sites.keys())[0]
            else:
                self.active_site = None
                
        # Lưu cấu hình
        self.save_sites()
        
        logger.info(f"Đã xóa site {name}")
        return True
    
    def connect_site(self, name):
        """Kết nối đến một site cụ thể."""
        if name not in self.sites:
            logger.warning(f"Site {name} không tồn tại")
            return False
            
        site = self.sites[name]
        result = site.connect()
        
        if result:
            self.active_site = name
            logger.info(f"Đã kết nối đến site {name}")
        
        return result
    
    def disconnect_site(self, name):
        """Ngắt kết nối khỏi một site cụ thể."""
        if name not in self.sites:
            logger.warning(f"Site {name} không tồn tại")
            return False
            
        site = self.sites[name]
        result = site.disconnect()
        
        if result and self.active_site == name:
            self.active_site = None
            
        return result
    
    def get_sites(self):
        """Lấy danh sách tất cả các site."""
        result = []
        
        for name, site in self.sites.items():
            info = site.get_info()
            info["active"] = (name == self.active_site)
            result.append(info)
            
        return result
    
    def get_site(self, name):
        """Lấy thông tin về một site cụ thể."""
        if name not in self.sites:
            return None
            
        return self.sites[name]
    
    def get_active_site(self):
        """Lấy site đang active."""
        if not self.active_site or self.active_site not in self.sites:
            return None
            
        return self.sites[self.active_site]
    
    def connect_all(self):
        """Kết nối đến tất cả các site."""
        for name, site in self.sites.items():
            try:
                site.connect()
            except Exception as e:
                logger.error(f"Lỗi khi kết nối đến site {name}: {e}")
                
        # Đặt active site là site đầu tiên đã kết nối thành công
        for name, site in self.sites.items():
            if site.is_connected():
                self.active_site = name
                break
                
        return True
    
    def disconnect_all(self):
        """Ngắt kết nối khỏi tất cả các site."""
        for name, site in self.sites.items():
            try:
                site.disconnect()
            except Exception as e:
                logger.error(f"Lỗi khi ngắt kết nối khỏi site {name}: {e}")
                
        self.active_site = None
        return True


def main():
    """Hàm chính để chạy quản lý site."""
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='MikroTik Site Manager')
    
    # Các tham số cơ bản
    parser.add_argument('--config', type=str, default='sites.json', help='File cấu hình site (mặc định: sites.json)')
    
    # Các lệnh
    subparsers = parser.add_subparsers(dest='command', help='Lệnh')
    
    # Lệnh list sites
    list_parser = subparsers.add_parser('list', help='Liệt kê sites')
    
    # Lệnh add site
    add_parser = subparsers.add_parser('add', help='Thêm site mới')
    add_parser.add_argument('--name', required=True, help='Tên site')
    add_parser.add_argument('--host', required=True, help='Địa chỉ IP của thiết bị')
    add_parser.add_argument('--username', required=True, help='Tên đăng nhập')
    add_parser.add_argument('--password', required=True, help='Mật khẩu')
    add_parser.add_argument('--description', help='Mô tả site')
    add_parser.add_argument('--connect', action='store_true', help='Kết nối đến site sau khi thêm')
    
    # Lệnh remove site
    remove_parser = subparsers.add_parser('remove', help='Xóa site')
    remove_parser.add_argument('--name', required=True, help='Tên site')
    
    # Lệnh connect site
    connect_parser = subparsers.add_parser('connect', help='Kết nối đến site')
    connect_parser.add_argument('--name', required=True, help='Tên site')
    
    # Lệnh disconnect site
    disconnect_parser = subparsers.add_parser('disconnect', help='Ngắt kết nối khỏi site')
    disconnect_parser.add_argument('--name', required=True, help='Tên site')
    
    # Lệnh connect all
    connect_all_parser = subparsers.add_parser('connect-all', help='Kết nối đến tất cả các site')
    
    # Lệnh disconnect all
    disconnect_all_parser = subparsers.add_parser('disconnect-all', help='Ngắt kết nối khỏi tất cả các site')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Khởi tạo site manager
    site_manager = SiteManager(args.config)
    
    # Xử lý các lệnh
    if args.command == 'list':
        sites = site_manager.get_sites()
        print(f"Danh sách {len(sites)} site:")
        for i, site in enumerate(sites):
            active = " (active)" if site.get('active') else ""
            status = site.get('status', 'offline')
            status_color = '\033[92m' if status == 'online' else '\033[91m'
            print(f"{i+1}. \033[94m{site['name']}\033[0m - {site['host']} - {status_color}{status}\033[0m{active}")
            if site.get('description'):
                print(f"   Mô tả: {site['description']}")
            if site.get('device_info'):
                device = site['device_info']
                print(f"   Thiết bị: {device.get('hostname', 'Unknown')} ({device.get('model', 'Unknown')})")
                print(f"   RouterOS: {device.get('ros_version', 'Unknown')}")
            print("")
    
    elif args.command == 'add':
        if site_manager.add_site(args.name, args.host, args.username, args.password, args.description, args.connect):
            print(f"Đã thêm site {args.name} thành công")
        else:
            print(f"Không thể thêm site {args.name}")
    
    elif args.command == 'remove':
        if site_manager.remove_site(args.name):
            print(f"Đã xóa site {args.name} thành công")
        else:
            print(f"Không thể xóa site {args.name}")
    
    elif args.command == 'connect':
        if site_manager.connect_site(args.name):
            print(f"Đã kết nối đến site {args.name} thành công")
        else:
            print(f"Không thể kết nối đến site {args.name}")
    
    elif args.command == 'disconnect':
        if site_manager.disconnect_site(args.name):
            print(f"Đã ngắt kết nối khỏi site {args.name} thành công")
        else:
            print(f"Không thể ngắt kết nối khỏi site {args.name}")
    
    elif args.command == 'connect-all':
        site_manager.connect_all()
        print("Đã kết nối đến tất cả các site")
    
    elif args.command == 'disconnect-all':
        site_manager.disconnect_all()
        print("Đã ngắt kết nối khỏi tất cả các site")
    
    else:
        # Nếu không có lệnh nào được chỉ định, hiển thị trợ giúp
        parser.print_help()


if __name__ == "__main__":
    import argparse
    main()