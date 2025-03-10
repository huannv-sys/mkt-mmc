import type { Express } from "express";
import { createServer, type Server } from "http";
import { Server as SocketIOServer } from 'socket.io';
import { storage } from "./storage";
import type { NetworkStatus, InterfaceStats } from "@shared/schema";
import * as promClient from 'prom-client';
import { mikrotikService } from './services/mikrotik';
import { mikrotikClient } from './services/mikrotik-client';
import { updateMetrics } from './services/mikrotik-metrics';

// Initialize Prometheus metrics
const collectDefaultMetrics = promClient.collectDefaultMetrics();
const registry = new promClient.Registry();

const httpRequestCount = new promClient.Counter({
  name: 'http_requests_total',
  help: 'Total HTTP requests',
  labelNames: ['method', 'route', 'status']
});

const networkTraffic = new promClient.Gauge({
  name: 'network_traffic_mbps',
  help: 'Current network traffic in Mbps'
});

// Add interface-specific metrics
const interfaceTraffic = new promClient.Gauge({
  name: 'interface_traffic_bytes',
  help: 'Interface traffic in bytes',
  labelNames: ['interface', 'direction']
});

registry.registerMetric(httpRequestCount);
registry.registerMetric(networkTraffic);
registry.registerMetric(interfaceTraffic);

export async function registerRoutes(app: Express): Promise<Server> {
  const httpServer = createServer(app);
  const io = new SocketIOServer(httpServer, {
    path: '/socket.io',
    cors: {
      origin: "*",
      methods: ["GET", "POST"]
    }
  });

  // MikroTik device management routes
  app.post('/api/mikrotik/devices', async (req, res) => {
    try {
      const device = await storage.createMikrotikDevice(req.body);
      const connected = await mikrotikService.connect(device);
      res.json({ ...device, isConnected: connected });
    } catch (error) {
      console.error('Error creating MikroTik device:', error);
      res.status(500).json({ error: 'Failed to create device' });
    }
  });

  app.get('/api/mikrotik/devices', async (_req, res) => {
    try {
      const devices = await storage.getMikrotikDevices();
      res.json(devices);
    } catch (error) {
      console.error('Error fetching MikroTik devices:', error);
      res.status(500).json({ error: 'Failed to fetch devices' });
    }
  });

  app.get('/api/historical-data', async (req, res) => {
    try {
      const start = new Date(req.query.start as string);
      const end = new Date(req.query.end as string);
      const data = await storage.getHistoricalData(start, end);
      res.json(data);
    } catch (error) {
      console.error('Error fetching historical data:', error);
      res.status(500).json({ error: 'Failed to fetch historical data' });
    }
  });

  // Handle Socket.IO connections
  io.on('connection', (socket) => {
    console.log('Client connected');

    // Send initial data
    const sendUpdate = async () => {
      try {
        const interfaces = await mikrotikClient.getInterfaces();
        const wireless = await mikrotikClient.getWirelessClients();
        const [systemResources] = await mikrotikClient.getSystemResources();

        const status: NetworkStatus = {
          clients: {
            connected: wireless.length,
            total: interfaces.length
          },
          traffic: [], // Will be updated with historical data
          interfaces: interfaces.map((iface: any) => ({
            name: iface.name,
            traffic: `${((Number(iface['rx-byte']) + Number(iface['tx-byte'])) / 1e6).toFixed(2)} MB/s`,
            status: iface.running === 'true' ? 'active' : 'down',
            bytesReceived: Number(iface['rx-byte']),
            bytesSent: Number(iface['tx-byte']),
            packetsReceived: Number(iface['rx-packet']),
            packetsSent: Number(iface['tx-packet']),
            errors: {
              rx: Number(iface['rx-error'] || 0),
              tx: Number(iface['tx-error'] || 0)
            },
            droppedPackets: {
              rx: Number(iface['rx-drop'] || 0),
              tx: Number(iface['tx-drop'] || 0)
            },
            speed: iface.speed || 'unknown',
            duplex: iface.duplex || 'unknown',
            mtu: Number(iface.mtu || 1500)
          })),
          wifi: {
            bands: ['2.4 GHz', '5 GHz'],
            channels: systemResources.channels || [],
            connections: [],
            heatmap: []
          }
        };

        // Store historical data
        await storage.storeHistoricalData(status);

        // Update metrics
        await updateMetrics();

        socket.emit('network-update', status);
      } catch (error) {
        console.error('Error sending network update:', error);
      }
    };

    // Send initial update
    sendUpdate();

    // Set up interval for updates
    const interval = setInterval(sendUpdate, 2000);

    socket.on('disconnect', () => {
      clearInterval(interval);
      console.log('Client disconnected');
    });

    socket.on('error', (error) => {
      console.error('Socket error:', error);
      clearInterval(interval);
    });
  });

  // Prometheus metrics endpoint
  app.get('/metrics', async (_req, res) => {
    try {
      await updateMetrics();
      res.set('Content-Type', registry.contentType);
      res.end(await registry.metrics());
    } catch (error) {
      console.error('Error collecting metrics:', error);
      res.status(500).end();
    }
  });

  // Middleware for tracking HTTP requests
  app.use((req, res, next) => {
    res.on('finish', () => {
      httpRequestCount.inc({
        method: req.method,
        route: req.route?.path || 'unknown',
        status: res.statusCode
      });
    });
    next();
  });

  return httpServer;
}