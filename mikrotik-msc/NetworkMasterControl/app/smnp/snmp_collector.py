from pysnmp.hlapi import *
from app.utils.logger import logger

class SNMPMonitor:
    def __init__(self, community, snmp_version='3'):
        self.community = community
        self.snmp_version = snmp_version

    def get_snmp_data(self, target_ip, oid):
        error_indication, error_status, error_index, var_binds = next(
            getCmd(SnmpEngine(),
                   CommunityData(self.community),
                   UdpTransportTarget((target_ip, 161)),
                   ContextData(),
                   ObjectType(ObjectIdentity(oid))
        )

        if error_indication:
            logger.error(f"SNMP Error: {error_indication}")
            return None
        return var_binds

    def get_cpu_usage(self, target_ip):
        return self.get_snmp_data(target_ip, '1.3.6.1.2.1.25.3.3.1.2.1')