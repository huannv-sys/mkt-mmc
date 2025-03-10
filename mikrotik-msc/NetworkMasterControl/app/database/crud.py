# File: app/database/crud.py
from difflib import unified_diff

def save_config_version(device_ip, config_text):
    # Lưu vào database với timestamp
    ...

def compare_config_versions(old_config, new_config):
    return list(unified_diff(old_config.splitlines(), new_config.splitlines()))
