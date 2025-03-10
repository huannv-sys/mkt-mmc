from routeros_api import RouterOsApiPool
from contextlib import contextmanager
from app.utils.logger import logger
from app.utils.config_loader import config

class MikroTikManager:
    def __init__(self, device_ip):
        self.device_ip = device_ip
        self.credentials = config['devices'][device_ip]

    @contextmanager
    def _connect(self):
        connection = None
        try:
            connection = RouterOsApiPool(
                host=self.device_ip,
                username=self.credentials['username'],
                password=self.credentials['password'],
                port=443,
                plaintext_login=False
            ).get_api()
            yield connection
        except Exception as e:
            logger.error(f"Connection failed to {self.device_ip}: {str(e)}")
            raise
        finally:
            if connection:
                connection.disconnect()

    def get_system_health(self):
        with self._connect() as conn:
            return conn.get_resource('/system/resource').get()

    def apply_config(self, config_commands):
        with self._connect() as conn:
            for cmd in config_commands:
                conn.get_binary_resource('/').call(cmd)
            logger.info(f"Applied {len(config_commands)} commands to {self.device_ip}")
