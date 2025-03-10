from librouteros import connect
from app.config import settings

class MikroTikService:
    @staticmethod
    async def get_device_interfaces(device_ip: str):
        try:
            conn = connect(
                host=device_ip,
                username=settings.MIKROTIK_USER,
                password=settings.MIKROTIK_PASS,
                port=443,
                ssl=True
            )
            interfaces = conn(cmd='/interface/print')
            return list(interfaces)
        except Exception as e:
            raise RuntimeError(f"MikroTik API Error: {e}")
