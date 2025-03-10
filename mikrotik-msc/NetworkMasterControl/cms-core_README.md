# CMS Core

Đây là hệ thống giám sát cho các thiết bị MikroTik, bao gồm các thành phần chính như API, SNMP, VPN và các tiện ích hỗ trợ khác.

## Cấu trúc thư mục

```plaintext
cms-core/
├── app/
│   ├── api/
│   │   ├── mikrotik_api.py
│   │   └── capsman_api.py
│   ├── snmp/
│   │   ├── snmp_collector.py
│   │   └── alerts.py
│   ├── vpn/
│   │   ├── ipsec_manager.py
│   │   └── openvpn_manager.py
│   ├── database/
│   │   ├── models.py
│   │   └── migrations/
│   ├── auth/
│   │   ├── rbac.py
│   │   └── jwt_handler.py
│   └── utils/
│       ├── logger.py
│       └── config_loader.py
├── config/
│   ├── settings.yaml
│   └── vpn/
├── scripts/
│   ├── backup_configs.py
│   └── capsman_provision.py
├── web/
│   ├── frontend/
│   └── backend/
├── requirements.txt
├── docker-compose.yaml
└── README.md