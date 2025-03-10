"""
Module kết nối với MikroTik API
"""

import ssl
import socket
import hashlib
import binascii
import logging
import time
import config

class MikroTikAPI:
    """Lớp kết nối và tương tác với MikroTik API"""
    
    def __init__(self, host, username, password, port=None, use_ssl=False, timeout=10):
        """Khởi tạo kết nối MikroTik API"""
        self.host = host
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.port = port or (config.MIKROTIK_API_SSL_PORT if use_ssl else config.MIKROTIK_API_PORT)
        self.timeout = timeout
        self.sock = None
        self.connected = False
        self.logger = logging.getLogger('mikrotik_api')
    
    def connect(self):
        """Kết nối đến MikroTik API"""
        try:
            # Tạo socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            
            # Sử dụng SSL nếu được yêu cầu
            if self.use_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                self.sock = ssl_context.wrap_socket(self.sock)
            
            # Kết nối đến thiết bị MikroTik
            self.sock.connect((self.host, self.port))
            
            # Đăng nhập
            self._login()
            self.connected = True
            self.logger.info(f"Đã kết nối thành công đến MikroTik tại {self.host}:{self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi kết nối đến MikroTik: {str(e)}")
            self.sock = None
            self.connected = False
            return False
    
    def disconnect(self):
        """Ngắt kết nối khỏi MikroTik API"""
        if self.sock:
            self.sock.close()
            self.sock = None
            self.connected = False
            self.logger.info(f"Đã ngắt kết nối khỏi MikroTik tại {self.host}")
    
    def _login(self):
        """Đăng nhập vào MikroTik API"""
        # Gửi lệnh đăng nhập trống
        self._send_word('/login')
        self._send_word('')
        
        # Nhận challenge từ server
        response = self._get_response()
        if 'ret' not in response or len(response['ret']) != 1:
            raise ValueError("Không nhận được challenge từ server")
        
        challenge = binascii.unhexlify(response['ret'][0])
        
        # Mã hóa mật khẩu với challenge
        md5 = hashlib.md5()
        md5.update(b'\x00')
        md5.update(self.password.encode('utf-8'))
        md5.update(challenge)
        password_hash = binascii.hexlify(md5.digest())
        
        # Gửi tên đăng nhập và mật khẩu đã mã hóa
        self._send_word('/login')
        self._send_word(f'=name={self.username}')
        self._send_word(f'=password={password_hash.decode("utf-8")}')
        self._send_word('')
        
        # Kiểm tra kết quả đăng nhập
        response = self._get_response()
        if 'ret' in response:
            raise ValueError("Đăng nhập thất bại: Tên đăng nhập hoặc mật khẩu không chính xác")
    
    def _send_word(self, word):
        """Gửi một từ đến MikroTik API"""
        if not self.sock:
            raise ValueError("Chưa kết nối đến MikroTik API")
        
        # Mã hóa độ dài từ
        length = len(word)
        if length < 0x80:
            self.sock.send(length.to_bytes(1, byteorder='little'))
        elif length < 0x4000:
            length |= 0x8000
            self.sock.send(length.to_bytes(2, byteorder='little'))
        elif length < 0x200000:
            length |= 0xC00000
            self.sock.send(length.to_bytes(3, byteorder='little'))
        elif length < 0x10000000:
            length |= 0xE0000000
            self.sock.send(length.to_bytes(4, byteorder='little'))
        else:
            self.sock.send(b'\xF0')
            self.sock.send(length.to_bytes(4, byteorder='little'))
        
        # Gửi từ
        self.sock.send(word.encode('utf-8'))
    
    def _read_word(self):
        """Đọc một từ từ MikroTik API"""
        if not self.sock:
            raise ValueError("Chưa kết nối đến MikroTik API")
        
        # Đọc byte đầu tiên để xác định độ dài
        first_byte = self.sock.recv(1)
        if not first_byte:
            return ''
        
        first_byte = first_byte[0]
        if first_byte < 0x80:
            length = first_byte
        elif first_byte < 0xC0:
            second_byte = self.sock.recv(1)[0]
            length = ((first_byte & 0x3F) << 8) + second_byte
        elif first_byte < 0xE0:
            length_bytes = self.sock.recv(2)
            length = ((first_byte & 0x1F) << 16) + (length_bytes[0] << 8) + length_bytes[1]
        elif first_byte < 0xF0:
            length_bytes = self.sock.recv(3)
            length = ((first_byte & 0x0F) << 24) + (length_bytes[0] << 16) + (length_bytes[1] << 8) + length_bytes[2]
        else:
            length_bytes = self.sock.recv(4)
            length = (length_bytes[0] << 24) + (length_bytes[1] << 16) + (length_bytes[2] << 8) + length_bytes[3]
        
        # Nếu độ dài là 0, trả về chuỗi rỗng
        if length == 0:
            return ''
        
        # Đọc từ
        word = b''
        while len(word) < length:
            chunk = self.sock.recv(length - len(word))
            if not chunk:
                break
            word += chunk
        
        return word.decode('utf-8')
    
    def _get_response(self):
        """Nhận phản hồi từ MikroTik API"""
        response = {'re': [], 'ret': [], 'trap': [], 'done': False}
        
        # Đọc các từ cho đến khi nhận được !done
        while True:
            word = self._read_word()
            
            # Nếu từ rỗng, tiếp tục
            if not word:
                continue
            
            # Kiểm tra loại từ
            if word.startswith('!re'):
                response['re'].append({})
                attrs = response['re'][-1]
            elif word.startswith('!trap'):
                response['trap'].append({})
                attrs = response['trap'][-1]
            elif word.startswith('!done'):
                response['done'] = True
                attrs = {}
            else:
                # Nếu từ này là giá trị cần lưu
                if '=' in word:
                    key, value = word.split('=', 1)
                    if key.startswith('='):
                        key = key[1:]
                        if response['done']:
                            response[key] = value
                        else:
                            attrs[key] = value
            
            # Nếu đã nhận được !done, dừng vòng lặp
            if response['done']:
                break
        
        return response
    
    def execute_command(self, command, params=None):
        """Thực thi một lệnh MikroTik API"""
        if not self.connected:
            if not self.connect():
                raise ValueError("Không thể kết nối đến MikroTik API")
        
        try:
            # Gửi lệnh
            self._send_word(command)
            
            # Gửi các tham số
            if params:
                for key, value in params.items():
                    self._send_word(f'={key}={value}')
            
            # Kết thúc lệnh
            self._send_word('')
            
            # Nhận phản hồi
            response = self._get_response()
            
            # Kiểm tra lỗi
            if response['trap']:
                trap = response['trap'][0]
                error_message = trap.get('message', 'Unknown error')
                self.logger.error(f"Lỗi khi thực thi lệnh '{command}': {error_message}")
                raise ValueError(f"MikroTik API error: {error_message}")
            
            return response
        except Exception as e:
            self.logger.error(f"Lỗi khi thực thi lệnh '{command}': {str(e)}")
            # Thử kết nối lại nếu lỗi socket
            if isinstance(e, (socket.error, socket.timeout, OSError)):
                self.connected = False
                self.sock = None
            raise
    
    def get_device_info(self):
        """Lấy thông tin cơ bản về thiết bị"""
        try:
            # Lấy thông tin hệ thống
            system_response = self.execute_command('/system/resource/print')
            system_info = system_response['re'][0] if system_response['re'] else {}
            
            # Lấy thông tin thiết bị
            identity_response = self.execute_command('/system/identity/print')
            identity_info = identity_response['re'][0] if identity_response['re'] else {}
            
            # Lấy thông tin phiên bản
            version_response = self.execute_command('/system/package/update/print')
            version_info = version_response['re'][0] if version_response['re'] else {}
            
            # Tổng hợp thông tin
            device_info = {
                'identity': identity_info.get('name', 'Unknown'),
                'model': system_info.get('board-name', 'Unknown'),
                'serial_number': system_info.get('serial-number', 'Unknown'),
                'version': system_info.get('version', 'Unknown'),
                'uptime': system_info.get('uptime', 'Unknown'),
                'cpu_load': system_info.get('cpu-load', '0'),
                'total_memory': int(system_info.get('total-memory', 0)),
                'free_memory': int(system_info.get('free-memory', 0)),
                'total_hdd_space': int(system_info.get('total-hdd-space', 0)),
                'free_hdd_space': int(system_info.get('free-hdd-space', 0)),
                'architecture': system_info.get('architecture-name', 'Unknown'),
                'board': system_info.get('board-name', 'Unknown'),
                'current_channel': version_info.get('channel', 'Unknown')
            }
            
            return device_info
        except Exception as e:
            self.logger.error(f"Lỗi khi lấy thông tin thiết bị: {str(e)}")
            return {'error': str(e)}
    
    def get_interfaces(self):
        """Lấy danh sách interfaces"""
        try:
            # Lấy danh sách interfaces
            interfaces_response = self.execute_command('/interface/print')
            interfaces = []
            
            for interface_data in interfaces_response.get('re', []):
                # Lấy thông tin cơ bản
                interface = {
                    'name': interface_data.get('name', 'Unknown'),
                    'type': interface_data.get('type', 'Unknown'),
                    'mac_address': interface_data.get('mac-address', 'Unknown'),
                    'mtu': interface_data.get('mtu', '1500'),
                    'actual_mtu': interface_data.get('actual-mtu', '1500'),
                    'running': interface_data.get('running', 'false') == 'true',
                    'disabled': interface_data.get('disabled', 'false') == 'true',
                    'comment': interface_data.get('comment', '')
                }
                
                # Thêm vào danh sách
                interfaces.append(interface)
            
            # Lấy thông tin traffic cho các interfaces
            traffic_response = self.execute_command('/interface/monitor-traffic', {
                'interface': 'all',
                'once': 'yes'
            })
            
            # Cập nhật thông tin traffic
            for traffic_data in traffic_response.get('re', []):
                if 'name' in traffic_data:
                    interface_name = traffic_data['name']
                    for interface in interfaces:
                        if interface['name'] == interface_name:
                            interface['rx_byte'] = traffic_data.get('rx-byte', '0')
                            interface['tx_byte'] = traffic_data.get('tx-byte', '0')
                            interface['rx_packet'] = traffic_data.get('rx-packet', '0')
                            interface['tx_packet'] = traffic_data.get('tx-packet', '0')
                            break
            
            return interfaces
        except Exception as e:
            self.logger.error(f"Lỗi khi lấy danh sách interfaces: {str(e)}")
            return []
    
    def get_clients(self):
        """Lấy danh sách clients kết nối"""
        try:
            clients = []
            
            # Lấy danh sách DHCP leases
            dhcp_response = self.execute_command('/ip/dhcp-server/lease/print')
            
            for lease in dhcp_response.get('re', []):
                client = {
                    'hostname': lease.get('host-name', 'Unknown'),
                    'ip_address': lease.get('address', 'Unknown'),
                    'mac_address': lease.get('mac-address', 'Unknown'),
                    'client_id': lease.get('client-id', ''),
                    'status': 'active' if lease.get('status', '') == 'bound' else 'inactive',
                    'expires': lease.get('expires-after', 'Unknown'),
                    'type': 'dhcp',
                    'comment': lease.get('comment', '')
                }
                clients.append(client)
            
            # Lấy danh sách wireless clients
            wireless_response = self.execute_command('/interface/wireless/registration-table/print')
            
            for client in wireless_response.get('re', []):
                # Tìm thông tin DHCP tương ứng
                mac = client.get('mac-address', '')
                existing_client = next((c for c in clients if c['mac_address'] == mac), None)
                
                if existing_client:
                    # Cập nhật thông tin wireless
                    existing_client['connection_type'] = 'wireless'
                    existing_client['interface'] = client.get('interface', 'Unknown')
                    existing_client['signal_strength'] = client.get('signal-strength', '0')
                    existing_client['tx_rate'] = client.get('tx-rate', '0')
                    existing_client['rx_rate'] = client.get('rx-rate', '0')
                else:
                    # Thêm client mới
                    new_client = {
                        'hostname': 'Unknown',
                        'ip_address': 'Unknown',
                        'mac_address': mac,
                        'status': 'active',
                        'connection_type': 'wireless',
                        'interface': client.get('interface', 'Unknown'),
                        'signal_strength': client.get('signal-strength', '0'),
                        'tx_rate': client.get('tx-rate', '0'),
                        'rx_rate': client.get('rx-rate', '0'),
                        'type': 'wireless'
                    }
                    clients.append(new_client)
            
            # Cập nhật thông tin từ bảng ARP
            arp_response = self.execute_command('/ip/arp/print')
            
            for arp in arp_response.get('re', []):
                mac = arp.get('mac-address', '')
                ip = arp.get('address', '')
                existing_client = next((c for c in clients if c['mac_address'] == mac), None)
                
                if existing_client and existing_client['ip_address'] == 'Unknown':
                    existing_client['ip_address'] = ip
                    existing_client['interface'] = arp.get('interface', 'Unknown')
                elif not existing_client and mac and ip:
                    # Thêm client mới từ bảng ARP
                    new_client = {
                        'hostname': 'Unknown',
                        'ip_address': ip,
                        'mac_address': mac,
                        'status': 'active' if arp.get('complete', 'false') == 'true' else 'inactive',
                        'connection_type': 'wired',
                        'interface': arp.get('interface', 'Unknown'),
                        'type': 'arp'
                    }
                    clients.append(new_client)
            
            # Thêm ID duy nhất cho mỗi client
            for i, client in enumerate(clients):
                client['id'] = f"client{i+1}"
            
            return clients
        except Exception as e:
            self.logger.error(f"Lỗi khi lấy danh sách clients: {str(e)}")
            return []
    
    def get_firewall_rules(self):
        """Lấy danh sách firewall rules"""
        try:
            # Lấy danh sách filter rules
            filter_response = self.execute_command('/ip/firewall/filter/print')
            rules = []
            
            for rule in filter_response.get('re', []):
                # Chuẩn bị rule data
                rule_data = {
                    'id': rule.get('.id', 'Unknown'),
                    'chain': rule.get('chain', 'Unknown'),
                    'action': rule.get('action', 'Unknown'),
                    'protocol': rule.get('protocol', 'any'),
                    'src_address': rule.get('src-address', ''),
                    'dst_address': rule.get('dst-address', ''),
                    'src_port': rule.get('src-port', ''),
                    'dst_port': rule.get('dst-port', ''),
                    'comment': rule.get('comment', ''),
                    'disabled': rule.get('disabled', 'false') == 'true',
                    'type': 'filter'
                }
                
                rules.append(rule_data)
            
            # Lấy danh sách NAT rules
            nat_response = self.execute_command('/ip/firewall/nat/print')
            
            for rule in nat_response.get('re', []):
                # Chuẩn bị rule data
                rule_data = {
                    'id': rule.get('.id', 'Unknown'),
                    'chain': rule.get('chain', 'Unknown'),
                    'action': rule.get('action', 'Unknown'),
                    'protocol': rule.get('protocol', 'any'),
                    'src_address': rule.get('src-address', ''),
                    'dst_address': rule.get('dst-address', ''),
                    'to_addresses': rule.get('to-addresses', ''),
                    'to_ports': rule.get('to-ports', ''),
                    'comment': rule.get('comment', ''),
                    'disabled': rule.get('disabled', 'false') == 'true',
                    'type': 'nat'
                }
                
                rules.append(rule_data)
            
            return rules
        except Exception as e:
            self.logger.error(f"Lỗi khi lấy danh sách firewall rules: {str(e)}")
            return []
    
    def get_ip_addresses(self):
        """Lấy danh sách địa chỉ IP"""
        try:
            # Lấy danh sách địa chỉ IP
            ip_response = self.execute_command('/ip/address/print')
            addresses = []
            
            for addr in ip_response.get('re', []):
                # Chuẩn bị dữ liệu địa chỉ IP
                address_data = {
                    'id': addr.get('.id', 'Unknown'),
                    'address': addr.get('address', 'Unknown'),
                    'network': addr.get('network', ''),
                    'interface': addr.get('interface', 'Unknown'),
                    'type': 'static' if 'dynamic' not in addr else 'dynamic',
                    'status': 'active' if addr.get('disabled', 'false') == 'false' else 'inactive',
                    'comment': addr.get('comment', '')
                }
                
                addresses.append(address_data)
            
            return addresses
        except Exception as e:
            self.logger.error(f"Lỗi khi lấy danh sách địa chỉ IP: {str(e)}")
            return []
    
    def block_client(self, ip_address=None, mac_address=None, comment=None):
        """Block một client"""
        try:
            if not ip_address and not mac_address:
                raise ValueError("Phải cung cấp địa chỉ IP hoặc địa chỉ MAC để block client")
            
            # Tạo comment nếu không được cung cấp
            if not comment:
                comment = f"Blocked by MikroTik MSC on {time.strftime('%Y-%m-%d %H:%M:%S')}"
            
            params = {
                'list': 'blocked',
                'comment': comment
            }
            
            # Thêm vào address list nếu có địa chỉ IP
            if ip_address:
                params['address'] = ip_address
                ip_response = self.execute_command('/ip/firewall/address-list/add', params)
            
            # Block MAC nếu có địa chỉ MAC
            if mac_address:
                # Thêm rule filter theo MAC
                mac_params = {
                    'chain': 'forward',
                    'src-mac-address': mac_address,
                    'action': 'drop',
                    'comment': comment
                }
                mac_response = self.execute_command('/ip/firewall/filter/add', mac_params)
            
            return {'success': True, 'message': 'Client đã bị block thành công'}
        except Exception as e:
            self.logger.error(f"Lỗi khi block client: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def unblock_client(self, ip_address=None, mac_address=None):
        """Unblock một client"""
        try:
            if not ip_address and not mac_address:
                raise ValueError("Phải cung cấp địa chỉ IP hoặc địa chỉ MAC để unblock client")
            
            success = False
            
            # Xóa khỏi address list nếu có địa chỉ IP
            if ip_address:
                # Tìm ID của address list entry
                find_params = {'?address': ip_address, '?list': 'blocked'}
                find_response = self.execute_command('/ip/firewall/address-list/print', find_params)
                
                # Xóa các entry tìm thấy
                for entry in find_response.get('re', []):
                    if '.id' in entry:
                        self.execute_command('/ip/firewall/address-list/remove', {'numbers': entry['.id']})
                        success = True
            
            # Unblock MAC nếu có địa chỉ MAC
            if mac_address:
                # Tìm ID của filter rule
                find_params = {'?src-mac-address': mac_address, '?action': 'drop'}
                find_response = self.execute_command('/ip/firewall/filter/print', find_params)
                
                # Xóa các rule tìm thấy
                for rule in find_response.get('re', []):
                    if '.id' in rule:
                        self.execute_command('/ip/firewall/filter/remove', {'numbers': rule['.id']})
                        success = True
            
            if success:
                return {'success': True, 'message': 'Client đã được unblock thành công'}
            else:
                return {'success': False, 'error': 'Không tìm thấy client trong danh sách bị chặn'}
        except Exception as e:
            self.logger.error(f"Lỗi khi unblock client: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_backup(self, name=None, include_sensitive=False):
        """Tạo file backup"""
        try:
            # Tạo tên file backup nếu không được cung cấp
            if not name:
                current_time = time.strftime('%Y%m%d_%H%M%S')
                name = f"backup_{current_time}"
            
            # Thêm phần mở rộng .backup nếu chưa có
            if not name.endswith('.backup'):
                name += '.backup'
            
            # Tạo backup
            params = {'name': name}
            if include_sensitive:
                params['don-t-encrypt'] = 'yes'
            
            backup_response = self.execute_command('/system/backup/save', params)
            
            # Kiểm tra kết quả
            if backup_response.get('done', False):
                return {'success': True, 'filename': name, 'message': 'Backup đã được tạo thành công'}
            else:
                return {'success': False, 'error': 'Không thể tạo backup'}
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo backup: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_export(self, name=None, compact=False, include_sensitive=False):
        """Xuất cấu hình dạng text"""
        try:
            # Tạo tên file export nếu không được cung cấp
            if not name:
                current_time = time.strftime('%Y%m%d_%H%M%S')
                name = f"export_{current_time}"
            
            # Thêm phần mở rộng .rsc nếu chưa có
            if not name.endswith('.rsc'):
                name += '.rsc'
            
            # Tạo export
            params = {'file': name}
            if compact:
                params['compact'] = 'yes'
            if include_sensitive:
                params['sensitive'] = 'yes'
            
            export_response = self.execute_command('/export', params)
            
            # Kiểm tra kết quả
            if export_response.get('done', False):
                return {'success': True, 'filename': name, 'message': 'Export đã được tạo thành công'}
            else:
                return {'success': False, 'error': 'Không thể tạo export'}
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo export: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_logs(self, topics=None, limit=50):
        """Lấy logs từ thiết bị"""
        try:
            params = {}
            if topics:
                params['topics'] = ','.join(topics)
            if limit:
                params['limit'] = str(limit)
            
            logs_response = self.execute_command('/log/print', params)
            logs = []
            
            for log in logs_response.get('re', []):
                log_entry = {
                    'time': log.get('time', 'Unknown'),
                    'topics': log.get('topics', '').split(','),
                    'message': log.get('message', 'Unknown')
                }
                logs.append(log_entry)
            
            return logs
        except Exception as e:
            self.logger.error(f"Lỗi khi lấy logs: {str(e)}")
            return []