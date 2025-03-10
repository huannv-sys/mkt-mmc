#!/usr/bin/env python3
import os
import time
from datetime import datetime
from routeros_api import RouterOsApiPool
from app.utils.logger import logger
from app.utils.config_loader import load_config

config = load_config()

def mikrotik_backup(device_ip: str, user: str, password: str):
    """Backup cấu hình MikroTik và tải về server"""
    try:
        # Kết nối API
        api = RouterOsApiPool(
            device_ip,
            username=user,
            password=password,
            port=443,
            use_ssl=True
        ).get_api()

        # Tạo tên file backup
        backup_name = f"backup_{device_ip}_{datetime.now().strftime('%Y%m%d_%H%M')}"

        # Tạo backup
        api.get_binary_resource('/').call(
            'system/backup/save',
            {'name': backup_name}
        )

        # Tải file backup về
        backup_file = api.get_binary_resource('/').call(
            'file/get',
            {'name': f'{backup_name}.backup'}
        )[0]['contents']

        # Lưu vào thư mục backups
        backup_dir = config['backup']['directory']
        os.makedirs(backup_dir, exist_ok=True)

        with open(f"{backup_dir}/{backup_name}.backup", 'wb') as f:
            f.write(backup_file)

        logger.info(f"Backup thành công cho {device_ip}")
        return True

    except Exception as e:
        logger.error(f"Backup thất bại {device_ip}: {str(e)}")
        return False

if __name__ == "__main__":
    # Lấy danh sách thiết bị từ config
    for device in config['devices']:
        mikrotik_backup(
            device['ip'],
            device['username'],
            device['password']
        )
        time.sleep(1)  # Giãn cách giữa các thiết bị
        # Trong scripts/backup_configs.py
old_config = get_previous_config(device_ip)
changes = compare_config_versions(old_config, new_config)
if changes:
    send_alert(f"Cấu hình {device_ip} thay đổi: {changes}")
