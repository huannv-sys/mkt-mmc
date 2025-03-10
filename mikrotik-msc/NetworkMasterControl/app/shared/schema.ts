import { pgTable, text, serial, integer, timestamp, boolean, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const networkData = pgTable("network_data", {
  id: serial("id").primaryKey(),
  timestamp: timestamp("timestamp").defaultNow(),
  traffic: integer("traffic").notNull(),
  connectedClients: integer("connected_clients").notNull(),
  totalClients: integer("total_clients").notNull(),
  interfaceStats: jsonb("interface_stats").notNull(),
  mikrotikStats: jsonb("mikrotik_stats"),
});

export const mikrotikDevices = pgTable("mikrotik_devices", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  address: text("address").notNull(),
  username: text("username").notNull(),
  password: text("password").notNull(),
  port: integer("port").default(8728),
  isConnected: boolean("is_connected").default(false),
});

export const networkInterfaces = pgTable("network_interfaces", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  traffic: text("traffic").notNull(),
  status: text("status").notNull(),
  timestamp: timestamp("timestamp").defaultNow(),
  bytesReceived: integer("bytes_received").notNull(),
  bytesSent: integer("bytes_sent").notNull(),
  errors: jsonb("errors").notNull(),
  droppedPackets: jsonb("dropped_packets").notNull(),
});

export interface MikrotikStats {
  cpuLoad: number;
  memoryUsage: number;
  uptime: string;
  version: string;
  interfaces: {
    name: string;
    type: string;
    rxBytes: number;
    txBytes: number;
    rxPackets: number;
    txPackets: number;
    status: string;
  }[];
  dhcpLeases: {
    address: string;
    macAddress: string;
    clientId: string;
    hostName: string;
    status: string;
  }[];
  wirelessClients: {
    interface: string;
    macAddress: string;
    signal: number;
    txRate: number;
    rxRate: number;
  }[];
}

export const wifiConfig = pgTable("wifi_config", {
  id: serial("id").primaryKey(),
  bands: text("bands").array(),
  channels: integer("channels").array(),
  connections: text("connections").array(),
});

export interface InterfaceStats {
  name: string;
  traffic: string;
  status: string;
  bytesReceived: number;
  bytesSent: number;
  packetsReceived: number;
  packetsSent: number;
  errors: {
    rx: number;
    tx: number;
  };
  droppedPackets: {
    rx: number;
    tx: number;
  };
  speed: string;
  duplex: 'full' | 'half';
  mtu: number;
}

export interface NetworkStatus {
  clients: {
    connected: number;
    total: number;
  };
  traffic: {
    time: string;
    value: number;
  }[];
  interfaces: InterfaceStats[];
  wifi: {
    bands: string[];
    channels: number[];
    connections: string[];
    heatmap: {
      lat: number;
      lng: number;
      intensity: number;
    }[];
  };
  metrics?: {
    httpRequests: number;
    networkTraffic: number;
  };
  mikrotik?: MikrotikStats;
}

export type NetworkData = typeof networkData.$inferSelect;
export type NetworkInterface = typeof networkInterfaces.$inferSelect;
export type WifiConfig = typeof wifiConfig.$inferSelect;
export type MikrotikDevice = typeof mikrotikDevices.$inferSelect;

export const insertMikrotikDeviceSchema = createInsertSchema(mikrotikDevices).omit({
  id: true,
  isConnected: true,
});

export type InsertMikrotikDevice = z.infer<typeof insertMikrotikDeviceSchema>;