import * as RouterOS from 'node-routeros';
import type { MikrotikDevice, MikrotikStats } from '@shared/schema';

export class MikrotikService {
  private connections: Map<number, RouterOS.RouterOSAPI> = new Map();

  async connect(device: MikrotikDevice): Promise<boolean> {
    try {
      const api = new RouterOS.RouterOSAPI({
        host: device.address,
        user: device.username,
        password: device.password,
        port: device.port || 8728,
      });

      await api.connect();
      this.connections.set(device.id, api);
      return true;
    } catch (error) {
      console.error(`Failed to connect to MikroTik device ${device.name}:`, error);
      return false;
    }
  }

  async disconnect(deviceId: number): Promise<void> {
    const connection = this.connections.get(deviceId);
    if (connection) {
      await connection.close();
      this.connections.delete(deviceId);
    }
  }

  async getDeviceStats(deviceId: number): Promise<MikrotikStats | null> {
    const connection = this.connections.get(deviceId);
    if (!connection) return null;

    try {
      // Get system resources
      const [system] = await connection.write('/system/resource/print');

      // Get interface information
      const interfaces = await connection.write('/interface/print');

      // Get DHCP leases
      const dhcp = await connection.write('/ip/dhcp-server/lease/print');

      // Get wireless clients
      const wireless = await connection.write('/interface/wireless/registration-table/print');

      return {
        cpuLoad: Number(system.cpu_load),
        memoryUsage: Number(system.free_memory) / Number(system.total_memory) * 100,
        uptime: system.uptime,
        version: system.version,
        interfaces: interfaces.map((iface: any) => ({
          name: iface.name,
          type: iface.type,
          rxBytes: Number(iface.rx_byte || 0),
          txBytes: Number(iface.tx_byte || 0),
          rxPackets: Number(iface.rx_packet || 0),
          txPackets: Number(iface.tx_packet || 0),
          status: iface.running === 'true' ? 'active' : 'down'
        })),
        dhcpLeases: dhcp.map((lease: any) => ({
          address: lease.address,
          macAddress: lease['mac-address'],
          clientId: lease['client-id'] || '',
          hostName: lease['host-name'] || '',
          status: lease.status
        })),
        wirelessClients: wireless.map((client: any) => ({
          interface: client.interface,
          macAddress: client['mac-address'],
          signal: Number(client.signal_strength || 0),
          txRate: Number(client.tx_rate || 0),
          rxRate: Number(client.rx_rate || 0)
        }))
      };
    } catch (error) {
      console.error(`Failed to get stats from device ${deviceId}:`, error);
      return null;
    }
  }
}

export const mikrotikService = new MikrotikService();