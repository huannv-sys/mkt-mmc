import { NetworkStatus, MikrotikDevice, InsertMikrotikDevice } from "@shared/schema";

interface HistoricalNetworkData {
  timestamp: Date;
  status: NetworkStatus;
}

export interface IStorage {
  getCurrentNetworkStatus(): Promise<NetworkStatus>;
  updateNetworkStatus(status: NetworkStatus): Promise<void>;
  createMikrotikDevice(device: InsertMikrotikDevice): Promise<MikrotikDevice>;
  getMikrotikDevices(): Promise<MikrotikDevice[]>;
  getHistoricalData(start: Date, end: Date): Promise<HistoricalNetworkData[]>;
  storeHistoricalData(status: NetworkStatus): Promise<void>;
}

export class MemStorage implements IStorage {
  private currentStatus: NetworkStatus;
  private mikrotikDevices: MikrotikDevice[];
  private nextDeviceId: number;
  private historicalData: HistoricalNetworkData[];
  private readonly MAX_HISTORY_LENGTH = 1000; // Keep last 1000 records

  constructor() {
    this.currentStatus = {
      clients: {
        connected: 42,
        total: 100
      },
      traffic: [],
      interfaces: [
        { 
          name: 'eth0',
          traffic: '1.2 Gbps',
          status: 'active',
          bytesReceived: 1000000,
          bytesSent: 2000000,
          packetsReceived: 1000,
          packetsSent: 2000,
          errors: { rx: 0, tx: 0 },
          droppedPackets: { rx: 0, tx: 0 },
          speed: '1 Gbps',
          duplex: 'full',
          mtu: 1500
        },
        {
          name: 'wlan0',
          traffic: '850 Mbps',
          status: 'active',
          bytesReceived: 800000,
          bytesSent: 900000,
          packetsReceived: 800,
          packetsSent: 900,
          errors: { rx: 0, tx: 0 },
          droppedPackets: { rx: 0, tx: 0 },
          speed: '1 Gbps',
          duplex: 'full',
          mtu: 1500
        }
      ],
      wifi: {
        bands: ['2.4 GHz', '5 GHz'],
        channels: [1, 6, 11, 36, 40],
        connections: ['802.11ax', '802.11ac', '802.11n'],
        heatmap: [
          { lat: 51.505, lng: -0.09, intensity: 0.8 },
          { lat: 51.51, lng: -0.1, intensity: 0.6 },
          { lat: 51.49, lng: -0.08, intensity: 0.4 }
        ]
      }
    };
    this.mikrotikDevices = [];
    this.nextDeviceId = 1;
    this.historicalData = [];
  }

  async getCurrentNetworkStatus(): Promise<NetworkStatus> {
    return this.currentStatus;
  }

  async updateNetworkStatus(status: NetworkStatus): Promise<void> {
    this.currentStatus = status;
    await this.storeHistoricalData(status);
  }

  async createMikrotikDevice(device: InsertMikrotikDevice): Promise<MikrotikDevice> {
    const newDevice: MikrotikDevice = {
      id: this.nextDeviceId++,
      name: device.name,
      address: device.address,
      username: device.username,
      password: device.password,
      port: device.port ?? 8728,
      isConnected: false
    };
    this.mikrotikDevices.push(newDevice);
    return newDevice;
  }

  async getMikrotikDevices(): Promise<MikrotikDevice[]> {
    return this.mikrotikDevices;
  }

  async storeHistoricalData(status: NetworkStatus): Promise<void> {
    this.historicalData.push({
      timestamp: new Date(),
      status: { ...status }
    });

    // Keep only the last MAX_HISTORY_LENGTH records
    if (this.historicalData.length > this.MAX_HISTORY_LENGTH) {
      this.historicalData = this.historicalData.slice(-this.MAX_HISTORY_LENGTH);
    }
  }

  async getHistoricalData(start: Date, end: Date): Promise<HistoricalNetworkData[]> {
    return this.historicalData.filter(
      data => data.timestamp >= start && data.timestamp <= end
    );
  }
}

export const storage = new MemStorage();