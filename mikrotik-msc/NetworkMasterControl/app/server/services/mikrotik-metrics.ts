import * as promClient from 'prom-client';
import { mikrotikClient } from './mikrotik-client';

// Initialize metrics
const mikrotikTraffic = new promClient.Gauge({
  name: 'mikrotik_interface_traffic_bytes',
  help: 'MikroTik interface traffic in bytes',
  labelNames: ['interface', 'direction']
});

const mikrotikClientCount = new promClient.Gauge({
  name: 'mikrotik_wireless_clients',
  help: 'Number of wireless clients connected',
  labelNames: ['interface']
});

const mikrotikSystemResources = new promClient.Gauge({
  name: 'mikrotik_system_resources',
  help: 'System resource usage',
  labelNames: ['resource']
});

export async function updateMetrics() {
  try {
    // Get interfaces data
    const interfaces = await mikrotikClient.getInterfaces();
    interfaces.forEach((iface: any) => {
      mikrotikTraffic.set(
        { interface: iface.name, direction: 'tx' }, 
        Number(iface['tx-byte'] || 0)
      );
      mikrotikTraffic.set(
        { interface: iface.name, direction: 'rx' }, 
        Number(iface['rx-byte'] || 0)
      );
    });

    // Get wireless clients
    const wirelessClients = await mikrotikClient.getWirelessClients();
    const clientsByInterface = wirelessClients.reduce((acc: any, client: any) => {
      acc[client.interface] = (acc[client.interface] || 0) + 1;
      return acc;
    }, {});

    Object.entries(clientsByInterface).forEach(([iface, count]) => {
      mikrotikClientCount.set({ interface: iface }, Number(count));
    });

    // Get system resources
    const [resources] = await mikrotikClient.getSystemResources();
    if (resources) {
      mikrotikSystemResources.set({ resource: 'cpu-load' }, Number(resources['cpu-load']));
      mikrotikSystemResources.set(
        { resource: 'memory-usage' },
        (Number(resources['total-memory'] - resources['free-memory']) / Number(resources['total-memory'])) * 100
      );
    }
  } catch (error) {
    console.error('Error updating MikroTik metrics:', error);
  }
}

// Register metrics with the default registry
promClient.register.registerMetric(mikrotikTraffic);
promClient.register.registerMetric(mikrotikClientCount);
promClient.register.registerMetric(mikrotikSystemResources);
