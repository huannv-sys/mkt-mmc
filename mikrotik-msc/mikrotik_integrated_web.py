
#!/usr/bin/env python3
"""
MikroTik Integrated Web Manager
Ứng dụng web tích hợp tất cả tính năng quản lý MikroTik theo thời gian thực
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
logger = logging.getLogger("mikrotik_integrated_web")

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
    from mikrotik_site_manager import SiteManager
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
app = FastAPI(title="MikroTik Integrated Web Manager")

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

# Thiết lập thư mục templates
templates = Jinja2Templates(directory="templates")

# Thiết lập thư mục static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Tạo thư mục templates và static nếu chưa tồn tại
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)

# Biến globals
site_manager = None    # Site Manager
current_site = None    # Site hiện tại
mikrotik_monitor = None  # Monitor chính
client_monitor = None    # Client Monitor
firewall_manager = None  # Firewall Manager
capsman_manager = None   # CAPsMAN Manager
backup_manager = None    # Backup Manager
vpn_manager = None       # VPN Manager

# Trang HTML Dashboard
@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Trả về trang dashboard chính."""
    return templates.TemplateResponse("index.html", {"request": request})

# Trang HTML cho client
@app.get("/monitor", response_class=HTMLResponse)
async def get_monitor_page(request: Request):
    """Trả về trang monitor."""
    return templates.TemplateResponse("monitor.html", {"request": request})

# Trang quản lý client
@app.get("/clients", response_class=HTMLResponse)
async def get_clients_page(request: Request):
    """Trả về trang quản lý client."""
    return templates.TemplateResponse("clients.html", {"request": request})

# Trang quản lý firewall
@app.get("/firewall", response_class=HTMLResponse)
async def get_firewall_page(request: Request):
    """Trả về trang quản lý firewall."""
    return templates.TemplateResponse("firewall.html", {"request": request})

# Trang quản lý CAPsMAN
@app.get("/capsman", response_class=HTMLResponse)
async def get_capsman_page(request: Request):
    """Trả về trang quản lý CAPsMAN."""
    return templates.TemplateResponse("capsman.html", {"request": request})

# Trang quản lý backup
@app.get("/backup", response_class=HTMLResponse)
async def get_backup_page(request: Request):
    """Trả về trang quản lý backup."""
    return templates.TemplateResponse("backup.html", {"request": request})

# Trang quản lý VPN
@app.get("/vpn", response_class=HTMLResponse)
async def get_vpn_page(request: Request):
    """Trả về trang quản lý VPN."""
    return templates.TemplateResponse("vpn.html", {"request": request})

# Trang quản lý site
@app.get("/sites", response_class=HTMLResponse)
async def get_sites_page(request: Request):
    """Trả về trang quản lý site."""
    return templates.TemplateResponse("sites.html", {"request": request})

# Trang cài đặt
@app.get("/settings", response_class=HTMLResponse)
async def get_settings_page(request: Request):
    """Trả về trang cài đặt."""
    return templates.TemplateResponse("settings.html", {"request": request})

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


# API ENDPOINT SITES
@app.get("/api/sites")
async def api_get_sites():
    """API endpoint để lấy danh sách các sites."""
    global site_manager
    
    if not site_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Site Manager"}, status_code=500)
    
    sites = site_manager.get_sites()
    return JSONResponse(content={"sites": sites})

@app.post("/api/sites/add")
async def api_add_site(
    name: str = Form(...),
    host: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    description: str = Form(None)
):
    """API endpoint để thêm site mới."""
    global site_manager
    
    if not site_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Site Manager"}, status_code=500)
    
    result = site_manager.add_site(name, host, username, password, description)
    if result:
        return JSONResponse(content={"success": True, "message": f"Đã thêm site {name}"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể thêm site"}, status_code=500)

@app.post("/api/sites/remove")
async def api_remove_site(name: str = Form(...)):
    """API endpoint để xóa site."""
    global site_manager
    
    if not site_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Site Manager"}, status_code=500)
    
    result = site_manager.remove_site(name)
    if result:
        return JSONResponse(content={"success": True, "message": f"Đã xóa site {name}"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể xóa site"}, status_code=500)

@app.post("/api/sites/connect")
async def api_connect_site(name: str = Form(...)):
    """API endpoint để kết nối đến site."""
    global site_manager, current_site, mikrotik_monitor, client_monitor, firewall_manager, capsman_manager, backup_manager, vpn_manager
    
    if not site_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Site Manager"}, status_code=500)
    
    # Ngắt kết nối site hiện tại nếu có
    if current_site:
        site_manager.disconnect_site(current_site)
        current_site = None
        mikrotik_monitor = None
        client_monitor = None
        firewall_manager = None
        capsman_manager = None
        backup_manager = None
        vpn_manager = None
    
    # Kết nối đến site mới
    result = site_manager.connect_site(name)
    if result:
        current_site = name
        site = site_manager.get_site(name)
        
        # Cập nhật các biến global
        mikrotik_monitor = site.monitor
        client_monitor = site.client_monitor
        firewall_manager = site.firewall_manager
        capsman_manager = site.capsman_manager
        backup_manager = site.backup_manager
        
        return JSONResponse(content={"success": True, "message": f"Đã kết nối đến site {name}"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể kết nối đến site"}, status_code=500)

@app.post("/api/sites/disconnect")
async def api_disconnect_site(name: str = Form(...)):
    """API endpoint để ngắt kết nối khỏi site."""
    global site_manager, current_site, mikrotik_monitor, client_monitor, firewall_manager, capsman_manager, backup_manager, vpn_manager
    
    if not site_manager:
        return JSONResponse(content={"error": "Chưa khởi tạo Site Manager"}, status_code=500)
    
    result = site_manager.disconnect_site(name)
    
    # Nếu đó là site hiện tại, xóa các tham chiếu
    if result and current_site == name:
        current_site = None
        mikrotik_monitor = None
        client_monitor = None
        firewall_manager = None
        capsman_manager = None
        backup_manager = None
        vpn_manager = None
        
    if result:
        return JSONResponse(content={"success": True, "message": f"Đã ngắt kết nối khỏi site {name}"})
    else:
        return JSONResponse(content={"success": False, "message": "Không thể ngắt kết nối khỏi site"}, status_code=500)

# API ENDPOINTS DEVICE INFO
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


@app.on_event("startup")
async def startup_event():
    """Sự kiện khi ứng dụng khởi động."""
    global site_manager, current_site
    
    # Khởi tạo Site Manager
    site_manager = SiteManager()
    logger.info(f"Đã khởi tạo Site Manager")
    
    # Tạo file templates
    create_template_files()


@app.on_event("shutdown")
async def shutdown_event():
    """Sự kiện khi ứng dụng tắt."""
    global site_manager, current_site, mikrotik_monitor
    
    # Ngắt kết nối site hiện tại nếu có
    if current_site:
        site_manager.disconnect_site(current_site)
        logger.info(f"Đã ngắt kết nối từ site {current_site}")
        
    logger.info("Đã ngắt kết nối từ thiết bị MikroTik")


def create_template_files():
    """Tạo các file template mặc định."""
    # Tạo file CSS
    css_content = """
    /* Main CSS */
    :root {
        --primary-color: #0056b3;
        --secondary-color: #005cbf;
        --background-color: #f5f5f5;
        --card-bg-color: white;
        --text-color: #333;
        --border-color: #ddd;
        --success-color: #28a745;
        --warning-color: #ffc107;
        --danger-color: #dc3545;
        --info-color: #17a2b8;
    }

    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 0;
        padding: 0;
        background-color: var(--background-color);
        color: var(--text-color);
    }

    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }

    .sidebar {
        width: 250px;
        position: fixed;
        top: 0;
        left: 0;
        height: 100%;
        background-color: var(--primary-color);
        color: white;
        overflow-y: auto;
        z-index: 100;
    }

    .sidebar-header {
        padding: 20px;
        text-align: center;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    .sidebar-menu {
        padding: 0;
        list-style: none;
    }

    .sidebar-menu li {
        margin: 0;
        padding: 0;
    }

    .sidebar-menu a {
        display: block;
        padding: 15px 20px;
        color: white;
        text-decoration: none;
        transition: background-color 0.3s;
    }

    .sidebar-menu a:hover,
    .sidebar-menu a.active {
        background-color: var(--secondary-color);
    }

    .sidebar-menu i {
        margin-right: 10px;
    }

    .main-content {
        margin-left: 250px;
        padding: 20px;
        transition: margin-left 0.3s;
    }

    .card {
        background-color: var(--card-bg-color);
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        padding: 20px;
        margin-bottom: 20px;
    }

    .card-header {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border-color);
    }

    .btn {
        display: inline-block;
        padding: 8px 16px;
        background-color: var(--primary-color);
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        text-decoration: none;
        font-size: 14px;
        transition: background-color 0.3s;
    }

    .btn:hover {
        background-color: var(--secondary-color);
    }

    .btn-success {
        background-color: var(--success-color);
    }

    .btn-success:hover {
        background-color: #218838;
    }

    .btn-danger {
        background-color: var(--danger-color);
    }

    .btn-danger:hover {
        background-color: #c82333;
    }

    .alert {
        padding: 15px;
        margin-bottom: 20px;
        border-radius: 4px;
    }

    .alert-success {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }

    .alert-danger {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }

    table, th, td {
        border: 1px solid var(--border-color);
    }

    th, td {
        padding: 12px;
        text-align: left;
    }

    th {
        background-color: #f2f2f2;
        font-weight: bold;
    }

    tr:nth-child(even) {
        background-color: #f9f9f9;
    }

    .form-group {
        margin-bottom: 15px;
    }

    .form-group label {
        display: block;
        margin-bottom: 5px;
        font-weight: bold;
    }

    .form-control {
        width: 100%;
        padding: 8px;
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-sizing: border-box;
    }

    .modal {
        display: none;
        position: fixed;
        z-index: 1000;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
    }

    .modal-content {
        background-color: white;
        margin: 10% auto;
        padding: 20px;
        border-radius: 5px;
        max-width: 500px;
        position: relative;
    }

    .close {
        position: absolute;
        right: 20px;
        top: 10px;
        font-size: 24px;
        font-weight: bold;
        cursor: pointer;
    }

    /* Dashboard specific */
    .dashboard-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin-bottom: 20px;
    }

    .dashboard-card {
        background-color: white;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        padding: 20px;
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

    /* Charts */
    .chart-container {
        background-color: white;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        padding: 20px;
        margin-bottom: 20px;
        min-height: 300px;
    }
    """
    
    with open("static/css/style.css", "w") as f:
        f.write(css_content)
    
    # Tạo file JavaScript
    js_content = """
    // Main JavaScript
    document.addEventListener('DOMContentLoaded', function() {
        // Connect WebSocket
        connectWebSocket();
        
        // Initialize any components
        initializeModals();
        
        // Handle forms
        setupFormSubmission();
    });

    // WebSocket Connection
    function connectWebSocket() {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        const socket = new WebSocket(wsUrl);
        
        socket.onopen = function(e) {
            console.log('WebSocket connection established');
            document.getElementById('connection-status').textContent = 'Đã kết nối';
            document.getElementById('connection-status').classList.add('status-connected');
        };
        
        socket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        };
        
        socket.onclose = function(event) {
            console.log('WebSocket connection closed. Reconnecting...');
            document.getElementById('connection-status').textContent = 'Mất kết nối - đang thử lại...';
            document.getElementById('connection-status').classList.remove('status-connected');
            document.getElementById('connection-status').classList.add('status-disconnected');
            setTimeout(connectWebSocket, 3000);
        };
        
        socket.onerror = function(error) {
            console.error('WebSocket error:', error);
            socket.close();
        };
    }

    // Update Dashboard
    function updateDashboard(data) {
        if (!data || !data.device) return;
        
        // Update device info
        if (document.getElementById('device-hostname')) {
            document.getElementById('device-hostname').textContent = data.device.hostname || 'Unknown';
        }
        
        if (document.getElementById('device-model')) {
            document.getElementById('device-model').textContent = data.device.model || 'Unknown';
        }
        
        if (document.getElementById('device-ros')) {
            document.getElementById('device-ros').textContent = data.device.ros_version || 'Unknown';
        }
        
        if (document.getElementById('device-cpu')) {
            document.getElementById('device-cpu').textContent = `${data.device.cpu_load || '0'}%`;
        }
        
        if (document.getElementById('device-ram')) {
            document.getElementById('device-ram').textContent = 
                `${data.device.free_memory || '0'}/${data.device.total_memory || '0'} MB`;
        }
        
        if (document.getElementById('device-uptime')) {
            document.getElementById('device-uptime').textContent = data.device.uptime || 'Unknown';
        }
        
        // Update interfaces table
        updateInterfacesTable(data.interfaces);
        
        // Update charts
        updateTrafficCharts(data.interfaces);
    }

    // Update Interfaces Table
    function updateInterfacesTable(interfaces) {
        if (!interfaces || !document.getElementById('interfaces-table')) return;
        
        const table = document.getElementById('interfaces-table').getElementsByTagName('tbody')[0];
        table.innerHTML = '';
        
        for (const [name, iface] of Object.entries(interfaces)) {
            const row = table.insertRow();
            
            const nameCell = row.insertCell(0);
            nameCell.textContent = name;
            
            const statusCell = row.insertCell(1);
            statusCell.textContent = 'Hoạt động';
            statusCell.className = 'status-active';
            
            const txCell = row.insertCell(2);
            txCell.textContent = `${iface.current.tx_kbps.toFixed(2)} KB/s (${iface.current.tx_mbps.toFixed(2)} MB/s)`;
            
            const rxCell = row.insertCell(3);
            rxCell.textContent = `${iface.current.rx_kbps.toFixed(2)} KB/s (${iface.current.rx_mbps.toFixed(2)} MB/s)`;
        }
    }

    // Update Traffic Charts
    function updateTrafficCharts(interfaces) {
        if (!interfaces) return;
        
        for (const [name, iface] of Object.entries(interfaces)) {
            // Create charts if they don't exist
            if (!window.charts) window.charts = {};
            
            if (!window.charts[name]) {
                createTrafficChart(name);
            }
            
            // Update chart data
            updateTrafficChart(name, iface.history);
        }
    }

    // Create Traffic Chart
    function createTrafficChart(interfaceName) {
        if (!document.getElementById(`chart-${interfaceName}`)) {
            // Create container for the chart
            const chartsContainer = document.querySelector('.traffic-charts');
            if (!chartsContainer) return;
            
            const chartContainer = document.createElement('div');
            chartContainer.className = 'chart-container';
            chartContainer.setAttribute('data-interface', interfaceName);
            
            const chartTitle = document.createElement('h3');
            chartTitle.textContent = `Traffic Interface ${interfaceName}`;
            chartContainer.appendChild(chartTitle);
            
            const canvas = document.createElement('canvas');
            canvas.id = `chart-${interfaceName}`;
            chartContainer.appendChild(canvas);
            
            chartsContainer.appendChild(chartContainer);
        }
        
        // Initialize chart
        const ctx = document.getElementById(`chart-${interfaceName}`).getContext('2d');
        window.charts[interfaceName] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(30).fill(''),
                datasets: [
                    {
                        label: 'TX (KB/s)',
                        data: Array(30).fill(null),
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.1
                    },
                    {
                        label: 'RX (KB/s)',
                        data: Array(30).fill(null),
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
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

    // Update Traffic Chart
    function updateTrafficChart(interfaceName, historyData) {
        if (!window.charts || !window.charts[interfaceName]) return;
        
        const chart = window.charts[interfaceName];
        
        // Prepare new data
        const txData = [];
        const rxData = [];
        const labels = [];
        
        // Get data from history
        for (const point of historyData) {
            txData.push(point.tx_kbps);
            rxData.push(point.rx_kbps);
            
            // Create time label
            const date = new Date(point.timestamp * 1000);
            const timeLabel = `${date.getHours()}:${date.getMinutes()}:${date.getSeconds()}`;
            labels.push(timeLabel);
        }
        
        // Update chart data
        chart.data.labels = labels;
        chart.data.datasets[0].data = txData;
        chart.data.datasets[1].data = rxData;
        
        // Adjust y axis to fit data
        const maxValue = Math.max(...txData, ...rxData);
        chart.options.scales.y.max = maxValue * 1.2; // Add 20% margin on top
        
        chart.update();
    }

    // Initialize Modals
    function initializeModals() {
        const modals = document.querySelectorAll('.modal');
        const modalTriggers = document.querySelectorAll('[data-modal]');
        const closeButtons = document.querySelectorAll('.close');
        
        modalTriggers.forEach(trigger => {
            trigger.addEventListener('click', function() {
                const modalId = this.getAttribute('data-modal');
                document.getElementById(modalId).style.display = 'block';
            });
        });
        
        closeButtons.forEach(button => {
            button.addEventListener('click', function() {
                this.closest('.modal').style.display = 'none';
            });
        });
        
        window.addEventListener('click', function(event) {
            modals.forEach(modal => {
                if (event.target === modal) {
                    modal.style.display = 'none';
                }
            });
        });
    }

    // Setup Form Submission
    function setupFormSubmission() {
        const forms = document.querySelectorAll('form[data-async]');
        
        forms.forEach(form => {
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const url = this.getAttribute('action');
                const method = this.getAttribute('method') || 'POST';
                const formData = new FormData(this);
                
                try {
                    const response = await fetch(url, {
                        method: method,
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showAlert('success', result.message);
                        
                        // Close modal if form is in a modal
                        const modal = this.closest('.modal');
                        if (modal) {
                            modal.style.display = 'none';
                        }
                        
                        // Reload data if needed
                        if (this.hasAttribute('data-reload')) {
                            const reloadTarget = this.getAttribute('data-reload');
                            reloadData(reloadTarget);
                        }
                    } else {
                        showAlert('danger', result.message || 'Đã xảy ra lỗi');
                    }
                } catch (error) {
                    console.error('Error submitting form:', error);
                    showAlert('danger', 'Đã xảy ra lỗi khi gửi form');
                }
            });
        });
    }

    // Show Alert
    function showAlert(type, message) {
        const alertContainer = document.getElementById('alert-container');
        if (!alertContainer) return;
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        
        alertContainer.appendChild(alert);
        
        // Remove alert after 5 seconds
        setTimeout(() => {
            alert.remove();
        }, 5000);
    }

    // Reload Data
    function reloadData(target) {
        switch (target) {
            case 'interfaces':
                fetchInterfaces();
                break;
            case 'clients':
                fetchClients();
                break;
            case 'firewall':
                fetchFirewallRules();
                break;
            case 'backup':
                fetchBackups();
                break;
            case 'sites':
                fetchSites();
                break;
            default:
                console.log('Unknown reload target:', target);
        }
    }

    // Fetch data functions
    async function fetchInterfaces() {
        try {
            const response = await fetch('/api/interfaces');
            const data = await response.json();
            
            // Update interfaces table with new data
            if (document.getElementById('interfaces-full-table')) {
                updateInterfacesFullTable(data);
            }
        } catch (error) {
            console.error('Error fetching interfaces:', error);
        }
    }

    async function fetchClients() {
        try {
            const response = await fetch('/api/clients');
            const data = await response.json();
            
            // Update clients table with new data
            if (document.getElementById('clients-table')) {
                updateClientsTable(data.clients);
            }
        } catch (error) {
            console.error('Error fetching clients:', error);
        }
    }

    // Update full interfaces table
    function updateInterfacesFullTable(interfaces) {
        if (!interfaces || !document.getElementById('interfaces-full-table')) return;
        
        const table = document.getElementById('interfaces-full-table').getElementsByTagName('tbody')[0];
        table.innerHTML = '';
        
        interfaces.forEach(iface => {
            const row = table.insertRow();
            
            // Name
            const nameCell = row.insertCell(0);
            nameCell.textContent = iface.name;
            
            // Type
            const typeCell = row.insertCell(1);
            typeCell.textContent = iface.type;
            
            // Status
            const statusCell = row.insertCell(2);
            statusCell.textContent = iface.status === 'active' ? 'Hoạt động' : 'Không hoạt động';
            statusCell.className = iface.status === 'active' ? 'status-active' : 'status-inactive';
            
            // Actions
            const actionsCell = row.insertCell(3);
            
            const monitorBtn = document.createElement('button');
            monitorBtn.textContent = 'Giám sát';
            monitorBtn.className = 'btn btn-sm btn-primary';
            monitorBtn.onclick = function() {
                // Redirect to monitoring for this interface
                window.location.href = `/monitor?interface=${iface.name}`;
            };
            
            actionsCell.appendChild(monitorBtn);
        });
    }

    // Update clients table
    function updateClientsTable(clients) {
        if (!clients || !document.getElementById('clients-table')) return;
        
        const table = document.getElementById('clients-table').getElementsByTagName('tbody')[0];
        table.innerHTML = '';
        
        clients.forEach(client => {
            const row = table.insertRow();
            
            // MAC
            const macCell = row.insertCell(0);
            macCell.textContent = client.mac_address;
            
            // IP
            const ipCell = row.insertCell(1);
            ipCell.textContent = client.ip_address;
            
            // Hostname
            const hostnameCell = row.insertCell(2);
            hostnameCell.textContent = client.hostname || '-';
            
            // Type
            const typeCell = row.insertCell(3);
            typeCell.textContent = client.type;
            
            // Signal
            const signalCell = row.insertCell(4);
            signalCell.textContent = client.signal || '-';
            
            // Traffic
            const trafficCell = row.insertCell(5);
            if (client.total_bytes) {
                // Format traffic
                let trafficStr = '';
                if (client.total_bytes >= 1024 * 1024 * 1024) {
                    trafficStr = `${(client.total_bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
                } else if (client.total_bytes >= 1024 * 1024) {
                    trafficStr = `${(client.total_bytes / (1024 * 1024)).toFixed(2)} MB`;
                } else if (client.total_bytes >= 1024) {
                    trafficStr = `${(client.total_bytes / 1024).toFixed(2)} KB`;
                } else {
                    trafficStr = `${client.total_bytes} B`;
                }
                trafficCell.textContent = trafficStr;
            } else {
                trafficCell.textContent = '-';
            }
            
            // Actions
            const actionsCell = row.insertCell(6);
            
            // Block/Unblock button
            const blockBtn = document.createElement('button');
            blockBtn.textContent = client.blocked ? 'Unblock' : 'Block';
            blockBtn.className = client.blocked ? 'btn btn-sm btn-success' : 'btn btn-sm btn-danger';
            blockBtn.onclick = async function() {
                try {
                    const formData = new FormData();
                    formData.append('mac', client.mac_address);
                    
                    const url = client.blocked ? '/api/clients/unblock' : '/api/clients/block';
                    
                    const response = await fetch(url, {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showAlert('success', result.message);
                        fetchClients(); // Reload clients data
                    } else {
                        showAlert('danger', result.message || 'Đã xảy ra lỗi');
                    }
                } catch (error) {
                    console.error('Error blocking/unblocking client:', error);
                    showAlert('danger', 'Đã xảy ra lỗi khi block/unblock client');
                }
            };
            
            actionsCell.appendChild(blockBtn);
        });
    }

    // Site management functions
    async function fetchSites() {
        try {
            const response = await fetch('/api/sites');
            const data = await response.json();
            
            // Update sites table with new data
            if (document.getElementById('sites-table')) {
                updateSitesTable(data.sites);
            }
        } catch (error) {
            console.error('Error fetching sites:', error);
        }
    }

    function updateSitesTable(sites) {
        if (!sites || !document.getElementById('sites-table')) return;
        
        const table = document.getElementById('sites-table').getElementsByTagName('tbody')[0];
        table.innerHTML = '';
        
        sites.forEach(site => {
            const row = table.insertRow();
            
            // Name
            const nameCell = row.insertCell(0);
            nameCell.textContent = site.name;
            
            // Host
            const hostCell = row.insertCell(1);
            hostCell.textContent = site.host;
            
            // Description
            const descCell = row.insertCell(2);
            descCell.textContent = site.description || '-';
            
            // Status
            const statusCell = row.insertCell(3);
            statusCell.textContent = site.status === 'online' ? 'Online' : 'Offline';
            statusCell.className = site.status === 'online' ? 'status-active' : 'status-inactive';
            
            // Active
            const activeCell = row.insertCell(4);
            if (site.active) {
                const activeIndicator = document.createElement('span');
                activeIndicator.textContent = '✓';
                activeIndicator.className = 'active-indicator';
                activeCell.appendChild(activeIndicator);
            }
            
            // Actions
            const actionsCell = row.insertCell(5);
            
            if (site.status === 'online') {
                // Disconnect button
                const disconnectBtn = document.createElement('button');
                disconnectBtn.textContent = 'Ngắt kết nối';
                disconnectBtn.className = 'btn btn-sm btn-danger';
                disconnectBtn.onclick = async function() {
                    try {
                        const formData = new FormData();
                        formData.append('name', site.name);
                        
                        const response = await fetch('/api/sites/disconnect', {
                            method: 'POST',
                            body: formData
                        });
                        
                        const result = await response.json();
                        
                        if (result.success) {
                            showAlert('success', result.message);
                            fetchSites(); // Reload sites data
                        } else {
                            showAlert('danger', result.message || 'Đã xảy ra lỗi');
                        }
                    } catch (error) {
                        console.error('Error disconnecting site:', error);
                        showAlert('danger', 'Đã xảy ra lỗi khi ngắt kết nối');
                    }
                };
                
                actionsCell.appendChild(disconnectBtn);
            } else {
                // Connect button
                const connectBtn = document.createElement('button');
                connectBtn.textContent = 'Kết nối';
                connectBtn.className = 'btn btn-sm btn-success';
                connectBtn.onclick = async function() {
                    try {
                        const formData = new FormData();
                        formData.append('name', site.name);
                        
                        const response = await fetch('/api/sites/connect', {
                            method: 'POST',
                            body: formData
                        });
                        
                        const result = await response.json();
                        
                        if (result.success) {
                            showAlert('success', result.message);
                            fetchSites(); // Reload sites data
                        } else {
                            showAlert('danger', result.message || 'Đã xảy ra lỗi');
                        }
                    } catch (error) {
                        console.error('Error connecting to site:', error);
                        showAlert('danger', 'Đã xảy ra lỗi khi kết nối');
                    }
                };
                
                actionsCell.appendChild(connectBtn);
            }
            
            // Remove button
            const removeBtn = document.createElement('button');
            removeBtn.textContent = 'Xóa';
            removeBtn.className = 'btn btn-sm btn-danger';
            removeBtn.style.marginLeft = '5px';
            removeBtn.onclick = async function() {
                if (confirm(`Bạn có chắc muốn xóa site ${site.name}?`)) {
                    try {
                        const formData = new FormData();
                        formData.append('name', site.name);
                        
                        const response = await fetch('/api/sites/remove', {
                            method: 'POST',
                            body: formData
                        });
                        
                        const result = await response.json();
                        
                        if (result.success) {
                            showAlert('success', result.message);
                            fetchSites(); // Reload sites data
                        } else {
                            showAlert('danger', result.message || 'Đã xảy ra lỗi');
                        }
                    } catch (error) {
                        console.error('Error removing site:', error);
                        showAlert('danger', 'Đã xảy ra lỗi khi xóa site');
                    }
                }
            };
            
            actionsCell.appendChild(removeBtn);
        });
    }
    """
    
    with open("static/js/main.js", "w") as f:
        f.write(js_content)
    
    # Tạo các templates HTML cơ bản
    # index.html - trang chính
    index_html = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MikroTik Integrated Manager</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        <link rel="stylesheet" href="/static/css/style.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <div class="sidebar">
            <div class="sidebar-header">
                <h3>MikroTik Manager</h3>
                <p id="connection-status">Đang kết nối...</p>
            </div>
            <ul class="sidebar-menu">
                <li><a href="/" class="active"><i class="fas fa-tachometer-alt"></i> Dashboard</a></li>
                <li><a href="/monitor"><i class="fas fa-chart-line"></i> Giám sát</a></li>
                <li><a href="/clients"><i class="fas fa-users"></i> Clients</a></li>
                <li><a href="/firewall"><i class="fas fa-shield-alt"></i> Firewall</a></li>
                <li><a href="/capsman"><i class="fas fa-wifi"></i> CAPsMAN</a></li>
                <li><a href="/backup"><i class="fas fa-save"></i> Backup</a></li>
                <li><a href="/vpn"><i class="fas fa-lock"></i> VPN</a></li>
                <li><a href="/sites"><i class="fas fa-server"></i> Sites</a></li>
                <li><a href="/settings"><i class="fas fa-cog"></i> Cài đặt</a></li>
            </ul>
        </div>
        
        <div class="main-content">
            <div id="alert-container"></div>
            
            <h1>MikroTik Dashboard</h1>
            
            <div class="card">
                <div class="card-header">Thông tin thiết bị</div>
                <div class="dashboard-grid">
                    <div class="dashboard-card">
                        <div class="dashboard-label">Tên thiết bị</div>
                        <div id="device-hostname" class="dashboard-value">-</div>
                    </div>
                    <div class="dashboard-card">
                        <div class="dashboard-label">Model</div>
                        <div id="device-model" class="dashboard-value">-</div>
                    </div>
                    <div class="dashboard-card">
                        <div class="dashboard-label">RouterOS</div>
                        <div id="device-ros" class="dashboard-value">-</div>
                    </div>
                    <div class="dashboard-card">
                        <div class="dashboard-label">CPU</div>
                        <div id="device-cpu" class="dashboard-value">-</div>
                    </div>
                    <div class="dashboard-card">
                        <div class="dashboard-label">RAM</div>
                        <div id="device-ram" class="dashboard-value">-</div>
                    </div>
                    <div class="dashboard-card">
                        <div class="dashboard-label">Uptime</div>
                        <div id="device-uptime" class="dashboard-value">-</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">Interfaces</div>
                <table id="interfaces-table">
                    <thead>
                        <tr>
                            <th>Interface</th>
                            <th>Trạng thái</th>
                            <th>TX</th>
                            <th>RX</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- Dữ liệu interfaces được thêm ở đây -->
                    </tbody>
                </table>
            </div>
            
            <div class="traffic-charts">
                <!-- Biểu đồ traffic được thêm ở đây -->
            </div>
        </div>
        
        <script src="/static/js/main.js"></script>
    </body>
    </html>
    """
    
    with open("templates/index.html", "w") as f:
        f.write(index_html)
    
    # monitor.html - trang giám sát
    monitor_html = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Giám sát - MikroTik Integrated Manager</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        <link rel="stylesheet" href="/static/css/style.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <div class="sidebar">
            <div class="sidebar-header">
                <h3>MikroTik Manager</h3>
                <p id="connection-status">Đang kết nối...</p>
            </div>
            <ul class="sidebar-menu">
                <li><a href="/"><i class="fas fa-tachometer-alt"></i> Dashboard</a></li>
                <li><a href="/monitor" class="active"><i class="fas fa-chart-line"></i> Giám sát</a></li>
                <li><a href="/clients"><i class="fas fa-users"></i> Clients</a></li>
                <li><a href="/firewall"><i class="fas fa-shield-alt"></i> Firewall</a></li>
                <li><a href="/capsman"><i class="fas fa-wifi"></i> CAPsMAN</a></li>
                <li><a href="/backup"><i class="fas fa-save"></i> Backup</a></li>
                <li><a href="/vpn"><i class="fas fa-lock"></i> VPN</a></li>
                <li><a href="/sites"><i class="fas fa-server"></i> Sites</a></li>
                <li><a href="/settings"><i class="fas fa-cog"></i> Cài đặt</a></li>
            </ul>
        </div>
        
        <div class="main-content">
            <div id="alert-container"></div>
            
            <h1>Giám sát Interface</h1>
            
            <div class="card">
                <div class="card-header">Danh sách Interfaces</div>
                <table id="interfaces-full-table">
                    <thead>
                        <tr>
                            <th>Interface</th>
                            <th>Loại</th>
                            <th>Trạng thái</th>
                            <th>Hành động</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- Dữ liệu interfaces được thêm ở đây -->
                    </tbody>
                </table>
            </div>
            
            <div class="traffic-charts">
                <!-- Biểu đồ traffic được thêm ở đây -->
            </div>
        </div>
        
        <script src="/static/js/main.js"></script>
        <script>
            // Fetch interfaces when page loads
            document.addEventListener('DOMContentLoaded', function() {
                fetchInterfaces();
            });
        </script>
    </body>
    </html>
    """
    
    with open("templates/monitor.html", "w") as f:
        f.write(monitor_html)
    
    # clients.html - trang quản lý client
    clients_html = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Clients - MikroTik Integrated Manager</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        <link rel="stylesheet" href="/static/css/style.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <div class="sidebar">
            <div class="sidebar-header">
                <h3>MikroTik Manager</h3>
                <p id="connection-status">Đang kết nối...</p>
            </div>
            <ul class="sidebar-menu">
                <li><a href="/"><i class="fas fa-tachometer-alt"></i> Dashboard</a></li>
                <li><a href="/monitor"><i class="fas fa-chart-line"></i> Giám sát</a></li>
                <li><a href="/clients" class="active"><i class="fas fa-users"></i> Clients</a></li>
                <li><a href="/firewall"><i class="fas fa-shield-alt"></i> Firewall</a></li>
                <li><a href="/capsman"><i class="fas fa-wifi"></i> CAPsMAN</a></li>
                <li><a href="/backup"><i class="fas fa-save"></i> Backup</a></li>
                <li><a href="/vpn"><i class="fas fa-lock"></i> VPN</a></li>
                <li><a href="/sites"><i class="fas fa-server"></i> Sites</a></li>
                <li><a href="/settings"><i class="fas fa-cog"></i> Cài đặt</a></li>
            </ul>
        </div>
        
        <div class="main-content">
            <div id="alert-container"></div>
            
            <h1>Quản lý Clients</h1>
            
            <div class="card">
                <div class="card-header">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Danh sách Clients</span>
                        <button class="btn" onclick="fetchClients()"><i class="fas fa-sync"></i> Làm mới</button>
                    </div>
                </div>
                <table id="clients-table">
                    <thead>
                        <tr>
                            <th>MAC Address</th>
                            <th>IP Address</th>
                            <th>Hostname</th>
                            <th>Loại</th>
                            <th>Tín hiệu</th>
                            <th>Traffic</th>
                            <th>Hành động</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- Dữ liệu clients được thêm ở đây -->
                    </tbody>
                </table>
            </div>
        </div>
        
        <script src="/static/js/main.js"></script>
        <script>
            // Fetch clients when page loads
            document.addEventListener('DOMContentLoaded', function() {
                fetchClients();
            });
        </script>
    </body>
    </html>
    """
    
    with open("templates/clients.html", "w") as f:
        f.write(clients_html)
    
    # sites.html - trang quản lý site
    sites_html = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sites - MikroTik Integrated Manager</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <div class="sidebar">
            <div class="sidebar-header">
                <h3>MikroTik Manager</h3>
                <p id="connection-status">Đang kết nối...</p>
            </div>
            <ul class="sidebar-menu">
                <li><a href="/"><i class="fas fa-tachometer-alt"></i> Dashboard</a></li>
                <li><a href="/monitor"><i class="fas fa-chart-line"></i> Giám sát</a></li>
                <li><a href="/clients"><i class="fas fa-users"></i> Clients</a></li>
                <li><a href="/firewall"><i class="fas fa-shield-alt"></i> Firewall</a></li>
                <li><a href="/capsman"><i class="fas fa-wifi"></i> CAPsMAN</a></li>
                <li><a href="/backup"><i class="fas fa-save"></i> Backup</a></li>
                <li><a href="/vpn"><i class="fas fa-lock"></i> VPN</a></li>
                <li><a href="/sites" class="active"><i class="fas fa-server"></i> Sites</a></li>
                <li><a href="/settings"><i class="fas fa-cog"></i> Cài đặt</a></li>
            </ul>
        </div>
        
        <div class="main-content">
            <div id="alert-container"></div>
            
            <h1>Quản lý Sites</h1>
            
            <div class="card">
                <div class="card-header">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Danh sách Sites</span>
                        <button class="btn" data-modal="addSiteModal"><i class="fas fa-plus"></i> Thêm Site</button>
                    </div>
                </div>
                <table id="sites-table">
                    <thead>
                        <tr>
                            <th>Tên</th>
                            <th>Host</th>
                            <th>Mô tả</th>
                            <th>Trạng thái</th>
                            <th>Active</th>
                            <th>Hành động</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- Dữ liệu sites được thêm ở đây -->
                    </tbody>
                </table>
            </div>
            
            <!-- Modal thêm site -->
            <div id="addSiteModal" class="modal">
                <div class="modal-content">
                    <span class="close">&times;</span>
                    <h2>Thêm Site Mới</h2>
                    <form id="addSiteForm" action="/api/sites/add" method="POST" data-async data-reload="sites">
                        <div class="form-group">
                            <label for="name">Tên Site:</label>
                            <input type="text" id="name" name="name" class="form-control" required>
                        </div>
                        <div class="form-group">
                            <label for="host">Địa chỉ IP/Hostname:</label>
                            <input type="text" id="host" name="host" class="form-control" required>
                        </div>
                        <div class="form-group">
                            <label for="username">Tên đăng nhập:</label>
                            <input type="text" id="username" name="username" class="form-control" required>
                        </div>
                        <div class="form-group">
                            <label for="password">Mật khẩu:</label>
                            <input type="password" id="password" name="password" class="form-control" required>
                        </div>
                        <div class="form-group">
                            <label for="description">Mô tả:</label>
                            <input type="text" id="description" name="description" class="form-control">
                        </div>
                        <button type="submit" class="btn btn-success">Thêm Site</button>
                    </form>
                </div>
            </div>
        </div>
        
        <script src="/static/js/main.js"></script>
        <script>
            // Fetch sites when page loads
            document.addEventListener('DOMContentLoaded', function() {
                fetchSites();
            });
        </script>
    </body>
    </html>
    """
    
    with open("templates/sites.html", "w") as f:
        f.write(sites_html)
    
    # Tạo các template cơ bản cho các trang khác
    firewall_html = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Firewall - MikroTik Integrated Manager</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <div class="sidebar">
            <div class="sidebar-header">
                <h3>MikroTik Manager</h3>
                <p id="connection-status">Đang kết nối...</p>
            </div>
            <ul class="sidebar-menu">
                <li><a href="/"><i class="fas fa-tachometer-alt"></i> Dashboard</a></li>
                <li><a href="/monitor"><i class="fas fa-chart-line"></i> Giám sát</a></li>
                <li><a href="/clients"><i class="fas fa-users"></i> Clients</a></li>
                <li><a href="/firewall" class="active"><i class="fas fa-shield-alt"></i> Firewall</a></li>
                <li><a href="/capsman"><i class="fas fa-wifi"></i> CAPsMAN</a></li>
                <li><a href="/backup"><i class="fas fa-save"></i> Backup</a></li>
                <li><a href="/vpn"><i class="fas fa-lock"></i> VPN</a></li>
                <li><a href="/sites"><i class="fas fa-server"></i> Sites</a></li>
                <li><a href="/settings"><i class="fas fa-cog"></i> Cài đặt</a></li>
            </ul>
        </div>
        
        <div class="main-content">
            <div id="alert-container"></div>
            
            <h1>Quản lý Firewall</h1>
            
            <div class="card">
                <p>Tính năng Firewall đang được phát triển</p>
            </div>
        </div>
        
        <script src="/static/js/main.js"></script>
    </body>
    </html>
    """
    
    with open("templates/firewall.html", "w") as f:
        f.write(firewall_html)
    
    capsman_html = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CAPsMAN - MikroTik Integrated Manager</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <div class="sidebar">
            <div class="sidebar-header">
                <h3>MikroTik Manager</h3>
                <p id="connection-status">Đang kết nối...</p>
            </div>
            <ul class="sidebar-menu">
                <li><a href="/"><i class="fas fa-tachometer-alt"></i> Dashboard</a></li>
                <li><a href="/monitor"><i class="fas fa-chart-line"></i> Giám sát</a></li>
                <li><a href="/clients"><i class="fas fa-users"></i> Clients</a></li>
                <li><a href="/firewall"><i class="fas fa-shield-alt"></i> Firewall</a></li>
                <li><a href="/capsman" class="active"><i class="fas fa-wifi"></i> CAPsMAN</a></li>
                <li><a href="/backup"><i class="fas fa-save"></i> Backup</a></li>
                <li><a href="/vpn"><i class="fas fa-lock"></i> VPN</a></li>
                <li><a href="/sites"><i class="fas fa-server"></i> Sites</a></li>
                <li><a href="/settings"><i class="fas fa-cog"></i> Cài đặt</a></li>
            </ul>
        </div>
        
        <div class="main-content">
            <div id="alert-container"></div>
            
            <h1>Quản lý CAPsMAN</h1>
            
            <div class="card">
                <p>Tính năng CAPsMAN đang được phát triển</p>
            </div>
        </div>
        
        <script src="/static/js/main.js"></script>
    </body>
    </html>
    """
    
    with open("templates/capsman.html", "w") as f:
        f.write(capsman_html)
    
    backup_html = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Backup - MikroTik Integrated Manager</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <div class="sidebar">
            <div class="sidebar-header">
                <h3>MikroTik Manager</h3>
                <p id="connection-status">Đang kết nối...</p>
            </div>
            <ul class="sidebar-menu">
                <li><a href="/"><i class="fas fa-tachometer-alt"></i> Dashboard</a></li>
                <li><a href="/monitor"><i class="fas fa-chart-line"></i> Giám sát</a></li>
                <li><a href="/clients"><i class="fas fa-users"></i> Clients</a></li>
                <li><a href="/firewall"><i class="fas fa-shield-alt"></i> Firewall</a></li>
                <li><a href="/capsman"><i class="fas fa-wifi"></i> CAPsMAN</a></li>
                <li><a href="/backup" class="active"><i class="fas fa-save"></i> Backup</a></li>
                <li><a href="/vpn"><i class="fas fa-lock"></i> VPN</a></li>
                <li><a href="/sites"><i class="fas fa-server"></i> Sites</a></li>
                <li><a href="/settings"><i class="fas fa-cog"></i> Cài đặt</a></li>
            </ul>
        </div>
        
        <div class="main-content">
            <div id="alert-container"></div>
            
            <h1>Quản lý Backup</h1>
            
            <div class="card">
                <p>Tính năng Backup đang được phát triển</p>
            </div>
        </div>
        
        <script src="/static/js/main.js"></script>
    </body>
    </html>
    """
    
    with open("templates/backup.html", "w") as f:
        f.write(backup_html)
    
    vpn_html = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VPN - MikroTik Integrated Manager</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <div class="sidebar">
            <div class="sidebar-header">
                <h3>MikroTik Manager</h3>
                <p id="connection-status">Đang kết nối...</p>
            </div>
            <ul class="sidebar-menu">
                <li><a href="/"><i class="fas fa-tachometer-alt"></i> Dashboard</a></li>
                <li><a href="/monitor"><i class="fas fa-chart-line"></i> Giám sát</a></li>
                <li><a href="/clients"><i class="fas fa-users"></i> Clients</a></li>
                <li><a href="/firewall"><i class="fas fa-shield-alt"></i> Firewall</a></li>
                <li><a href="/capsman"><i class="fas fa-wifi"></i> CAPsMAN</a></li>
                <li><a href="/backup"><i class="fas fa-save"></i> Backup</a></li>
                <li><a href="/vpn" class="active"><i class="fas fa-lock"></i> VPN</a></li>
                <li><a href="/sites"><i class="fas fa-server"></i> Sites</a></li>
                <li><a href="/settings"><i class="fas fa-cog"></i> Cài đặt</a></li>
            </ul>
        </div>
        
        <div class="main-content">
            <div id="alert-container"></div>
            
            <h1>Quản lý VPN</h1>
            
            <div class="card">
                <p>Tính năng VPN đang được phát triển</p>
            </div>
        </div>
        
        <script src="/static/js/main.js"></script>
    </body>
    </html>
    """
    
    with open("templates/vpn.html", "w") as f:
        f.write(vpn_html)
    
    settings_html = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cài đặt - MikroTik Integrated Manager</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <div class="sidebar">
            <div class="sidebar-header">
                <h3>MikroTik Manager</h3>
                <p id="connection-status">Đang kết nối...</p>
            </div>
            <ul class="sidebar-menu">
                <li><a href="/"><i class="fas fa-tachometer-alt"></i> Dashboard</a></li>
                <li><a href="/monitor"><i class="fas fa-chart-line"></i> Giám sát</a></li>
                <li><a href="/clients"><i class="fas fa-users"></i> Clients</a></li>
                <li><a href="/firewall"><i class="fas fa-shield-alt"></i> Firewall</a></li>
                <li><a href="/capsman"><i class="fas fa-wifi"></i> CAPsMAN</a></li>
                <li><a href="/backup"><i class="fas fa-save"></i> Backup</a></li>
                <li><a href="/vpn"><i class="fas fa-lock"></i> VPN</a></li>
                <li><a href="/sites"><i class="fas fa-server"></i> Sites</a></li>
                <li><a href="/settings" class="active"><i class="fas fa-cog"></i> Cài đặt</a></li>
            </ul>
        </div>
        
        <div class="main-content">
            <div id="alert-container"></div>
            
            <h1>Cài đặt</h1>
            
            <div class="card">
                <div class="card-header">Thông tin phiên bản</div>
                <p>MikroTik Integrated Web Manager</p>
                <p>Phiên bản: 1.0.0</p>
                <p>© 2023 - Tất cả các quyền được bảo lưu</p>
            </div>
        </div>
        
        <script src="/static/js/main.js"></script>
    </body>
    </html>
    """
    
    with open("templates/settings.html", "w") as f:
        f.write(settings_html)


def main():
    """Hàm chính để chạy ứng dụng."""
    parser = argparse.ArgumentParser(description='MikroTik Integrated Web Manager')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind (default: 5000)')
    args = parser.parse_args()
    
    print(f"=== MikroTik Integrated Web Manager ===")
    print(f"Server đang chạy tại http://{args.host}:{args.port}")
    
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    import argparse
    main()
