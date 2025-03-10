# File: scripts/auto_provision.py
from app.api.capsman_api import CapsManManager

def handle_new_ap(mac_address, ip):
    manager = CapsManManager()
    if mac_address.startswith("00:11:22"):
        manager.provision_ap(ip, profile="default")
