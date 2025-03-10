#!/usr/bin/env python3
"""
MikroTik Web Monitor
Ứng dụng web giám sát thiết bị MikroTik theo thời gian thực
"""

import os
import sys
import json
import time
import logging
import asyncio
import threading
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mikrotik_web_monitor")

# Kiểm tra các gói cần thiết
try:
    import routeros_api
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Request, Form, UploadFile, File
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.templating import Jinja2Templates
    import uvicorn
except ImportError as e:
    logger.error(f"Thiếu gói phụ thuộc: {e}")
    logger.info("Chạy: pip install routeros-api fastapi uvicorn websockets jinja2")
    sys.exit(1)

# Import các module quản lý
try:
    from mikrotik_client_monitor import MikroTikClientMonitor
    from mikrotik_firewall_manager import MikroTikFirewallManager
    from mikrotik_capsman_manager import MikroTikCAPsMANManager
    from mikrotik_backup_manager import MikroTikBackupManager
    from mikrotik_vpn_manager import MikroTikVPNManager
except ImportError as e:
    logger.warning(f"Một số module quản lý không khả dụng: {e}")
    logger.info("Một số tính năng có thể bị giới hạn")

# Load biến môi trường
load_dotenv()


class MikroTikMonitor:
    """Lớp giám sát thiết bị MikroTik."""
    
    def __init__(self, host, username, password):
        """Khởi tạo với thông tin kết nối."""
        self.host = host
        self.username = username
        self.password = password
        self.connection = None
        self.api = None
        self.running = False
        self.data_history = {}  # Lịch sử dữ liệu theo interface
        self.device_info = {}   # Thông tin thiết bị
        self.lock = threading.Lock()  # Lock để đồng bộ truy cập vào data
    
    def connect(self):
        """Kết nối đến thiết bị MikroTik và trả về API object."""
        try:
            # Thiết lập kết nối
            logger.info(f"Đang kết nối đến {self.host}...")
            self.connection = routeros_api.RouterOsApiPool(
                self.host,
                username=self.username,
                password=self.password,
                plaintext_login=True
            )
            self.api = self.connection.get_api()
            logger.info(f"Đã kết nối thành công đến {self.host}")
            
            # Lấy thông tin thiết bị
            self.get_device_info()
            
            return self.api
        except Exception as e:
            logger.error(f"Lỗi kết nối đến {self.host}: {e}")
            return None
    
    def disconnect(self):
        """Ngắt kết nối."""
        if self.connection:
            self.connection.disconnect()
            logger.info(f"Đã ngắt kết nối từ {self.host}")
    
    def get_device_info(self):
        """Lấy thông tin cơ bản về thiết bị."""
        if not self.api:
            return None
        
        try:
            resource = self.api.get_resource('/system/resource')
            identity = self.api.get_resource('/system/identity')
            
            resource_data = resource.get()[0]
            identity_data = identity.get()[0]
            
            self.device_info = {
                'hostname': identity_data.get('name', 'Unknown'),
                'model': resource_data.get('board-name', 'Unknown'),
                'ros_version': resource_data.get('version', 'Unknown'),
                'uptime': resource_data.get('uptime', 'Unknown'),
                'cpu_load': resource_data.get('cpu-load', '0'),
                'free_memory': int(resource_data.get('free-memory', '0')) // 1024 // 1024,
                'total_memory': int(resource_data.get('total-memory', '0')) // 1024 // 1024,
                'free_hdd': int(resource_data.get('free-hdd-space', '0')) // 1024 // 1024,
                'total_hdd': int(resource_data.get('total-hdd-space', '0')) // 1024 // 1024,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"Đã lấy thông tin thiết bị: {self.device_info['hostname']} ({self.device_info['model']})")
            return self.device_info
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin thiết bị: {e}")
            return None
    
    def get_interfaces(self):
        """Lấy danh sách interfaces đang hoạt động."""
        if not self.api:
            return None
        
        try:
            interfaces = self.api.get_resource('/interface')
            interface_list = interfaces.get()
            
            result = []
            for iface in interface_list:
                status = "active" if iface.get('running', 'false') == 'true' else "inactive"
                result.append({
                    'name': iface.get('name', 'Unknown'),
                    'type': iface.get('type', 'Unknown'),
                    'running': iface.get('running', 'false'),
                    'disabled': iface.get('disabled', 'true'),
                    'status': status,
                    'comment': iface.get('comment', '')
                })
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách interfaces: {e}")
            return None
    
    def get_active_interfaces(self):
        """Lấy danh sách các interface đang hoạt động."""
        interfaces = self.get_interfaces()
        if not interfaces:
            return []
        
        # Lọc các interface đang hoạt động và không bị vô hiệu hóa
        active_interfaces = [iface for iface in interfaces 
                           if iface['running'] == 'true' and iface['disabled'] == 'false']
        
        return active_interfaces
    
    def get_interface_traffic(self, interface_name):
        """Lấy dữ liệu traffic cho một interface cụ thể."""
        if not self.api:
            return None
        
        try:
            interfaces = self.api.get_resource('/interface')
            iface_data = interfaces.get(name=interface_name)
            
            if iface_data and len(iface_data) > 0:
                current_tx = int(iface_data[0].get('tx-byte', '0'))
                current_rx = int(iface_data[0].get('rx-byte', '0'))
                return current_tx, current_rx
            else:
                return None
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu traffic cho {interface_name}: {e}")
            return None
    
    def start_monitoring(self, interval=2):
        """Bắt đầu giám sát và thu thập dữ liệu từ thiết bị."""
        if not self.api:
            logger.error("Không có kết nối API. Vui lòng kết nối trước.")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info(f"Đã bắt đầu giám sát với chu kỳ {interval} giây")
    
    def stop_monitoring(self):
        """Dừng giám sát."""
        self.running = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=3)
        logger.info("Đã dừng giám sát")
    
    def _monitor_loop(self, interval):
        """Vòng lặp chính để giám sát các interfaces."""
        # Khởi tạo dữ liệu ban đầu
        self._init_interface_data()
        
        last_device_update = 0
        
        while self.running:
            current_time = time.time()
            
            # Cập nhật thông tin thiết bị mỗi 10 giây
            if current_time - last_device_update >= 10:
                self.get_device_info()
                last_device_update = current_time
            
            # Cập nhật dữ liệu traffic cho từng interface
            active_interfaces = self.get_active_interfaces()
            for iface in active_interfaces:
                self._update_interface_data(iface['name'], interval)
            
            # Ngủ đến lần cập nhật tiếp theo
            time.sleep(interval)
    
    def _init_interface_data(self):
        """Khởi tạo dữ liệu cho tất cả các interfaces."""
        active_interfaces = self.get_active_interfaces()
        if not active_interfaces:
            return
        
        with self.lock:
            for iface in active_interfaces:
                name = iface['name']
                if name not in self.data_history:
                    traffic_data = self.get_interface_traffic(name)
                    if traffic_data:
                        self.data_history[name] = {
                            'previous_data': traffic_data,
                            'history': [],
                            'max_history_length': 60  # Giữ 60 điểm dữ liệu
                        }
    
    def _update_interface_data(self, interface_name, interval):
        """Cập nhật dữ liệu cho một interface cụ thể."""
        if interface_name not in self.data_history:
            # Khởi tạo nếu chưa có
            traffic_data = self.get_interface_traffic(interface_name)
            if traffic_data:
                with self.lock:
                    self.data_history[interface_name] = {
                        'previous_data': traffic_data,
                        'history': [],
                        'max_history_length': 60
                    }
            return
        
        # Lấy dữ liệu traffic mới
        current_data = self.get_interface_traffic(interface_name)
        if not current_data:
            return
        
        with self.lock:
            previous_data = self.data_history[interface_name]['previous_data']
            if previous_data:
                # Tính toán tốc độ dựa trên sự khác biệt
                tx_bytes = current_data[0] - previous_data[0]
                rx_bytes = current_data[1] - previous_data[1]
                
                # Bytes/giây
                tx_bytes_per_second = tx_bytes / interval
                rx_bytes_per_second = rx_bytes / interval
                
                # Bits/giây (1 byte = 8 bits)
                tx_bits_per_second = tx_bytes_per_second * 8
                rx_bits_per_second = rx_bytes_per_second * 8
                
                # Chuyển đổi sang KB/s và MB/s
                tx_kbps = tx_bits_per_second / 1024
                rx_kbps = rx_bits_per_second / 1024
                tx_mbps = tx_kbps / 1024
                rx_mbps = rx_kbps / 1024
                
                # Thêm vào lịch sử
                timestamp = time.time()
                self.data_history[interface_name]['history'].append({
                    'timestamp': timestamp,
                    'tx_kbps': tx_kbps,
                    'rx_kbps': rx_kbps,
                    'tx_mbps': tx_mbps,
                    'rx_mbps': rx_mbps
                })
                
                # Giới hạn kích thước lịch sử
                max_length = self.data_history[interface_name]['max_history_length']
                if len(self.data_history[interface_name]['history']) > max_length:
                    self.data_history[interface_name]['history'] = self.data_history[interface_name]['history'][-max_length:]
            
            # Cập nhật dữ liệu trước đó
            self.data_history[interface_name]['previous_data'] = current_data
    
    def get_current_data(self):
        """Lấy dữ liệu mới nhất về thiết bị và traffic."""
        with self.lock:
            result = {
                'device': self.device_info,
                'interfaces': {}
            }
            
            # Thêm dữ liệu traffic cho mỗi interface
            for name, data in self.data_history.items():
                if data['history']:
                    latest = data['history'][-1]
                    result['interfaces'][name] = {
                        'current': latest,
                        'history': data['history']
                    }
            
            return result


class ConnectionManager:
    """Quản lý các kết nối WebSocket."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Lỗi khi gửi dữ liệu: {e}")


# Khởi tạo ứng dụng FastAPI
app = FastAPI(title="MikroTik Web Monitor")

# Thêm CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả origins trong môi trường phát triển
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo connection manager
manager = ConnectionManager()

# Biến globals
mikrotik_monitor = None  # Monitor chính
client_monitor = None    # Client Monitor
firewall_manager = None  # Firewall Manager
capsman_manager = None   # CAPsMAN Manager
backup_manager = None    # Backup Manager
vpn_manager = None       # VPN Manager


# Trang HTML cho client
html = """
<!DOCTYPE html>
<html>
<head>
    <title>MikroTik Web Monitor</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #0056b3;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .device-info {
            background-color: white;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .traffic-charts {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 20px;
        }
        .chart-container {
            flex: 1 1 500px;
            background-color: white;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .interfaces-list {
            background-color: white;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        table, th, td {
            border: 1px solid #ddd;
        }
        th, td {
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .footer {
            text-align: center;
            margin-top: 20px;
            color: #666;
        }
        .status-active {
            color: green;
            font-weight: bold;
        }
        .status-inactive {
            color: red;
        }
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .dashboard-item {
            background-color: white;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        .dashboard-value {
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }
        .dashboard-label {
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>MikroTik Web Monitor</h1>
            <div id="connection-status">Đang kết nối...</div>
        </div>
        
        <div class="device-info">
            <h2>Thông tin Thiết bị</h2>
            <div class="dashboard-grid">
                <div class="dashboard-item">
                    <div class="dashboard-label">Tên Thiết bị</div>
                    <div id="device-hostname" class="dashboard-value">-</div>
                </div>
                <div class="dashboard-item">
                    <div class="dashboard-label">Mẫu Thiết bị</div>
                    <div id="device-model" class="dashboard-value">-</div>
                </div>
                <div class="dashboard-item">
                    <div class="dashboard-label">RouterOS</div>
                    <div id="device-ros" class="dashboard-value">-</div>
                </div>
                <div class="dashboard-item">
                    <div class="dashboard-label">CPU Load</div>
                    <div id="device-cpu" class="dashboard-value">-</div>
                </div>
                <div class="dashboard-item">
                    <div class="dashboard-label">RAM Sử dụng</div>
                    <div id="device-ram" class="dashboard-value">-</div>
                </div>
                <div class="dashboard-item">
                    <div class="dashboard-label">Uptime</div>
                    <div id="device-uptime" class="dashboard-value">-</div>
                </div>
            </div>
        </div>
        
        <div class="interfaces-list">
            <h2>Danh sách Interfaces</h2>
            <table id="interfaces-table">
                <thead>
                    <tr>
                        <th>Tên</th>
                        <th>Loại</th>
                        <th>Trạng thái</th>
                        <th>TX Hiện tại</th>
                        <th>RX Hiện tại</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Dữ liệu interfaces sẽ được thêm ở đây -->
                </tbody>
            </table>
        </div>
        
        <div class="traffic-charts">
            <!-- Biểu đồ sẽ được thêm ở đây -->
        </div>
        
        <div class="footer">
            <p>MikroTik Web Monitor © 2025 - Dữ liệu cập nhật theo thời gian thực</p>
        </div>
    </div>

    <script>
        // Kết nối WebSocket
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        let socket;
        
        // Biểu đồ
        const charts = {};
        
        // Số điểm dữ liệu tối đa trên biểu đồ
        const MAX_DATA_POINTS = 30;
        
        function connect() {
            socket = new WebSocket(wsUrl);
            
            socket.onopen = function(e) {
                document.getElementById('connection-status').textContent = 'Đã kết nối';
                console.log('WebSocket connection established');
            };
            
            socket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateUI(data);
            };
            
            socket.onclose = function(event) {
                document.getElementById('connection-status').textContent = 'Mất kết nối - đang thử lại...';
                console.log('WebSocket connection closed. Reconnecting...');
                setTimeout(connect, 3000);
            };
            
            socket.onerror = function(error) {
                console.error('WebSocket error:', error);
                socket.close();
            };
        }
        
        function updateUI(data) {
            // Cập nhật thông tin thiết bị
            if (data.device) {
                document.getElementById('device-hostname').textContent = data.device.hostname || '-';
                document.getElementById('device-model').textContent = data.device.model || '-';
                document.getElementById('device-ros').textContent = data.device.ros_version || '-';
                document.getElementById('device-cpu').textContent = `${data.device.cpu_load || '0'}%`;
                document.getElementById('device-ram').textContent = `${data.device.free_memory || '0'}/${data.device.total_memory || '0'} MB`;
                document.getElementById('device-uptime').textContent = data.device.uptime || '-';
            }
            
            // Cập nhật bảng interfaces
            if (data.interfaces) {
                const table = document.getElementById('interfaces-table').getElementsByTagName('tbody')[0];
                table.innerHTML = '';
                
                for (const [name, iface] of Object.entries(data.interfaces)) {
                    const row = table.insertRow();
                    
                    const nameCell = row.insertCell(0);
                    nameCell.textContent = name;
                    
                    const typeCell = row.insertCell(1);
                    typeCell.textContent = '-'; // Thông tin loại sẽ được cập nhật sau nếu có
                    
                    const statusCell = row.insertCell(2);
                    statusCell.textContent = 'Hoạt động';
                    statusCell.className = 'status-active';
                    
                    const txCell = row.insertCell(3);
                    txCell.textContent = `${iface.current.tx_kbps.toFixed(2)} KB/s (${iface.current.tx_mbps.toFixed(2)} MB/s)`;
                    
                    const rxCell = row.insertCell(4);
                    rxCell.textContent = `${iface.current.rx_kbps.toFixed(2)} KB/s (${iface.current.rx_mbps.toFixed(2)} MB/s)`;
                    
                    // Tạo biểu đồ nếu chưa có
                    if (!charts[name]) {
                        createChart(name);
                    }
                    
                    // Cập nhật dữ liệu cho biểu đồ
                    updateChart(name, iface.history);
                }
            }
        }
        
        function createChart(interfaceName) {
            // Kiểm tra xem đã có container chưa
            let chartContainer = document.querySelector(`.chart-container[data-interface="${interfaceName}"]`);
            
            if (!chartContainer) {
                // Tạo container mới
                chartContainer = document.createElement('div');
                chartContainer.className = 'chart-container';
                chartContainer.setAttribute('data-interface', interfaceName);
                
                const chartTitle = document.createElement('h3');
                chartTitle.textContent = `Traffic Interface ${interfaceName}`;
                chartContainer.appendChild(chartTitle);
                
                const canvas = document.createElement('canvas');
                canvas.id = `chart-${interfaceName}`;
                chartContainer.appendChild(canvas);
                
                document.querySelector('.traffic-charts').appendChild(chartContainer);
                
                // Tạo biểu đồ
                const ctx = canvas.getContext('2d');
                charts[interfaceName] = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: Array(MAX_DATA_POINTS).fill(''),
                        datasets: [
                            {
                                label: 'TX (KB/s)',
                                data: Array(MAX_DATA_POINTS).fill(null),
                                borderColor: 'rgb(255, 99, 132)',
                                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                                borderWidth: 2,
                                tension: 0.1
                            },
                            {
                                label: 'RX (KB/s)',
                                data: Array(MAX_DATA_POINTS).fill(null),
                                borderColor: 'rgb(54, 162, 235)',
                                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                                borderWidth: 2,
                                tension: 0.1
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'KB/s'
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: 'Thời gian'
                                }
                            }
                        },
                        animation: {
                            duration: 0 // Tắt animation để tăng hiệu suất
                        },
                        plugins: {
                            legend: {
                                position: 'top',
                            }
                        }
                    }
                });
            }
        }
        
        function updateChart(interfaceName, historyData) {
            const chart = charts[interfaceName];
            if (!chart) return;
            
            // Chuẩn bị dữ liệu mới
            const txData = [];
            const rxData = [];
            const labels = [];
            
            // Lấy dữ liệu từ lịch sử
            for (const point of historyData) {
                txData.push(point.tx_kbps);
                rxData.push(point.rx_kbps);
                
                // Tạo label thời gian
                const date = new Date(point.timestamp * 1000);
                const timeLabel = `${date.getHours()}:${date.getMinutes()}:${date.getSeconds()}`;
                labels.push(timeLabel);
            }
            
            // Cập nhật dữ liệu cho biểu đồ
            chart.data.labels = labels;
            chart.data.datasets[0].data = txData;
            chart.data.datasets[1].data = rxData;
            
            // Điều chỉnh trục y để phù hợp với dữ liệu
            const maxValue = Math.max(...txData, ...rxData);
            chart.options.scales.y.max = maxValue * 1.2; // Thêm 20% lề trên
            
            chart.update();
        }
        
        // Kết nối khi trang được load
        window.onload = connect;
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get_html():
    """Trả về trang HTML giao diện người dùng."""
    return html


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket để gửi dữ liệu theo thời gian thực."""
    await manager.connect(websocket)
    try:
        while True:
            if mikrotik_monitor:
                # Lấy dữ liệu mới nhất
                data = mikrotik_monitor.get_current_data()
                
                # Gửi dữ liệu qua WebSocket
                if data:
                    await websocket.send_text(json.dumps(data))
            
            # Đợi 1 giây trước khi gửi dữ liệu mới
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client đã ngắt kết nối")
    except Exception as e:
        logger.error(f"Lỗi WebSocket: {e}")
        manager.disconnect(websocket)


@app.get("/api/device-info")
async def get_device_info():
    """API endpoint để lấy thông tin thiết bị."""
    if not mikrotik_monitor:
        return JSONResponse(content={"error": "Chưa kết nối đến thiết bị"}, status_code=500)
    
    device_info = mikrotik_monitor.device_info
    return JSONResponse(content=device_info)


@app.get("/api/interfaces")
async def get_interfaces():
    """API endpoint để lấy danh sách interfaces."""
    if not mikrotik_monitor:
        return JSONResponse(content={"error": "Chưa kết nối đến thiết bị"}, status_code=500)
    
    interfaces = mikrotik_monitor.get_interfaces()
    return JSONResponse(content=interfaces)


@app.get("/api/traffic/{interface_name}")
async def get_interface_traffic(interface_name: str):
    """API endpoint để lấy dữ liệu traffic của một interface cụ thể."""
    if not mikrotik_monitor:
        return JSONResponse(content={"error": "Chưa kết nối đến thiết bị"}, status_code=500)
    
    with mikrotik_monitor.lock:
        if interface_name in mikrotik_monitor.data_history:
            return JSONResponse(content=mikrotik_monitor.data_history[interface_name])
        else:
            return JSONResponse(content={"error": f"Không tìm thấy interface {interface_name}"}, status_code=404)


# CLIENTS API ENDPOINTS
@app.get("/api/clients")
async def get_clients():
    """API endpoint để lấy danh sách các clients."""
    global client_monitor
    
    if not client_monitor:
        return JSONResponse(content={"error": "Chưa khởi tạo Client Monitor"}, status_code=500)
    
    clients = client_monitor.get_all_clients()
    return JSONResponse(content={"clients": clients})


@app.get("/api/clients/wireless")
async def get_wireless_clients():
    """API endpoint để lấy danh sách các clients kết nối không dây."""
    global client_monitor
    
    if not client_monitor:
        return JSONResponse(content={"error": "Chưa khởi tạo Client Monitor"}, status_code=500)
    
    clients = client_monitor.get_wireless_clients()
    return JSONResponse(content={"clients": clients})


@app.get("/api/clients/dhcp")
async def get_dhcp_leases():
    """API endpoint để lấy danh sách các DHCP leases."""
    global client_monitor
    
    if not client_monitor:
        return JSONResponse(content={"error": "Chưa khởi tạo Client Monitor"}, status_code=500)
    
    leases = client_monitor.get_dhcp_leases()
    return JSONResponse(content={"leases": leases})


@app.get("/api/clients/blocked")
async def get_blocked_clients():
    """API endpoint để lấy danh sách các clients bị block."""
    global client_monitor
    
    if not client_monitor:
        return JSONResponse(content={"error": "Chưa khởi tạo Client Monitor"}, status_code=500)
    
    blocked = client_monitor.get_blocked_clients()
    return JSONResponse(content={"blocked": blocked})


@app.post("/api/clients/block")
async def block_client(ip: str = Form(None), mac: str = Form(None), comment: str = Form(None)):
    """API endpoint để block một client."""
    global client_monitor
    
    if not client_monitor:
        return JSONResponse(content={"error": "Chưa khởi tạo Client Monitor"}, status_code=500)
    
    if not ip and not mac:
        return JSONResponse(content={"error": "Phải cung cấp IP hoặc MAC address"}, status_code=400)
    
    result = client_monitor.block_client(ip, mac, comment)
    if result:
        return JSONResponse(content={"success": True, "message": f"Đã block client {ip or mac}"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể block client"}, status_code=500)


@app.post("/api/clients/unblock")
async def unblock_client(ip: str = Form(None), mac: str = Form(None)):
    """API endpoint để unblock một client."""
    global client_monitor
    
    if not client_monitor:
        return JSONResponse(content={"error": "Chưa khởi tạo Client Monitor"}, status_code=500)
    
    if not ip and not mac:
        return JSONResponse(content={"error": "Phải cung cấp IP hoặc MAC address"}, status_code=400)
    
    result = client_monitor.unblock_client(ip, mac)
    if result:
        return JSONResponse(content={"success": True, "message": f"Đã unblock client {ip or mac}"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể unblock client"}, status_code=500)


# FIREWALL API ENDPOINTS
@app.get("/api/firewall/filter")
async def get_filter_rules():
    """API endpoint để lấy danh sách các filter rules."""
    global firewall_manager
    
    if not firewall_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Firewall Manager"}, status_code=500)
    
    rules = firewall_manager.get_filter_rules()
    return JSONResponse(content={"rules": rules})


@app.get("/api/firewall/nat")
async def get_nat_rules():
    """API endpoint để lấy danh sách các NAT rules."""
    global firewall_manager
    
    if not firewall_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Firewall Manager"}, status_code=500)
    
    rules = firewall_manager.get_nat_rules()
    return JSONResponse(content={"rules": rules})


@app.get("/api/firewall/address-list")
async def get_address_lists():
    """API endpoint để lấy danh sách các address lists."""
    global firewall_manager
    
    if not firewall_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Firewall Manager"}, status_code=500)
    
    lists = firewall_manager.get_address_lists()
    return JSONResponse(content={"lists": lists})


@app.post("/api/firewall/filter/add")
async def add_filter_rule(
    chain: str = Form(...),
    action: str = Form(...),
    src_address: str = Form(None),
    dst_address: str = Form(None),
    protocol: str = Form(None),
    src_port: str = Form(None),
    dst_port: str = Form(None),
    comment: str = Form(None),
    disabled: bool = Form(False)
):
    """API endpoint để thêm một filter rule mới."""
    global firewall_manager
    
    if not firewall_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Firewall Manager"}, status_code=500)
    
    result = firewall_manager.add_filter_rule(
        chain=chain,
        action=action,
        src_address=src_address,
        dst_address=dst_address,
        protocol=protocol,
        src_port=src_port,
        dst_port=dst_port,
        comment=comment,
        disabled=disabled
    )
    
    if result:
        return JSONResponse(content={"success": True, "message": "Đã thêm filter rule"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể thêm filter rule"}, status_code=500)


@app.post("/api/firewall/port-forward/add")
async def add_port_forward(
    dst_port: str = Form(...),
    to_address: str = Form(...),
    to_port: str = Form(None),
    protocol: str = Form("tcp"),
    comment: str = Form(None),
    disabled: bool = Form(False)
):
    """API endpoint để thêm một port forward rule mới."""
    global firewall_manager
    
    if not firewall_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Firewall Manager"}, status_code=500)
    
    result = firewall_manager.add_port_forward(
        dst_port=dst_port,
        to_address=to_address,
        to_port=to_port,
        protocol=protocol,
        comment=comment,
        disabled=disabled
    )
    
    if result:
        return JSONResponse(content={"success": True, "message": "Đã thêm port forward rule"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể thêm port forward rule"}, status_code=500)


@app.post("/api/firewall/rule/remove")
async def remove_firewall_rule(rule_type: str = Form(...), rule_id: str = Form(...)):
    """API endpoint để xóa một rule."""
    global firewall_manager
    
    if not firewall_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Firewall Manager"}, status_code=500)
    
    result = firewall_manager.remove_firewall_rule(rule_type, rule_id)
    
    if result:
        return JSONResponse(content={"success": True, "message": f"Đã xóa {rule_type} rule với ID {rule_id}"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể xóa rule"}, status_code=500)


# CAPSMAN API ENDPOINTS
@app.get("/api/capsman/status")
async def get_capsman_status():
    """API endpoint để kiểm tra trạng thái CAPsMAN."""
    global capsman_manager
    
    if not capsman_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo CAPsMAN Manager"}, status_code=500)
    
    enabled = capsman_manager.check_capsman_enabled()
    return JSONResponse(content={"enabled": enabled})


@app.post("/api/capsman/enable")
async def enable_capsman(enabled: bool = Form(True)):
    """API endpoint để bật/tắt CAPsMAN."""
    global capsman_manager
    
    if not capsman_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo CAPsMAN Manager"}, status_code=500)
    
    result = capsman_manager.enable_capsman(enabled)
    
    if result:
        status = "bật" if enabled else "tắt"
        return JSONResponse(content={"success": True, "message": f"Đã {status} CAPsMAN"})
    else:
        return JSONResponse(content={"success": False, "message": f"Không thể {'bật' if enabled else 'tắt'} CAPsMAN"}, status_code=500)


@app.get("/api/capsman/profiles")
async def get_configuration_profiles():
    """API endpoint để lấy danh sách configuration profiles."""
    global capsman_manager
    
    if not capsman_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo CAPsMAN Manager"}, status_code=500)
    
    profiles = capsman_manager.get_configuration_profiles()
    return JSONResponse(content={"profiles": profiles})


@app.get("/api/capsman/aps")
async def get_access_points():
    """API endpoint để lấy danh sách Access Points."""
    global capsman_manager
    
    if not capsman_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo CAPsMAN Manager"}, status_code=500)
    
    aps = capsman_manager.get_access_points()
    return JSONResponse(content={"access_points": aps})


@app.post("/api/capsman/profile/add")
async def add_configuration_profile(
    name: str = Form(...),
    ssid: str = Form(...),
    security: str = Form("wpa2-psk"),
    passphrase: str = Form(None),
    datapath: str = Form(None)
):
    """API endpoint để thêm một configuration profile mới."""
    global capsman_manager
    
    if not capsman_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo CAPsMAN Manager"}, status_code=500)
    
    result = capsman_manager.add_configuration_profile(name, ssid, security, passphrase, datapath)
    
    if result:
        return JSONResponse(content={"success": True, "message": f"Đã thêm configuration profile {name}"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể thêm configuration profile"}, status_code=500)


@app.post("/api/capsman/ap/reboot")
async def reboot_access_point(mac: str = Form(...)):
    """API endpoint để khởi động lại một Access Point."""
    global capsman_manager
    
    if not capsman_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo CAPsMAN Manager"}, status_code=500)
    
    result = capsman_manager.reboot_access_point(mac)
    
    if result:
        return JSONResponse(content={"success": True, "message": f"Đã gửi lệnh khởi động lại Access Point {mac}"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể khởi động lại Access Point"}, status_code=500)


# BACKUP API ENDPOINTS
@app.get("/api/backup/list")
async def list_backups():
    """API endpoint để liệt kê các file backup."""
    global backup_manager
    
    if not backup_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Backup Manager"}, status_code=500)
    
    backups = backup_manager.list_backups()
    return JSONResponse(content={"backups": backups})


@app.get("/api/backup/exports")
async def list_exports():
    """API endpoint để liệt kê các file export."""
    global backup_manager
    
    if not backup_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Backup Manager"}, status_code=500)
    
    exports = backup_manager.list_exports()
    return JSONResponse(content={"exports": exports})


@app.post("/api/backup/create")
async def create_backup(name: str = Form(None), include_sensitive: bool = Form(False)):
    """API endpoint để tạo một backup mới."""
    global backup_manager
    
    if not backup_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Backup Manager"}, status_code=500)
    
    result = backup_manager.create_backup(name, include_sensitive)
    
    if result:
        return JSONResponse(content={"success": True, "message": "Đã tạo backup thành công"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể tạo backup"}, status_code=500)


@app.post("/api/backup/export")
async def create_export(
    name: str = Form(None),
    compact: bool = Form(False),
    include_sensitive: bool = Form(False)
):
    """API endpoint để xuất cấu hình."""
    global backup_manager
    
    if not backup_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Backup Manager"}, status_code=500)
    
    result = backup_manager.create_export(name, compact, include_sensitive)
    
    if result:
        return JSONResponse(content={"success": True, "message": "Đã xuất cấu hình thành công"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể xuất cấu hình"}, status_code=500)


@app.post("/api/backup/restore")
async def restore_backup(file: str = Form(...)):
    """API endpoint để khôi phục từ file backup."""
    global backup_manager
    
    if not backup_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Backup Manager"}, status_code=500)
    
    result = backup_manager.restore_backup(file)
    
    if result:
        return JSONResponse(content={"success": True, "message": "Đã gửi lệnh khôi phục backup thành công"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể khôi phục từ backup"}, status_code=500)


@app.post("/api/backup/upload")
async def upload_backup(backup_file: UploadFile = File(...)):
    """API endpoint để tải file backup lên."""
    global backup_manager
    
    if not backup_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Backup Manager"}, status_code=500)
    
    # Lưu file tạm thời
    temp_file_path = os.path.join(backup_manager.backup_dir, backup_file.filename)
    with open(temp_file_path, "wb") as f:
        contents = await backup_file.read()
        f.write(contents)
    
    # Tải lên thiết bị
    result = backup_manager.upload_backup(temp_file_path)
    
    if result:
        return JSONResponse(content={"success": True, "message": f"Đã tải lên file {backup_file.filename} thành công"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể tải lên file backup"}, status_code=500)


@app.on_event("startup")
async def startup_event():
    """Sự kiện khi ứng dụng khởi động."""
    global mikrotik_monitor, client_monitor, firewall_manager, capsman_manager, backup_manager, vpn_manager
    
    # Lấy thông tin kết nối từ biến môi trường
    host = os.getenv('MIKROTIK_HOST')
    username = os.getenv('MIKROTIK_USER')
    password = os.getenv('MIKROTIK_PASSWORD')
    
    if not host or not username or not password:
        logger.error("Không tìm thấy thông tin kết nối MikroTik trong file .env")
        logger.info("Vui lòng kiểm tra file .env và đảm bảo đã cấu hình MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASSWORD")
        return
    
    # Khởi tạo monitor
    mikrotik_monitor = MikroTikMonitor(host, username, password)
    
    # Khởi tạo các module quản lý khác
    try:
        if 'MikroTikClientMonitor' in globals():
            client_monitor = MikroTikClientMonitor(host, username, password)
            logger.info("Đã khởi tạo Client Monitor")
    except Exception as e:
        logger.warning(f"Không thể khởi tạo Client Monitor: {e}")
        
    try:
        if 'MikroTikFirewallManager' in globals():
            firewall_manager = MikroTikFirewallManager(host, username, password)
            logger.info("Đã khởi tạo Firewall Manager")
    except Exception as e:
        logger.warning(f"Không thể khởi tạo Firewall Manager: {e}")
        
    try:
        if 'MikroTikCAPsMANManager' in globals():
            capsman_manager = MikroTikCAPsMANManager(host, username, password)
            logger.info("Đã khởi tạo CAPsMAN Manager")
    except Exception as e:
        logger.warning(f"Không thể khởi tạo CAPsMAN Manager: {e}")
        
    try:
        if 'MikroTikBackupManager' in globals():
            backup_manager = MikroTikBackupManager(host, username, password)
            logger.info("Đã khởi tạo Backup Manager")
    except Exception as e:
        logger.warning(f"Không thể khởi tạo Backup Manager: {e}")
        
    try:
        if 'MikroTikVPNManager' in globals():
            vpn_manager = MikroTikVPNManager(host, username, password)
            logger.info("Đã khởi tạo VPN Manager")
    except Exception as e:
        logger.warning(f"Không thể khởi tạo VPN Manager: {e}")
    
    # Kết nối đến thiết bị trong background task
    def connect_to_mikrotik():
        # Kết nối monitor chính
        api = mikrotik_monitor.connect()
        if api:
            mikrotik_monitor.start_monitoring(interval=2)
        else:
            logger.error("Không thể kết nối đến thiết bị MikroTik")
            return
            
        # Kết nối các module khác
        if client_monitor:
            client_monitor.connect()
            
        if firewall_manager:
            firewall_manager.connect()
            
        if capsman_manager:
            capsman_manager.connect()
            
        if backup_manager:
            backup_manager.connect()
            
        if vpn_manager:
            vpn_manager.connect()
    
    # Chạy kết nối trong một thread riêng
    connect_thread = threading.Thread(target=connect_to_mikrotik)
    connect_thread.daemon = True
    connect_thread.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Sự kiện khi ứng dụng tắt."""
    global mikrotik_monitor, client_monitor, firewall_manager, capsman_manager, backup_manager, vpn_manager
    
    # Ngắt kết nối các module
    if mikrotik_monitor:
        mikrotik_monitor.stop_monitoring()
        mikrotik_monitor.disconnect()
        logger.info("Đã ngắt kết nối Web Monitor")
        
    if client_monitor:
        client_monitor.disconnect()
        logger.info("Đã ngắt kết nối Client Monitor")
        
    if firewall_manager:
        firewall_manager.disconnect()
        logger.info("Đã ngắt kết nối Firewall Manager")
        
    if capsman_manager:
        capsman_manager.disconnect()
        logger.info("Đã ngắt kết nối CAPsMAN Manager")
        
    if backup_manager:
        backup_manager.disconnect()
        logger.info("Đã ngắt kết nối Backup Manager")
        
    if vpn_manager:
        vpn_manager.disconnect()
        logger.info("Đã ngắt kết nối VPN Manager")
        
    logger.info("Đã ngắt kết nối từ thiết bị MikroTik")


# API Endpoints cho VPN
@app.get("/api/vpn/overview")
async def get_vpn_overview():
    """API endpoint để lấy tổng quan về VPN."""
    if not vpn_manager:
        return JSONResponse(content={"error": "VPN Manager chưa được khởi tạo"}, status_code=500)
    
    try:
        # Lấy thông tin từ các hàm khác nhau
        ipsec_peers = vpn_manager.get_ipsec_peers()
        ipsec_policies = vpn_manager.get_ipsec_policies()
        ovpn_servers = vpn_manager.get_ovpn_servers()
        ovpn_clients = vpn_manager.get_ovpn_clients()
        l2tp_servers = vpn_manager.get_l2tp_servers()
        l2tp_clients = vpn_manager.get_l2tp_clients()
        ppp_users = vpn_manager.get_ppp_secrets()
        active_connections = vpn_manager.get_active_connections()
        
        # Tạo đối tượng phản hồi
        response = {
            "ipsec": {
                "peers_count": len(ipsec_peers) if ipsec_peers else 0,
                "policies_count": len(ipsec_policies) if ipsec_policies else 0,
                "peers": ipsec_peers,
                "policies": ipsec_policies
            },
            "openvpn": {
                "servers_count": len(ovpn_servers) if ovpn_servers else 0,
                "clients_count": len(ovpn_clients) if ovpn_clients else 0,
                "servers": ovpn_servers,
                "clients": ovpn_clients
            },
            "l2tp": {
                "servers": l2tp_servers,
                "clients_count": len(l2tp_clients) if l2tp_clients else 0,
                "clients": l2tp_clients
            },
            "users": {
                "count": len(ppp_users) if ppp_users else 0,
                "data": ppp_users
            },
            "active_connections": {
                "count": len(active_connections) if active_connections else 0,
                "data": active_connections
            }
        }
        
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin VPN: {e}")
        return JSONResponse(content={"error": f"Lỗi khi lấy thông tin VPN: {e}"}, status_code=500)

@app.get("/api/vpn/ipsec/peers")
async def get_vpn_ipsec_peers():
    """API endpoint để lấy danh sách IPSec peers."""
    if not vpn_manager:
        return JSONResponse(content={"error": "VPN Manager chưa được khởi tạo"}, status_code=500)
    
    try:
        peers = vpn_manager.get_ipsec_peers()
        return JSONResponse(content=peers)
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách IPSec peers: {e}")
        return JSONResponse(content={"error": f"Lỗi khi lấy danh sách IPSec peers: {e}"}, status_code=500)

@app.get("/api/vpn/ovpn/servers")
async def get_vpn_ovpn_servers():
    """API endpoint để lấy danh sách OpenVPN servers."""
    if not vpn_manager:
        return JSONResponse(content={"error": "VPN Manager chưa được khởi tạo"}, status_code=500)
    
    try:
        servers = vpn_manager.get_ovpn_servers()
        return JSONResponse(content=servers)
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách OpenVPN servers: {e}")
        return JSONResponse(content={"error": f"Lỗi khi lấy danh sách OpenVPN servers: {e}"}, status_code=500)

@app.get("/api/vpn/ppp/users")
async def get_vpn_ppp_users():
    """API endpoint để lấy danh sách PPP users."""
    if not vpn_manager:
        return JSONResponse(content={"error": "VPN Manager chưa được khởi tạo"}, status_code=500)
    
    try:
        users = vpn_manager.get_ppp_secrets()
        return JSONResponse(content=users)
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách PPP users: {e}")
        return JSONResponse(content={"error": f"Lỗi khi lấy danh sách PPP users: {e}"}, status_code=500)

@app.get("/api/vpn/active-connections")
async def get_vpn_active_connections():
    """API endpoint để lấy danh sách các kết nối VPN đang hoạt động."""
    if not vpn_manager:
        return JSONResponse(content={"error": "VPN Manager chưa được khởi tạo"}, status_code=500)
    
    try:
        connections = vpn_manager.get_active_connections()
        return JSONResponse(content=connections)
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách kết nối VPN đang hoạt động: {e}")
        return JSONResponse(content={"error": f"Lỗi khi lấy danh sách kết nối VPN đang hoạt động: {e}"}, status_code=500)

@app.post("/api/vpn/add-user")
async def add_vpn_user(
    name: str = Form(...),
    password: str = Form(...),
    profile: str = Form(None),
    service: str = Form("any"),
    local_address: str = Form(None),
    remote_address: str = Form(None),
    comment: str = Form(None)
):
    """API endpoint để thêm PPP user."""
    if not vpn_manager:
        return JSONResponse(content={"error": "VPN Manager chưa được khởi tạo"}, status_code=500)
    
    try:
        vpn_manager.add_ppp_user(
            name=name,
            password=password,
            profile=profile,
            service=service,
            local_address=local_address,
            remote_address=remote_address,
            comment=comment
        )
        
        return JSONResponse(content={"success": True, "message": f"Đã thêm PPP user {name}"})
    except Exception as e:
        logger.error(f"Lỗi khi thêm PPP user: {e}")
        return JSONResponse(content={"error": f"Lỗi khi thêm PPP user: {e}"}, status_code=500)

@app.post("/api/vpn/remove-user")
async def remove_vpn_user(name: str = Form(...)):
    """API endpoint để xóa PPP user."""
    if not vpn_manager:
        return JSONResponse(content={"error": "VPN Manager chưa được khởi tạo"}, status_code=500)
    
    try:
        vpn_manager.remove_ppp_user(name=name)
        return JSONResponse(content={"success": True, "message": f"Đã xóa PPP user {name}"})
    except Exception as e:
        logger.error(f"Lỗi khi xóa PPP user: {e}")
        return JSONResponse(content={"error": f"Lỗi khi xóa PPP user: {e}"}, status_code=500)

@app.post("/api/vpn/disconnect")
async def disconnect_vpn_connection(id: str = Form(...)):
    """API endpoint để ngắt kết nối VPN đang hoạt động."""
    if not vpn_manager:
        return JSONResponse(content={"error": "VPN Manager chưa được khởi tạo"}, status_code=500)
    
    try:
        vpn_manager.disconnect_active_connection(id=id)
        return JSONResponse(content={"success": True, "message": f"Đã ngắt kết nối VPN có ID {id}"})
    except Exception as e:
        logger.error(f"Lỗi khi ngắt kết nối VPN: {e}")
        return JSONResponse(content={"error": f"Lỗi khi ngắt kết nối VPN: {e}"}, status_code=500)

@app.post("/api/vpn/setup-ipsec-site")
async def setup_ipsec_site(
    remote_gateway: str = Form(...),
    local_subnet: str = Form(...),
    remote_subnet: str = Form(...),
    shared_key: str = Form(...),
    local_gateway: str = Form(None)
):
    """API endpoint để thiết lập IPSec site-to-site."""
    if not vpn_manager:
        return JSONResponse(content={"error": "VPN Manager chưa được khởi tạo"}, status_code=500)
    
    try:
        vpn_manager.setup_ipsec_site_to_site(
            remote_gateway=remote_gateway,
            local_subnet=local_subnet,
            remote_subnet=remote_subnet,
            shared_key=shared_key,
            local_gateway=local_gateway
        )
        
        return JSONResponse(content={
            "success": True, 
            "message": f"Đã thiết lập IPSec site-to-site VPN đến {remote_gateway}"
        })
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập IPSec site-to-site: {e}")
        return JSONResponse(content={"error": f"Lỗi khi thiết lập IPSec site-to-site: {e}"}, status_code=500)

@app.post("/api/vpn/setup-ovpn-server")
async def setup_ovpn_server(
    name: str = Form(...),
    port: int = Form(1194),
    certificate: str = Form(None),
    auth: str = Form(None),
    cipher: str = Form(None)
):
    """API endpoint để thiết lập OpenVPN server."""
    if not vpn_manager:
        return JSONResponse(content={"error": "VPN Manager chưa được khởi tạo"}, status_code=500)
    
    try:
        vpn_manager.setup_ovpn_server(
            name=name,
            port=port,
            certificate=certificate,
            auth=auth,
            cipher=cipher
        )
        
        return JSONResponse(content={
            "success": True, 
            "message": f"Đã thiết lập OpenVPN server {name} trên cổng {port}"
        })
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập OpenVPN server: {e}")
        return JSONResponse(content={"error": f"Lỗi khi thiết lập OpenVPN server: {e}"}, status_code=500)


def main():
    """Hàm chính để chạy ứng dụng."""
    parser = argparse.ArgumentParser(description='MikroTik Web Monitor')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind (default: 5000)')
    args = parser.parse_args()
    
    print(f"=== MikroTik Web Monitor ===")
    print(f"Server đang chạy tại http://{args.host}:{args.port}")
    
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    import argparse
    main()