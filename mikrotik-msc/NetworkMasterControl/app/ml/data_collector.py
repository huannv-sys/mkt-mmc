# File: app/ml/data_collector.py
from app.snmp.snmp_collector import SNMPMonitor

def collect_training_data():
    snmp = SNMPMonitor()
    data = []
    for device in config['devices']:
        data.append({
            'cpu': snmp.get_cpu(device['ip']),
            'memory': snmp.get_memory(device['ip'])
        })
    return data
