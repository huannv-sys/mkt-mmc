# File: app/utils/network_scanner.py
import nmap

class NetworkScanner:
    def __init__(self, target_subnet="10.0.0.0/24"):
        self.subnet = target_subnet
        self.nm = nmap.PortScanner()

    def scan_mikrotik_devices(self):
        self.nm.scan(hosts=self.subnet, arguments='-p 8728 --open')
        devices = []
        for host in self.nm.all_hosts():
            if self.nm[host].has_tcp(8728):
                devices.append({"ip": host, "status": "discovered"})
        return devices
