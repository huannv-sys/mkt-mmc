import * as RouterOS from 'node-routeros';
import { promisify } from 'util';

class MikroTikClient {
  private conn: any;
  private static instance: MikroTikClient;

  private constructor() {
    if (!process.env.MIKROTIK_HOST || !process.env.MIKROTIK_USER || !process.env.MIKROTIK_PASSWORD) {
      throw new Error('MikroTik credentials not configured');
    }

    this.conn = new RouterOS.RouterOSAPI({
      host: process.env.MIKROTIK_HOST,
      user: process.env.MIKROTIK_USER,
      password: process.env.MIKROTIK_PASSWORD,
      timeout: 30
    });
  }

  public static getInstance(): MikroTikClient {
    if (!MikroTikClient.instance) {
      MikroTikClient.instance = new MikroTikClient();
    }
    return MikroTikClient.instance;
  }

  async connect(): Promise<void> {
    try {
      await this.conn.connect();
      console.log('Connected to MikroTik router');
    } catch (error) {
      console.error('Failed to connect to MikroTik:', error);
      throw error;
    }
  }

  async query(path: string) {
    try {
      const query = promisify(this.conn.query).bind(this.conn);
      return await query(path);
    } catch (error) {
      console.error('MikroTik API Error:', error);
      return [];
    }
  }

  async getInterfaces() {
    return this.query('/interface print');
  }

  async getWirelessClients() {
    return this.query('/interface/wireless/registration-table print');
  }

  async getSystemResources() {
    return this.query('/system/resource print');
  }

  async getDHCPLeases() {
    return this.query('/ip/dhcp-server/lease print');
  }
}

export const mikrotikClient = MikroTikClient.getInstance();