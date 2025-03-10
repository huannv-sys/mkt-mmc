#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quản lý Backup cấu hình trên thiết bị MikroTik
Script này tự động sao lưu và khôi phục cấu hình của thiết bị MikroTik
"""

import os
import sys
import time
import json
import logging
import argparse
import datetime
import hashlib
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
logger = logging.getLogger('mikrotik_backup')

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


class MikroTikBackupManager:
    """Lớp quản lý Backup cấu hình trên thiết bị MikroTik."""

    def __init__(self, host, username, password, backup_dir=None):
        """Khởi tạo với thông tin kết nối."""
        self.host = host
        self.username = username
        self.password = password
        self.connection = None
        self.api = None
        
        # Thư mục lưu backup
        if backup_dir:
            self.backup_dir = backup_dir
        else:
            self.backup_dir = os.path.join(os.getcwd(), 'backups')
            
        # Tạo thư mục nếu chưa tồn tại
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

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

    def create_backup(self, name=None, include_sensitive=False):
        """Tạo backup cấu hình và tải về."""
        if not self.api:
            return False
            
        try:
            # Tạo tên file dựa trên thông tin thiết bị và thời gian
            device_info = self.get_device_info()
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if name:
                backup_name = f"{name}_{timestamp}"
            elif device_info:
                backup_name = f"{device_info['hostname']}_{timestamp}"
            else:
                backup_name = f"mikrotik_{self.host}_{timestamp}"
            
            # Thực hiện lệnh backup
            system_backup = self.api.get_resource('/system/backup')
            
            # Tạo backup trên thiết bị
            backup_params = {
                "name": backup_name
            }
            
            if include_sensitive:
                backup_params["dont-encrypt"] = "yes"
            
            system_backup.call('save', backup_params)
            logger.info(f"Đã tạo backup trên thiết bị: {backup_name}")
            
            # Tải file về
            files = self.api.get_resource('/file')
            backup_files = files.get(type="backup")
            
            for file in backup_files:
                if file.get('name') == backup_name + '.backup':
                    # Tải file
                    self._download_file(file.get('name'))
                    logger.info(f"Đã tải backup về máy")
                    
                    # Xóa file trên thiết bị
                    files.remove(id=file.get('.id'))
                    logger.info(f"Đã xóa backup trên thiết bị")
                    
                    return True
                    
            logger.warning(f"Không tìm thấy file backup đã tạo")
            return False
        except Exception as e:
            logger.error(f"Lỗi khi tạo backup: {e}")
            return False

    def create_export(self, name=None, compact=False, include_sensitive=False):
        """Xuất cấu hình dạng text và lưu vào file."""
        if not self.api:
            return False
            
        try:
            # Tạo tên file dựa trên thông tin thiết bị và thời gian
            device_info = self.get_device_info()
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if name:
                export_name = f"{name}_{timestamp}"
            elif device_info:
                export_name = f"{device_info['hostname']}_{timestamp}"
            else:
                export_name = f"mikrotik_{self.host}_{timestamp}"
            
            # Thực hiện lệnh export
            system_export = self.api.get_resource('/export')
            
            # Tạo export trên thiết bị
            export_params = {
                "file": export_name
            }
            
            if compact:
                export_params["compact"] = "yes"
                
            if include_sensitive:
                export_params["show-sensitive"] = "yes"
            
            system_export.call('rsc', export_params)
            logger.info(f"Đã tạo export trên thiết bị: {export_name}")
            
            # Tải file về
            files = self.api.get_resource('/file')
            export_files = files.get()
            
            for file in export_files:
                if file.get('name') == export_name + '.rsc':
                    # Tải file
                    self._download_file(file.get('name'))
                    logger.info(f"Đã tải export về máy")
                    
                    # Xóa file trên thiết bị
                    files.remove(id=file.get('.id'))
                    logger.info(f"Đã xóa export trên thiết bị")
                    
                    return True
                    
            logger.warning(f"Không tìm thấy file export đã tạo")
            return False
        except Exception as e:
            logger.error(f"Lỗi khi tạo export: {e}")
            return False

    def _download_file(self, filename):
        """Tải file từ thiết bị về máy local."""
        if not self.api:
            return False
            
        try:
            # Lấy nội dung file
            fetch_resource = self.api.get_resource('/fetch')
            files = self.api.get_resource('/file')
            
            # Lấy kích thước file
            file_info = None
            for file in files.get():
                if file.get('name') == filename:
                    file_info = file
                    break
                    
            if not file_info:
                logger.error(f"Không tìm thấy file {filename} trên thiết bị")
                return False
                
            # Lấy đường dẫn file
            local_path = os.path.join(self.backup_dir, filename)
            
            # Tạo URL FTP
            ftp_url = f"ftp://{self.username}:{self.password}@{self.host}/{filename}"
            
            # Tải file bằng fetch (sử dụng mode=http để tải về máy local)
            fetch_resource.call('http', {
                "url": ftp_url,
                "dst-path": local_path
            })
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tải file: {e}")
            return False

    def list_backups(self):
        """Liệt kê các file backup đã lưu."""
        backups = []
        
        try:
            # Tìm file *.backup trong thư mục backup
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.backup'):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_size = os.path.getsize(file_path)
                    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    backups.append({
                        'name': filename,
                        'size': file_size,
                        'modified': file_mtime,
                        'path': file_path
                    })
                    
            # Sắp xếp theo thời gian mới nhất
            backups.sort(key=lambda x: x['modified'], reverse=True)
            return backups
        except Exception as e:
            logger.error(f"Lỗi khi liệt kê backups: {e}")
            return []

    def list_exports(self):
        """Liệt kê các file export đã lưu."""
        exports = []
        
        try:
            # Tìm file *.rsc trong thư mục backup
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.rsc'):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_size = os.path.getsize(file_path)
                    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    exports.append({
                        'name': filename,
                        'size': file_size,
                        'modified': file_mtime,
                        'path': file_path
                    })
                    
            # Sắp xếp theo thời gian mới nhất
            exports.sort(key=lambda x: x['modified'], reverse=True)
            return exports
        except Exception as e:
            logger.error(f"Lỗi khi liệt kê exports: {e}")
            return []

    def upload_backup(self, backup_file):
        """Tải file backup lên thiết bị."""
        if not self.api:
            return False
            
        try:
            # Kiểm tra file tồn tại
            if not os.path.exists(backup_file):
                logger.error(f"File {backup_file} không tồn tại")
                return False
                
            # Lấy tên file từ đường dẫn
            filename = os.path.basename(backup_file)
            
            # Tạo URL FTP
            ftp_url = f"ftp://{self.username}:{self.password}@{self.host}/{filename}"
            
            # Tải file lên
            fetch_resource = self.api.get_resource('/fetch')
            fetch_resource.call('send', {
                "url": ftp_url,
                "src-path": backup_file,
                "upload": "yes"
            })
            
            logger.info(f"Đã tải file {filename} lên thiết bị")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tải file lên thiết bị: {e}")
            return False

    def restore_backup(self, backup_file):
        """Khôi phục cấu hình từ file backup."""
        if not self.api:
            return False
            
        try:
            # Upload file nếu là đường dẫn local
            if os.path.exists(backup_file):
                filename = os.path.basename(backup_file)
                if not self.upload_backup(backup_file):
                    return False
            else:
                # Nếu là tên file, kiểm tra trên thiết bị
                filename = backup_file
            
            # Thực hiện lệnh restore
            system_backup = self.api.get_resource('/system/backup')
            system_backup.call('load', {
                "name": filename
            })
            
            logger.info(f"Đã gửi lệnh khôi phục từ file {filename}")
            logger.info(f"Thiết bị sẽ khởi động lại để hoàn tất khôi phục")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi khôi phục từ backup: {e}")
            return False

    def restore_export(self, export_file):
        """Khôi phục cấu hình từ file export."""
        if not self.api:
            return False
            
        try:
            # Kiểm tra file tồn tại
            if not os.path.exists(export_file):
                logger.error(f"File {export_file} không tồn tại")
                return False
                
            # Đọc nội dung file
            with open(export_file, 'r') as f:
                script = f.read()
                
            # Thực hiện từng lệnh
            system_script = self.api.get_resource('/system/script')
            script_name = f"restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Tạo script
            system_script.add(
                name=script_name,
                source=script
            )
            
            # Chạy script
            system_script.call('run', {
                'name': script_name
            })
            
            logger.info(f"Đã khôi phục cấu hình từ file {export_file}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi khôi phục từ export: {e}")
            return False

    def scheduled_backup(self, interval=86400, name=None, include_sensitive=False):
        """Thiết lập lịch tự động backup."""
        if not self.api:
            return False
            
        try:
            # Tạo tên mặc định nếu không có
            if not name:
                device_info = self.get_device_info()
                if device_info:
                    name = f"auto_backup_{device_info['hostname']}"
                else:
                    name = f"auto_backup_{self.host}"
            
            # Tạo script backup
            system_script = self.api.get_resource('/system/script')
            
            # Xóa script cũ nếu có
            scripts = system_script.get(name=name)
            for script in scripts:
                system_script.remove(id=script.get('.id'))
            
            # Tạo script mới
            backup_script = f"""
/system backup save name=(\$name . "-" . \[:pick [/system clock get date] 0 5] . \[:pick [/system clock get date] 6 10] . "-" . \[:pick [/system clock get time] 0 2] . \[:pick [/system clock get time] 3 5])
            """
            
            system_script.add(
                name=name,
                source=backup_script,
                comment="Auto backup script"
            )
            
            # Tạo scheduler
            system_scheduler = self.api.get_resource('/system/scheduler')
            
            # Xóa scheduler cũ nếu có
            schedulers = system_scheduler.get(name=name)
            for scheduler in schedulers:
                system_scheduler.remove(id=scheduler.get('.id'))
            
            # Tạo scheduler mới
            system_scheduler.add(
                name=name,
                interval=str(interval),
                on_event=f"/system script run {name}",
                comment="Auto backup scheduler"
            )
            
            logger.info(f"Đã thiết lập lịch tự động backup với interval {interval}s")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập lịch tự động backup: {e}")
            return False

    def disable_scheduled_backup(self, name=None):
        """Tắt lịch tự động backup."""
        if not self.api:
            return False
            
        try:
            # Tạo tên mặc định nếu không có
            if not name:
                device_info = self.get_device_info()
                if device_info:
                    name = f"auto_backup_{device_info['hostname']}"
                else:
                    name = f"auto_backup_{self.host}"
            
            # Xóa scheduler
            system_scheduler = self.api.get_resource('/system/scheduler')
            
            # Tìm và xóa scheduler
            schedulers = system_scheduler.get(name=name)
            for scheduler in schedulers:
                system_scheduler.remove(id=scheduler.get('.id'))
                
            # Xóa script
            system_script = self.api.get_resource('/system/script')
            
            # Tìm và xóa script
            scripts = system_script.get(name=name)
            for script in scripts:
                system_script.remove(id=script.get('.id'))
                
            logger.info(f"Đã tắt lịch tự động backup {name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tắt lịch tự động backup: {e}")
            return False

    def compare_exports(self, export_file1, export_file2):
        """So sánh hai file export và hiển thị sự khác biệt."""
        try:
            # Kiểm tra file tồn tại
            if not os.path.exists(export_file1):
                logger.error(f"File {export_file1} không tồn tại")
                return None
                
            if not os.path.exists(export_file2):
                logger.error(f"File {export_file2} không tồn tại")
                return None
                
            # Đọc nội dung file
            with open(export_file1, 'r') as f:
                content1 = f.readlines()
                
            with open(export_file2, 'r') as f:
                content2 = f.readlines()
                
            # Lọc bỏ các dòng comment và trống
            content1 = [line.strip() for line in content1 if line.strip() and not line.strip().startswith('#')]
            content2 = [line.strip() for line in content2 if line.strip() and not line.strip().startswith('#')]
            
            # So sánh từng dòng
            only_in_1 = [line for line in content1 if line not in content2]
            only_in_2 = [line for line in content2 if line not in content1]
            
            return {
                'file1': export_file1,
                'file2': export_file2,
                'only_in_1': only_in_1,
                'only_in_2': only_in_2,
                'difference_count': len(only_in_1) + len(only_in_2)
            }
        except Exception as e:
            logger.error(f"Lỗi khi so sánh file export: {e}")
            return None


def main():
    """Hàm chính để chạy công cụ backup."""
    # Load environment variables
    load_dotenv()
    
    # Lấy thông tin kết nối từ biến môi trường hoặc command line arguments
    parser = argparse.ArgumentParser(description='Công cụ backup cấu hình MikroTik')
    parser.add_argument('--host', default=os.getenv('MIKROTIK_HOST'), help='Địa chỉ IP của thiết bị MikroTik')
    parser.add_argument('--user', default=os.getenv('MIKROTIK_USER'), help='Tên đăng nhập')
    parser.add_argument('--password', default=os.getenv('MIKROTIK_PASSWORD'), help='Mật khẩu')
    parser.add_argument('--backup-dir', help='Thư mục lưu backup', default='backups')
    
    # Các lệnh
    subparsers = parser.add_subparsers(dest='command', help='Lệnh')
    
    # Lệnh backup
    backup_parser = subparsers.add_parser('backup', help='Tạo backup')
    backup_parser.add_argument('--name', help='Tên file backup (không bao gồm đuôi .backup)')
    backup_parser.add_argument('--sensitive', action='store_true', help='Bao gồm thông tin nhạy cảm')
    
    # Lệnh export
    export_parser = subparsers.add_parser('export', help='Xuất cấu hình')
    export_parser.add_argument('--name', help='Tên file export (không bao gồm đuôi .rsc)')
    export_parser.add_argument('--compact', action='store_true', help='Xuất dạng compact')
    export_parser.add_argument('--sensitive', action='store_true', help='Bao gồm thông tin nhạy cảm')
    
    # Lệnh list-backups
    list_backups_parser = subparsers.add_parser('list-backups', help='Liệt kê các file backup')
    
    # Lệnh list-exports
    list_exports_parser = subparsers.add_parser('list-exports', help='Liệt kê các file export')
    
    # Lệnh restore-backup
    restore_backup_parser = subparsers.add_parser('restore-backup', help='Khôi phục từ file backup')
    restore_backup_parser.add_argument('--file', required=True, help='Đường dẫn đến file backup')
    
    # Lệnh restore-export
    restore_export_parser = subparsers.add_parser('restore-export', help='Khôi phục từ file export')
    restore_export_parser.add_argument('--file', required=True, help='Đường dẫn đến file export')
    
    # Lệnh schedule
    schedule_parser = subparsers.add_parser('schedule', help='Thiết lập lịch tự động backup')
    schedule_parser.add_argument('--interval', type=int, default=86400, help='Khoảng thời gian (giây, mặc định: 86400 = 1 ngày)')
    schedule_parser.add_argument('--name', help='Tên task')
    schedule_parser.add_argument('--sensitive', action='store_true', help='Bao gồm thông tin nhạy cảm')
    
    # Lệnh disable-schedule
    disable_schedule_parser = subparsers.add_parser('disable-schedule', help='Tắt lịch tự động backup')
    disable_schedule_parser.add_argument('--name', help='Tên task')
    
    # Lệnh compare
    compare_parser = subparsers.add_parser('compare', help='So sánh hai file export')
    compare_parser.add_argument('--file1', required=True, help='File export thứ nhất')
    compare_parser.add_argument('--file2', required=True, help='File export thứ hai')
    
    args = parser.parse_args()
    
    # Kiểm tra thông tin kết nối
    if not args.command or (args.command not in ['list-backups', 'list-exports', 'compare'] and (not args.host or not args.user or not args.password)):
        print(f"{Colors.RED}Lỗi: Thiếu thông tin kết nối MikroTik.{Colors.ENDC}")
        print(f"{Colors.RED}Vui lòng cung cấp thông tin qua biến môi trường hoặc command line arguments.{Colors.ENDC}")
        parser.print_help()
        return
    
    # Khởi tạo đối tượng backup
    backup_manager = MikroTikBackupManager(args.host, args.user, args.password, args.backup_dir)
    
    # Xử lý các lệnh không cần kết nối trước
    if args.command == 'list-backups':
        backups = backup_manager.list_backups()
        if backups:
            print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH BACKUP FILES ==={Colors.ENDC}")
            for i, backup in enumerate(backups):
                size_str = f"{backup['size'] / 1024:.1f} KB" if backup['size'] < 1024 * 1024 else f"{backup['size'] / (1024 * 1024):.1f} MB"
                print(f"{i+1}. {backup['name']}")
                print(f"   Size: {size_str}")
                print(f"   Modified: {backup['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Path: {backup['path']}")
                print()
        else:
            print(f"{Colors.WARNING}Không có file backup nào.{Colors.ENDC}")
        return
        
    elif args.command == 'list-exports':
        exports = backup_manager.list_exports()
        if exports:
            print(f"{Colors.HEADER}{Colors.BOLD}=== DANH SÁCH EXPORT FILES ==={Colors.ENDC}")
            for i, export in enumerate(exports):
                size_str = f"{export['size'] / 1024:.1f} KB" if export['size'] < 1024 * 1024 else f"{export['size'] / (1024 * 1024):.1f} MB"
                print(f"{i+1}. {export['name']}")
                print(f"   Size: {size_str}")
                print(f"   Modified: {export['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Path: {export['path']}")
                print()
        else:
            print(f"{Colors.WARNING}Không có file export nào.{Colors.ENDC}")
        return
        
    elif args.command == 'compare':
        result = backup_manager.compare_exports(args.file1, args.file2)
        if result:
            print(f"{Colors.HEADER}{Colors.BOLD}=== SO SÁNH EXPORT FILES ==={Colors.ENDC}")
            print(f"File 1: {result['file1']}")
            print(f"File 2: {result['file2']}")
            print(f"Tổng số khác biệt: {result['difference_count']}")
            print()
            
            if result['only_in_1']:
                print(f"{Colors.BLUE}Chỉ có trong {os.path.basename(result['file1'])}:{Colors.ENDC}")
                for line in result['only_in_1']:
                    print(f"  + {line}")
                print()
                
            if result['only_in_2']:
                print(f"{Colors.GREEN}Chỉ có trong {os.path.basename(result['file2'])}:{Colors.ENDC}")
                for line in result['only_in_2']:
                    print(f"  + {line}")
        else:
            print(f"{Colors.RED}Không thể so sánh các file.{Colors.ENDC}")
        return
    
    # Kết nối tới thiết bị cho các lệnh khác
    api = backup_manager.connect()
    
    if not api and args.command not in ['list-backups', 'list-exports', 'compare']:
        print(f"{Colors.RED}Lỗi: Không thể kết nối đến MikroTik.{Colors.ENDC}")
        return
    
    try:
        # Xử lý các lệnh
        if args.command == 'backup':
            if backup_manager.create_backup(args.name, args.sensitive):
                print(f"{Colors.GREEN}Đã tạo backup thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể tạo backup.{Colors.ENDC}")
                
        elif args.command == 'export':
            if backup_manager.create_export(args.name, args.compact, args.sensitive):
                print(f"{Colors.GREEN}Đã xuất cấu hình thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể xuất cấu hình.{Colors.ENDC}")
                
        elif args.command == 'restore-backup':
            confirm = input(f"{Colors.WARNING}CẢNH BÁO: Khôi phục sẽ khởi động lại thiết bị. Tiếp tục? (y/n): {Colors.ENDC}")
            if confirm.lower() == 'y':
                if backup_manager.restore_backup(args.file):
                    print(f"{Colors.GREEN}Đã gửi lệnh khôi phục backup thành công.{Colors.ENDC}")
                    print(f"{Colors.GREEN}Thiết bị sẽ khởi động lại để hoàn tất khôi phục.{Colors.ENDC}")
                else:
                    print(f"{Colors.RED}Không thể khôi phục từ backup.{Colors.ENDC}")
            else:
                print("Đã hủy khôi phục.")
                
        elif args.command == 'restore-export':
            confirm = input(f"{Colors.WARNING}CẢNH BÁO: Khôi phục có thể làm thay đổi cấu hình. Tiếp tục? (y/n): {Colors.ENDC}")
            if confirm.lower() == 'y':
                if backup_manager.restore_export(args.file):
                    print(f"{Colors.GREEN}Đã khôi phục từ export thành công.{Colors.ENDC}")
                else:
                    print(f"{Colors.RED}Không thể khôi phục từ export.{Colors.ENDC}")
            else:
                print("Đã hủy khôi phục.")
                
        elif args.command == 'schedule':
            if backup_manager.scheduled_backup(args.interval, args.name, args.sensitive):
                print(f"{Colors.GREEN}Đã thiết lập lịch tự động backup thành công.{Colors.ENDC}")
                interval_str = f"{args.interval} giây"
                if args.interval == 86400:
                    interval_str = "1 ngày"
                elif args.interval == 3600:
                    interval_str = "1 giờ"
                elif args.interval == 604800:
                    interval_str = "1 tuần"
                print(f"{Colors.GREEN}Backup sẽ được thực hiện tự động mỗi {interval_str}.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thiết lập lịch tự động backup.{Colors.ENDC}")
                
        elif args.command == 'disable-schedule':
            if backup_manager.disable_scheduled_backup(args.name):
                print(f"{Colors.GREEN}Đã tắt lịch tự động backup thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể tắt lịch tự động backup.{Colors.ENDC}")
                
        else:
            # Nếu không có lệnh nào được chỉ định, hiển thị trợ giúp
            parser.print_help()
    
    finally:
        # Đảm bảo luôn ngắt kết nối
        if args.command not in ['list-backups', 'list-exports', 'compare']:
            backup_manager.disconnect()


if __name__ == "__main__":
    main()