#!/usr/bin/env python3
from routeros_api import RouterOsApiPool
from app.utils.logger import logger
from app.utils.config_loader import load_config

config = load_config()

def register_capsman_ap(controller_ip: str, ap_ip: str):
    """Đăng ký AP mới vào CAPsMAN Controller"""
    try:
        # Kết nối tới CAPsMAN Controller
        api = RouterOsApiPool(
            controller_ip,
            username=config['capsman']['username'],
            password=config['capsman']['password'],
            port=443,
            use_ssl=True
        ).get_api()

        # Thêm AP vào CAPsMAN
        capsman = api.get_resource('/interface/wireless/cap')
        capsman.add(
            interface='wlan1',
            discovery_interfaces=config['capsman']['discovery_interface'],
            enabled='yes',
            name=ap_ip
        )

        logger.info(f"Đăng ký thành công AP {ap_ip} vào CAPsMAN")
        return True

    except Exception as e:
        logger.error(f"Lỗi đăng ký AP {ap_ip}: {str(e)}")
        return False

def discover_new_aps():
    """Tự động phát hiện AP chưa đăng ký"""
    # Triển khai logic quét mạng ở đây
    # Ví dụ: sử dụng ARP scan hoặc đọc từ database
    pass  

if __name__ == "__main__":
    # Ví dụ sử dụng - cần tích hợp với hệ thống phát hiện AP
    new_aps = discover_new_aps()
    for ap in new_aps:
        register_capsman_ap(
            controller_ip=config['capsman']['controller_ip'],
            ap_ip=ap['ip']
        )
