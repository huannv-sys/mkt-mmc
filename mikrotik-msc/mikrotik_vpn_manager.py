#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quản lý VPN trên thiết bị MikroTik
Script này quản lý các kết nối VPN như IPSec, OpenVPN, L2TP, PPTP và SSTP
"""

import os
import sys
import time
import json
import logging
import argparse
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
import routeros_api

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('mikrotik_vpn')

class Colors:
    """Màu sắc cho đầu ra terminal."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class MikroTikVPNManager:
    """Lớp quản lý VPN trên thiết bị MikroTik."""
    
    def __init__(self, host, username, password):
        """Khởi tạo với thông tin kết nối."""
        self.host = host
        self.username = username
        self.password = password
        self.connection = None
        self.api = None
        logger.info(f"Đang kết nối đến {host}...")
        
    def connect(self):
        """Kết nối đến thiết bị MikroTik và trả về API object."""
        try:
            self.connection = routeros_api.RouterOsApiPool(
                self.host,
                username=self.username,
                password=self.password,
                plaintext_login=True
            )
            self.api = self.connection.get_api()
            logger.info(f"Đã kết nối thành công đến {self.host}")
            return self.api
        except Exception as e:
            logger.error(f"Lỗi khi kết nối đến {self.host}: {e}")
            return None
            
    def disconnect(self):
        """Ngắt kết nối."""
        if self.connection:
            self.connection.disconnect()
            logger.info(f"Đã ngắt kết nối từ {self.host}")
            
    def get_device_info(self):
        """Lấy thông tin cơ bản về thiết bị."""
        if not self.api:
            return {}
            
        try:
            # Lấy thông tin thiết bị
            identity = self.api.get_resource('/system/identity').get()[0].get('name', 'Unknown')
            resource = self.api.get_resource('/system/resource').get()[0]
            
            # Lấy thông tin RouterOS
            ros_version = resource.get('version', 'Unknown')
            uptime = resource.get('uptime', 'Unknown')
            cpu_load = resource.get('cpu-load', '0')
            
            # Lấy thông tin phần cứng
            board_name = resource.get('board-name', 'Unknown')
            platform = resource.get('platform', 'Unknown')
            
            return {
                'hostname': identity,
                'ros_version': ros_version,
                'uptime': uptime,
                'cpu_load': f"{cpu_load}%",
                'model': f"{platform} {board_name}"
            }
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin thiết bị: {e}")
            return {}
            
    # ===== IPSec VPN =====
    
    def get_ipsec_proposals(self):
        """Lấy danh sách IPSec proposals."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/ip/ipsec/proposal').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách IPSec proposals: {e}")
            return []
    
    def add_ipsec_proposal(self, name, auth_algorithms=None, enc_algorithms=None, pfs_group=None, lifetime=None, comment=None):
        """Thêm một IPSec proposal."""
        if not self.api:
            return False
            
        try:
            proposal_resource = self.api.get_resource('/ip/ipsec/proposal')
            
            # Params cơ bản
            params = {"name": name}
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if auth_algorithms:
                params["auth-algorithms"] = auth_algorithms
            if enc_algorithms:
                params["enc-algorithms"] = enc_algorithms
            if pfs_group:
                params["pfs-group"] = pfs_group
            if lifetime:
                params["lifetime"] = str(lifetime)
            if comment:
                params["comment"] = comment
                
            # Thêm proposal
            proposal_resource.add(**params)
            logger.info(f"Đã thêm IPSec proposal: {name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm IPSec proposal: {e}")
            return False
    
    def get_ipsec_peers(self):
        """Lấy danh sách IPSec peers."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/ip/ipsec/peer').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách IPSec peers: {e}")
            return []
    
    def add_ipsec_peer(self, name, address, local_address=None, profile=None, exchange_mode="main", 
                      send_initial_contact=True, nat_traversal=True, proposal=None, comment=None):
        """Thêm một IPSec peer."""
        if not self.api:
            return False
            
        try:
            peer_resource = self.api.get_resource('/ip/ipsec/peer')
            
            # Params cơ bản
            params = {
                "name": name,
                "address": address,
                "exchange-mode": exchange_mode,
                "send-initial-contact": "yes" if send_initial_contact else "no",
                "nat-traversal": "yes" if nat_traversal else "no"
            }
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if local_address:
                params["local-address"] = local_address
            if profile:
                params["profile"] = profile
            if proposal:
                params["proposal"] = proposal
            if comment:
                params["comment"] = comment
                
            # Thêm peer
            peer_resource.add(**params)
            logger.info(f"Đã thêm IPSec peer: {name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm IPSec peer: {e}")
            return False
    
    def get_ipsec_identities(self):
        """Lấy danh sách IPSec identities."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/ip/ipsec/identity').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách IPSec identities: {e}")
            return []
    
    def add_ipsec_identity(self, peer, secret, policy_template_group=None, generate_policy=True, remote_id=None, comment=None):
        """Thêm một IPSec identity."""
        if not self.api:
            return False
            
        try:
            identity_resource = self.api.get_resource('/ip/ipsec/identity')
            
            # Params cơ bản
            params = {
                "peer": peer,
                "secret": secret,
                "generate-policy": "yes" if generate_policy else "no"
            }
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if policy_template_group:
                params["policy-template-group"] = policy_template_group
            if remote_id:
                params["remote-id"] = remote_id
            if comment:
                params["comment"] = comment
                
            # Thêm identity
            identity_resource.add(**params)
            logger.info(f"Đã thêm IPSec identity cho peer: {peer}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm IPSec identity: {e}")
            return False
    
    def get_ipsec_policies(self):
        """Lấy danh sách IPSec policies."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/ip/ipsec/policy').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách IPSec policies: {e}")
            return []
    
    def add_ipsec_policy(self, src_address, dst_address, sa_src_address=None, sa_dst_address=None,
                        protocol="all", proposal=None, template=False, comment=None):
        """Thêm một IPSec policy."""
        if not self.api:
            return False
            
        try:
            policy_resource = self.api.get_resource('/ip/ipsec/policy')
            
            # Params cơ bản
            params = {
                "src-address": src_address,
                "dst-address": dst_address,
                "protocol": protocol,
                "template": "yes" if template else "no"
            }
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if sa_src_address:
                params["sa-src-address"] = sa_src_address
            if sa_dst_address:
                params["sa-dst-address"] = sa_dst_address
            if proposal:
                params["proposal"] = proposal
            if comment:
                params["comment"] = comment
                
            # Thêm policy
            policy_resource.add(**params)
            logger.info(f"Đã thêm IPSec policy: {src_address} -> {dst_address}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm IPSec policy: {e}")
            return False
    
    def setup_ipsec_site_to_site(self, remote_gateway, local_subnet, remote_subnet, shared_key, 
                               proposal_name=None, peer_name=None, local_gateway=None):
        """Thiết lập VPN Site-to-Site sử dụng IPSec."""
        if not self.api:
            return False
            
        try:
            # 1. Tạo proposal nếu cần
            if not proposal_name:
                proposal_name = f"proposal-{remote_gateway}"
                self.add_ipsec_proposal(
                    name=proposal_name,
                    auth_algorithms="sha256",
                    enc_algorithms="aes-256-cbc",
                    pfs_group="modp2048",
                    lifetime="8h",
                    comment=f"Proposal for {remote_gateway}"
                )
            
            # 2. Tạo peer
            if not peer_name:
                peer_name = f"peer-{remote_gateway}"
            self.add_ipsec_peer(
                name=peer_name,
                address=remote_gateway,
                local_address=local_gateway,
                proposal=proposal_name,
                comment=f"Peer for {remote_gateway}"
            )
            
            # 3. Tạo identity
            self.add_ipsec_identity(
                peer=peer_name,
                secret=shared_key,
                comment=f"Identity for {remote_gateway}"
            )
            
            # 4. Tạo policy
            self.add_ipsec_policy(
                src_address=local_subnet,
                dst_address=remote_subnet,
                sa_src_address=local_gateway,
                sa_dst_address=remote_gateway,
                proposal=proposal_name,
                comment=f"Policy for {remote_gateway} site-to-site"
            )
            
            logger.info(f"Đã thiết lập IPSec site-to-site VPN đến {remote_gateway}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập IPSec site-to-site: {e}")
            return False
    
    # ===== OpenVPN =====
    
    def get_ovpn_servers(self):
        """Lấy danh sách OpenVPN servers."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/interface/ovpn-server/server').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách OpenVPN servers: {e}")
            return []
    
    def setup_ovpn_server(self, name, port=1194, netmask=24, certificate=None, auth=None,
                        cipher=None, max_mtu=1500, mode="ip", comment=None):
        """Thiết lập một OpenVPN server."""
        if not self.api:
            return False
            
        try:
            server_resource = self.api.get_resource('/interface/ovpn-server/server')
            
            # Params cơ bản
            params = {
                "name": name,
                "port": str(port),
                "netmask": str(netmask),
                "mode": mode,
                "max-mtu": str(max_mtu)
            }
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if certificate:
                params["certificate"] = certificate
            if auth:
                params["auth"] = auth
            if cipher:
                params["cipher"] = cipher
            if comment:
                params["comment"] = comment
                
            # Thiết lập server
            server_resource.add(**params)
            logger.info(f"Đã thiết lập OpenVPN server: {name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập OpenVPN server: {e}")
            return False
    
    def get_ovpn_clients(self):
        """Lấy danh sách OpenVPN clients."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/interface/ovpn-client').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách OpenVPN clients: {e}")
            return []
    
    def setup_ovpn_client(self, name, connect_to, port=1194, user=None, password=None, 
                        certificate=None, auth=None, cipher=None, max_mtu=1500, comment=None):
        """Thiết lập một OpenVPN client."""
        if not self.api:
            return False
            
        try:
            client_resource = self.api.get_resource('/interface/ovpn-client')
            
            # Params cơ bản
            params = {
                "name": name,
                "connect-to": connect_to,
                "port": str(port),
                "max-mtu": str(max_mtu)
            }
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if user:
                params["user"] = user
            if password:
                params["password"] = password
            if certificate:
                params["certificate"] = certificate
            if auth:
                params["auth"] = auth
            if cipher:
                params["cipher"] = cipher
            if comment:
                params["comment"] = comment
                
            # Thiết lập client
            client_resource.add(**params)
            logger.info(f"Đã thiết lập OpenVPN client: {name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập OpenVPN client: {e}")
            return False
    
    # ===== L2TP =====
    
    def get_l2tp_servers(self):
        """Lấy thông tin L2TP server."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/interface/l2tp-server/server').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin L2TP server: {e}")
            return []
    
    def setup_l2tp_server(self, enabled=True, max_sessions=100, authentication="mschap2", 
                        use_ipsec=True, ipsec_secret=None, default_profile=None, keepalive_timeout="60"):
        """Thiết lập L2TP server."""
        if not self.api:
            return False
            
        try:
            server_resource = self.api.get_resource('/interface/l2tp-server/server')
            
            # Params cơ bản
            params = {
                "enabled": "yes" if enabled else "no",
                "max-sessions": str(max_sessions),
                "authentication": authentication,
                "use-ipsec": "yes" if use_ipsec else "no",
                "keepalive-timeout": keepalive_timeout
            }
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if ipsec_secret:
                params["ipsec-secret"] = ipsec_secret
            if default_profile:
                params["default-profile"] = default_profile
                
            # Nếu L2TP server đã được cấu hình, cập nhật nó
            servers = server_resource.get()
            if servers:
                # Cập nhật server hiện có
                server_resource.set(id=servers[0].get('.id'), **params)
                logger.info("Đã cập nhật L2TP server")
            else:
                # Tạo mới nếu chưa có
                server_resource.add(**params)
                logger.info("Đã tạo L2TP server mới")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập L2TP server: {e}")
            return False
    
    def get_l2tp_clients(self):
        """Lấy danh sách L2TP clients."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/interface/l2tp-client').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách L2TP clients: {e}")
            return []
    
    def setup_l2tp_client(self, name, connect_to, user, password, profile=None, 
                        use_ipsec=True, ipsec_secret=None, add_default_route=False,
                        allow_remote=True, comment=None):
        """Thiết lập L2TP client."""
        if not self.api:
            return False
            
        try:
            client_resource = self.api.get_resource('/interface/l2tp-client')
            
            # Params cơ bản
            params = {
                "name": name,
                "connect-to": connect_to,
                "user": user,
                "password": password,
                "use-ipsec": "yes" if use_ipsec else "no",
                "add-default-route": "yes" if add_default_route else "no",
                "allow-remote": "yes" if allow_remote else "no"
            }
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if profile:
                params["profile"] = profile
            if use_ipsec and ipsec_secret:
                params["ipsec-secret"] = ipsec_secret
            if comment:
                params["comment"] = comment
                
            # Thiết lập client
            client_resource.add(**params)
            logger.info(f"Đã thiết lập L2TP client: {name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập L2TP client: {e}")
            return False
    
    # ===== PPTP =====
    
    def get_pptp_servers(self):
        """Lấy thông tin PPTP server."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/interface/pptp-server/server').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin PPTP server: {e}")
            return []
    
    def setup_pptp_server(self, enabled=True, max_sessions=100, authentication="mschap2", 
                        default_profile=None, keepalive_timeout="60"):
        """Thiết lập PPTP server."""
        if not self.api:
            return False
            
        try:
            server_resource = self.api.get_resource('/interface/pptp-server/server')
            
            # Params cơ bản
            params = {
                "enabled": "yes" if enabled else "no",
                "max-sessions": str(max_sessions),
                "authentication": authentication,
                "keepalive-timeout": keepalive_timeout
            }
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if default_profile:
                params["default-profile"] = default_profile
                
            # Nếu PPTP server đã được cấu hình, cập nhật nó
            servers = server_resource.get()
            if servers:
                # Cập nhật server hiện có
                server_resource.set(id=servers[0].get('.id'), **params)
                logger.info("Đã cập nhật PPTP server")
            else:
                # Tạo mới nếu chưa có
                server_resource.add(**params)
                logger.info("Đã tạo PPTP server mới")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập PPTP server: {e}")
            return False
    
    def get_pptp_clients(self):
        """Lấy danh sách PPTP clients."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/interface/pptp-client').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách PPTP clients: {e}")
            return []
    
    def setup_pptp_client(self, name, connect_to, user, password, profile=None, 
                        add_default_route=False, allow_remote=True, comment=None):
        """Thiết lập PPTP client."""
        if not self.api:
            return False
            
        try:
            client_resource = self.api.get_resource('/interface/pptp-client')
            
            # Params cơ bản
            params = {
                "name": name,
                "connect-to": connect_to,
                "user": user,
                "password": password,
                "add-default-route": "yes" if add_default_route else "no",
                "allow-remote": "yes" if allow_remote else "no"
            }
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if profile:
                params["profile"] = profile
            if comment:
                params["comment"] = comment
                
            # Thiết lập client
            client_resource.add(**params)
            logger.info(f"Đã thiết lập PPTP client: {name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập PPTP client: {e}")
            return False
    
    # ===== SSTP =====
    
    def get_sstp_servers(self):
        """Lấy thông tin SSTP server."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/interface/sstp-server/server').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin SSTP server: {e}")
            return []
    
    def setup_sstp_server(self, enabled=True, cert=None, verify_client_cert=False, 
                        authentication="mschap2", default_profile=None, port="443"):
        """Thiết lập SSTP server."""
        if not self.api:
            return False
            
        try:
            server_resource = self.api.get_resource('/interface/sstp-server/server')
            
            # Params cơ bản
            params = {
                "enabled": "yes" if enabled else "no",
                "verify-client-certificate": "yes" if verify_client_cert else "no",
                "authentication": authentication,
                "port": port
            }
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if cert:
                params["certificate"] = cert
            if default_profile:
                params["default-profile"] = default_profile
                
            # Nếu SSTP server đã được cấu hình, cập nhật nó
            servers = server_resource.get()
            if servers:
                # Cập nhật server hiện có
                server_resource.set(id=servers[0].get('.id'), **params)
                logger.info("Đã cập nhật SSTP server")
            else:
                # Tạo mới nếu chưa có
                server_resource.add(**params)
                logger.info("Đã tạo SSTP server mới")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập SSTP server: {e}")
            return False
    
    def get_sstp_clients(self):
        """Lấy danh sách SSTP clients."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/interface/sstp-client').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách SSTP clients: {e}")
            return []
    
    def setup_sstp_client(self, name, connect_to, user, password, profile=None, 
                        verify_server_certificate=False, add_default_route=False, comment=None):
        """Thiết lập SSTP client."""
        if not self.api:
            return False
            
        try:
            client_resource = self.api.get_resource('/interface/sstp-client')
            
            # Params cơ bản
            params = {
                "name": name,
                "connect-to": connect_to,
                "user": user,
                "password": password,
                "verify-server-certificate": "yes" if verify_server_certificate else "no",
                "add-default-route": "yes" if add_default_route else "no"
            }
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if profile:
                params["profile"] = profile
            if comment:
                params["comment"] = comment
                
            # Thiết lập client
            client_resource.add(**params)
            logger.info(f"Đã thiết lập SSTP client: {name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập SSTP client: {e}")
            return False
    
    # ===== PPP Profiles =====
    
    def get_ppp_profiles(self):
        """Lấy danh sách PPP profiles."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/ppp/profile').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách PPP profiles: {e}")
            return []
    
    def setup_ppp_profile(self, name, local_address=None, remote_address=None, 
                        dns_server=None, wins_server=None, rate_limit=None, 
                        use_mpls=False, use_compression=True, use_encryption=True, comment=None):
        """Thiết lập PPP profile."""
        if not self.api:
            return False
            
        try:
            profile_resource = self.api.get_resource('/ppp/profile')
            
            # Params cơ bản
            params = {
                "name": name,
                "use-mpls": "yes" if use_mpls else "no",
                "use-compression": "yes" if use_compression else "no",
                "use-encryption": "yes" if use_encryption else "no"
            }
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if local_address:
                params["local-address"] = local_address
            if remote_address:
                params["remote-address"] = remote_address
            if dns_server:
                params["dns-server"] = dns_server
            if wins_server:
                params["wins-server"] = wins_server
            if rate_limit:
                params["rate-limit"] = rate_limit
            if comment:
                params["comment"] = comment
                
            # Thiết lập profile
            profile_resource.add(**params)
            logger.info(f"Đã thiết lập PPP profile: {name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập PPP profile: {e}")
            return False
    
    # ===== PPP Users =====
    
    def get_ppp_secrets(self):
        """Lấy danh sách PPP secrets (users)."""
        if not self.api:
            return []
            
        try:
            return self.api.get_resource('/ppp/secret').get()
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách PPP secrets: {e}")
            return []
    
    def add_ppp_user(self, name, password, profile=None, local_address=None, remote_address=None, 
                   service="any", caller_id=None, limit_bytes_in=None, limit_bytes_out=None, comment=None):
        """Thêm PPP user."""
        if not self.api:
            return False
            
        try:
            secret_resource = self.api.get_resource('/ppp/secret')
            
            # Params cơ bản
            params = {
                "name": name,
                "password": password,
                "service": service
            }
            
            # Thêm các tham số tùy chọn nếu được cung cấp
            if profile:
                params["profile"] = profile
            if local_address:
                params["local-address"] = local_address
            if remote_address:
                params["remote-address"] = remote_address
            if caller_id:
                params["caller-id"] = caller_id
            if limit_bytes_in:
                params["limit-bytes-in"] = str(limit_bytes_in)
            if limit_bytes_out:
                params["limit-bytes-out"] = str(limit_bytes_out)
            if comment:
                params["comment"] = comment
                
            # Thêm user
            secret_resource.add(**params)
            logger.info(f"Đã thêm PPP user: {name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm PPP user: {e}")
            return False
    
    def remove_ppp_user(self, name):
        """Xóa PPP user."""
        if not self.api:
            return False
            
        try:
            secret_resource = self.api.get_resource('/ppp/secret')
            
            # Tìm user cần xóa
            secrets = secret_resource.get(name=name)
            if not secrets:
                logger.warning(f"Không tìm thấy PPP user: {name}")
                return False
                
            # Xóa user
            for secret in secrets:
                secret_resource.remove(id=secret.get('.id'))
                logger.info(f"Đã xóa PPP user: {name}")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi xóa PPP user: {e}")
            return False
    
    # ===== Active Connections =====
    
    def get_active_connections(self):
        """Lấy danh sách kết nối VPN đang hoạt động."""
        if not self.api:
            return []
            
        try:
            active = []
            
            # Lấy các kết nối PPP
            try:
                ppp_active = self.api.get_resource('/ppp/active').get()
                for conn in ppp_active:
                    conn['type'] = 'ppp'
                active.extend(ppp_active)
            except:
                pass
                
            return active
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách kết nối VPN đang hoạt động: {e}")
            return []
    
    def disconnect_active_connection(self, id):
        """Ngắt kết nối VPN đang hoạt động."""
        if not self.api:
            return False
            
        try:
            active_resource = self.api.get_resource('/ppp/active')
            active_resource.remove(id=id)
            logger.info(f"Đã ngắt kết nối VPN ID: {id}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi ngắt kết nối VPN: {e}")
            return False
    
    # ===== Routing =====
    
    def get_vpn_routes(self):
        """Lấy các route liên quan đến VPN."""
        if not self.api:
            return []
            
        try:
            # Lọc các route có gateway là interface VPN hoặc dst-address là subnet VPN
            routes = self.api.get_resource('/ip/route').get()
            vpn_routes = []
            
            # Các tên interface VPN thường có
            vpn_interface_prefixes = ['ovpn', 'l2tp', 'pptp', 'sstp', 'ipsec']
            
            for route in routes:
                gateway = route.get('gateway', '')
                
                # Kiểm tra xem route có phải cho VPN không
                for prefix in vpn_interface_prefixes:
                    if prefix in gateway:
                        route['vpn_type'] = prefix
                        vpn_routes.append(route)
                        break
                        
            return vpn_routes
        except Exception as e:
            logger.error(f"Lỗi khi lấy các route VPN: {e}")
            return []


def main():
    """Hàm chính để chạy công cụ quản lý VPN."""
    # Load environment variables
    load_dotenv()
    
    # Lấy thông tin kết nối từ biến môi trường hoặc command line arguments
    parser = argparse.ArgumentParser(description='Công cụ quản lý VPN trên MikroTik')
    parser.add_argument('--host', default=os.getenv('MIKROTIK_HOST'), help='Địa chỉ IP của thiết bị MikroTik')
    parser.add_argument('--user', default=os.getenv('MIKROTIK_USER'), help='Tên đăng nhập')
    parser.add_argument('--password', default=os.getenv('MIKROTIK_PASSWORD'), help='Mật khẩu')
    
    # Các lệnh
    subparsers = parser.add_subparsers(dest='command', help='Lệnh')
    
    # Lệnh list
    list_parser = subparsers.add_parser('list', help='Liệt kê thông tin VPN')
    list_parser.add_argument('--type', choices=['ipsec', 'ovpn', 'l2tp', 'pptp', 'sstp', 'users', 'active', 'routes'], help='Loại VPN cần liệt kê')
    
    # Lệnh setup IPSec site-to-site
    ipsec_site_parser = subparsers.add_parser('ipsec-site', help='Thiết lập IPSec site-to-site VPN')
    ipsec_site_parser.add_argument('--remote-gateway', required=True, help='Địa chỉ gateway của site đối tác')
    ipsec_site_parser.add_argument('--local-subnet', required=True, help='Subnet local cần kết nối (ví dụ: 192.168.1.0/24)')
    ipsec_site_parser.add_argument('--remote-subnet', required=True, help='Subnet remote cần kết nối đến (ví dụ: 192.168.2.0/24)')
    ipsec_site_parser.add_argument('--shared-key', required=True, help='Pre-shared key')
    ipsec_site_parser.add_argument('--local-gateway', help='Địa chỉ gateway local, nếu khác với WAN')
    
    # Lệnh setup OpenVPN server
    ovpn_server_parser = subparsers.add_parser('ovpn-server', help='Thiết lập OpenVPN server')
    ovpn_server_parser.add_argument('--name', default='ovpn-server', help='Tên server (mặc định: ovpn-server)')
    ovpn_server_parser.add_argument('--port', type=int, default=1194, help='Port (mặc định: 1194)')
    ovpn_server_parser.add_argument('--certificate', required=True, help='Tên certificate')
    
    # Lệnh setup OpenVPN client
    ovpn_client_parser = subparsers.add_parser('ovpn-client', help='Thiết lập OpenVPN client')
    ovpn_client_parser.add_argument('--name', required=True, help='Tên client')
    ovpn_client_parser.add_argument('--connect-to', required=True, help='Địa chỉ server')
    ovpn_client_parser.add_argument('--port', type=int, default=1194, help='Port (mặc định: 1194)')
    ovpn_client_parser.add_argument('--user', help='Tên đăng nhập (nếu cần)')
    ovpn_client_parser.add_argument('--password', help='Mật khẩu (nếu cần)')
    ovpn_client_parser.add_argument('--certificate', help='Tên certificate (nếu cần)')
    
    # Lệnh setup L2TP server
    l2tp_server_parser = subparsers.add_parser('l2tp-server', help='Thiết lập L2TP server')
    l2tp_server_parser.add_argument('--enabled', action='store_true', default=True, help='Bật server (mặc định: True)')
    l2tp_server_parser.add_argument('--use-ipsec', action='store_true', default=True, help='Sử dụng IPSec (mặc định: True)')
    l2tp_server_parser.add_argument('--ipsec-secret', help='IPSec secret (bắt buộc nếu use-ipsec=True)')
    
    # Lệnh setup L2TP client
    l2tp_client_parser = subparsers.add_parser('l2tp-client', help='Thiết lập L2TP client')
    l2tp_client_parser.add_argument('--name', required=True, help='Tên client')
    l2tp_client_parser.add_argument('--connect-to', required=True, help='Địa chỉ server')
    l2tp_client_parser.add_argument('--user', required=True, help='Tên đăng nhập')
    l2tp_client_parser.add_argument('--password', required=True, help='Mật khẩu')
    l2tp_client_parser.add_argument('--use-ipsec', action='store_true', default=True, help='Sử dụng IPSec (mặc định: True)')
    l2tp_client_parser.add_argument('--ipsec-secret', help='IPSec secret (bắt buộc nếu use-ipsec=True)')
    
    # Lệnh thêm PPP user
    add_user_parser = subparsers.add_parser('add-user', help='Thêm PPP user')
    add_user_parser.add_argument('--name', required=True, help='Tên user')
    add_user_parser.add_argument('--password', required=True, help='Mật khẩu')
    add_user_parser.add_argument('--profile', help='Profile')
    add_user_parser.add_argument('--service', default='any', choices=['any', 'l2tp', 'pptp', 'sstp', 'ovpn'], help='Dịch vụ (mặc định: any)')
    add_user_parser.add_argument('--remote-address', help='Địa chỉ IP cấp cho client')
    add_user_parser.add_argument('--comment', help='Ghi chú')
    
    # Lệnh xóa PPP user
    remove_user_parser = subparsers.add_parser('remove-user', help='Xóa PPP user')
    remove_user_parser.add_argument('--name', required=True, help='Tên user')
    
    # Lệnh ngắt kết nối VPN
    disconnect_parser = subparsers.add_parser('disconnect', help='Ngắt kết nối VPN')
    disconnect_parser.add_argument('--id', required=True, help='ID của kết nối (lấy từ lệnh list --type=active)')
    
    args = parser.parse_args()
    
    # Kiểm tra thông tin kết nối
    if not args.host or not args.user or not args.password:
        print(f"{Colors.RED}Lỗi: Thiếu thông tin kết nối MikroTik.{Colors.ENDC}")
        print(f"{Colors.RED}Vui lòng cung cấp thông tin qua biến môi trường hoặc command line arguments.{Colors.ENDC}")
        parser.print_help()
        return
    
    # Khởi tạo VPN manager
    vpn_manager = MikroTikVPNManager(args.host, args.user, args.password)
    api = vpn_manager.connect()
    
    if not api:
        print(f"{Colors.RED}Lỗi: Không thể kết nối đến MikroTik.{Colors.ENDC}")
        return
    
    try:
        # Xử lý các lệnh
        if args.command == 'list':
            if not args.type or args.type == 'ipsec':
                # IPSec
                print(f"{Colors.HEADER}{Colors.BOLD}=== IPSEC PEERS ==={Colors.ENDC}")
                peers = vpn_manager.get_ipsec_peers()
                for i, peer in enumerate(peers):
                    print(f"{i+1}. {peer.get('name')} - Address: {peer.get('address')}")
                    if peer.get('comment'):
                        print(f"   Comment: {peer.get('comment')}")
                print()
                
                print(f"{Colors.HEADER}{Colors.BOLD}=== IPSEC POLICIES ==={Colors.ENDC}")
                policies = vpn_manager.get_ipsec_policies()
                for i, policy in enumerate(policies):
                    src = policy.get('src-address', '')
                    dst = policy.get('dst-address', '')
                    print(f"{i+1}. Policy: {src} -> {dst}")
                    if policy.get('comment'):
                        print(f"   Comment: {policy.get('comment')}")
                print()
                
            if not args.type or args.type == 'ovpn':
                # OpenVPN
                print(f"{Colors.HEADER}{Colors.BOLD}=== OPENVPN SERVERS ==={Colors.ENDC}")
                servers = vpn_manager.get_ovpn_servers()
                for i, server in enumerate(servers):
                    print(f"{i+1}. {server.get('name')} - Port: {server.get('port')}")
                    if server.get('certificate'):
                        print(f"   Certificate: {server.get('certificate')}")
                    if server.get('comment'):
                        print(f"   Comment: {server.get('comment')}")
                print()
                
                print(f"{Colors.HEADER}{Colors.BOLD}=== OPENVPN CLIENTS ==={Colors.ENDC}")
                clients = vpn_manager.get_ovpn_clients()
                for i, client in enumerate(clients):
                    print(f"{i+1}. {client.get('name')} - Server: {client.get('connect-to')}:{client.get('port')}")
                    if client.get('comment'):
                        print(f"   Comment: {client.get('comment')}")
                print()
                
            if not args.type or args.type == 'l2tp':
                # L2TP
                print(f"{Colors.HEADER}{Colors.BOLD}=== L2TP SERVER ==={Colors.ENDC}")
                servers = vpn_manager.get_l2tp_servers()
                for i, server in enumerate(servers):
                    enabled = "Đã bật" if server.get('enabled') == "true" else "Đã tắt"
                    use_ipsec = "Có" if server.get('use-ipsec') == "true" else "Không"
                    print(f"Trạng thái: {enabled}")
                    print(f"Sử dụng IPSec: {use_ipsec}")
                    print(f"Max sessions: {server.get('max-sessions')}")
                    print(f"Authentication: {server.get('authentication')}")
                print()
                
                print(f"{Colors.HEADER}{Colors.BOLD}=== L2TP CLIENTS ==={Colors.ENDC}")
                clients = vpn_manager.get_l2tp_clients()
                for i, client in enumerate(clients):
                    print(f"{i+1}. {client.get('name')} - Server: {client.get('connect-to')}")
                    print(f"   User: {client.get('user')}")
                    use_ipsec = "Có" if client.get('use-ipsec') == "true" else "Không"
                    print(f"   Sử dụng IPSec: {use_ipsec}")
                    if client.get('comment'):
                        print(f"   Comment: {client.get('comment')}")
                print()
                
            if not args.type or args.type == 'pptp':
                # PPTP
                print(f"{Colors.HEADER}{Colors.BOLD}=== PPTP SERVER ==={Colors.ENDC}")
                servers = vpn_manager.get_pptp_servers()
                for i, server in enumerate(servers):
                    enabled = "Đã bật" if server.get('enabled') == "true" else "Đã tắt"
                    print(f"Trạng thái: {enabled}")
                    print(f"Max sessions: {server.get('max-sessions')}")
                    print(f"Authentication: {server.get('authentication')}")
                print()
                
                print(f"{Colors.HEADER}{Colors.BOLD}=== PPTP CLIENTS ==={Colors.ENDC}")
                clients = vpn_manager.get_pptp_clients()
                for i, client in enumerate(clients):
                    print(f"{i+1}. {client.get('name')} - Server: {client.get('connect-to')}")
                    print(f"   User: {client.get('user')}")
                    if client.get('comment'):
                        print(f"   Comment: {client.get('comment')}")
                print()
                
            if not args.type or args.type == 'sstp':
                # SSTP
                print(f"{Colors.HEADER}{Colors.BOLD}=== SSTP SERVER ==={Colors.ENDC}")
                servers = vpn_manager.get_sstp_servers()
                for i, server in enumerate(servers):
                    enabled = "Đã bật" if server.get('enabled') == "true" else "Đã tắt"
                    print(f"Trạng thái: {enabled}")
                    print(f"Port: {server.get('port')}")
                    print(f"Authentication: {server.get('authentication')}")
                    if server.get('certificate'):
                        print(f"Certificate: {server.get('certificate')}")
                print()
                
                print(f"{Colors.HEADER}{Colors.BOLD}=== SSTP CLIENTS ==={Colors.ENDC}")
                clients = vpn_manager.get_sstp_clients()
                for i, client in enumerate(clients):
                    print(f"{i+1}. {client.get('name')} - Server: {client.get('connect-to')}")
                    print(f"   User: {client.get('user')}")
                    if client.get('comment'):
                        print(f"   Comment: {client.get('comment')}")
                print()
                
            if not args.type or args.type == 'users':
                # PPP users
                print(f"{Colors.HEADER}{Colors.BOLD}=== PPP USERS ==={Colors.ENDC}")
                users = vpn_manager.get_ppp_secrets()
                for i, user in enumerate(users):
                    print(f"{i+1}. {user.get('name')} - Service: {user.get('service')}")
                    if user.get('profile'):
                        print(f"   Profile: {user.get('profile')}")
                    if user.get('remote-address'):
                        print(f"   Remote address: {user.get('remote-address')}")
                    if user.get('comment'):
                        print(f"   Comment: {user.get('comment')}")
                print()
                
            if not args.type or args.type == 'active':
                # Active connections
                print(f"{Colors.HEADER}{Colors.BOLD}=== ACTIVE CONNECTIONS ==={Colors.ENDC}")
                connections = vpn_manager.get_active_connections()
                for i, conn in enumerate(connections):
                    print(f"{i+1}. {conn.get('name')} - Service: {conn.get('service')}")
                    print(f"   User: {conn.get('user')}")
                    print(f"   Address: {conn.get('address')}")
                    print(f"   Uptime: {conn.get('uptime')}")
                    print(f"   ID: {conn.get('.id')}")
                print()
                
            if not args.type or args.type == 'routes':
                # VPN routes
                print(f"{Colors.HEADER}{Colors.BOLD}=== VPN ROUTES ==={Colors.ENDC}")
                routes = vpn_manager.get_vpn_routes()
                for i, route in enumerate(routes):
                    dst = route.get('dst-address', '')
                    gateway = route.get('gateway', '')
                    vpn_type = route.get('vpn_type', 'unknown')
                    print(f"{i+1}. {dst} via {gateway} ({vpn_type})")
                    if route.get('comment'):
                        print(f"   Comment: {route.get('comment')}")
                print()
        
        elif args.command == 'ipsec-site':
            # Thiết lập IPSec site-to-site VPN
            if vpn_manager.setup_ipsec_site_to_site(
                remote_gateway=args.remote_gateway,
                local_subnet=args.local_subnet,
                remote_subnet=args.remote_subnet,
                shared_key=args.shared_key,
                local_gateway=args.local_gateway
            ):
                print(f"{Colors.GREEN}Đã thiết lập IPSec site-to-site VPN đến {args.remote_gateway} thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thiết lập IPSec site-to-site VPN.{Colors.ENDC}")
        
        elif args.command == 'ovpn-server':
            # Thiết lập OpenVPN server
            if vpn_manager.setup_ovpn_server(
                name=args.name,
                port=args.port,
                certificate=args.certificate
            ):
                print(f"{Colors.GREEN}Đã thiết lập OpenVPN server {args.name} thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thiết lập OpenVPN server.{Colors.ENDC}")
        
        elif args.command == 'ovpn-client':
            # Thiết lập OpenVPN client
            if vpn_manager.setup_ovpn_client(
                name=args.name,
                connect_to=args.connect_to,
                port=args.port,
                user=args.user,
                password=args.password,
                certificate=args.certificate
            ):
                print(f"{Colors.GREEN}Đã thiết lập OpenVPN client {args.name} thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thiết lập OpenVPN client.{Colors.ENDC}")
        
        elif args.command == 'l2tp-server':
            # Thiết lập L2TP server
            if args.use_ipsec and not args.ipsec_secret:
                print(f"{Colors.RED}Lỗi: Thiếu tham số ipsec-secret.{Colors.ENDC}")
                return
                
            if vpn_manager.setup_l2tp_server(
                enabled=args.enabled,
                use_ipsec=args.use_ipsec,
                ipsec_secret=args.ipsec_secret
            ):
                print(f"{Colors.GREEN}Đã thiết lập L2TP server thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thiết lập L2TP server.{Colors.ENDC}")
        
        elif args.command == 'l2tp-client':
            # Thiết lập L2TP client
            if args.use_ipsec and not args.ipsec_secret:
                print(f"{Colors.RED}Lỗi: Thiếu tham số ipsec-secret.{Colors.ENDC}")
                return
                
            if vpn_manager.setup_l2tp_client(
                name=args.name,
                connect_to=args.connect_to,
                user=args.user,
                password=args.password,
                use_ipsec=args.use_ipsec,
                ipsec_secret=args.ipsec_secret
            ):
                print(f"{Colors.GREEN}Đã thiết lập L2TP client {args.name} thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thiết lập L2TP client.{Colors.ENDC}")
        
        elif args.command == 'add-user':
            # Thêm PPP user
            if vpn_manager.add_ppp_user(
                name=args.name,
                password=args.password,
                profile=args.profile,
                remote_address=args.remote_address,
                service=args.service,
                comment=args.comment
            ):
                print(f"{Colors.GREEN}Đã thêm PPP user {args.name} thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể thêm PPP user.{Colors.ENDC}")
        
        elif args.command == 'remove-user':
            # Xóa PPP user
            if vpn_manager.remove_ppp_user(args.name):
                print(f"{Colors.GREEN}Đã xóa PPP user {args.name} thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể xóa PPP user.{Colors.ENDC}")
        
        elif args.command == 'disconnect':
            # Ngắt kết nối VPN
            if vpn_manager.disconnect_active_connection(args.id):
                print(f"{Colors.GREEN}Đã ngắt kết nối VPN thành công.{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Không thể ngắt kết nối VPN.{Colors.ENDC}")
        
        else:
            # Nếu không có lệnh nào được chỉ định, hiển thị thông tin cơ bản
            device_info = vpn_manager.get_device_info()
            print(f"{Colors.HEADER}{Colors.BOLD}=== THÔNG TIN THIẾT BỊ ==={Colors.ENDC}")
            print(f"Thiết bị: {device_info.get('hostname')}")
            print(f"Model: {device_info.get('model')}")
            print(f"RouterOS: {device_info.get('ros_version')}")
            print(f"Uptime: {device_info.get('uptime')}")
            print(f"CPU Load: {device_info.get('cpu_load')}")
            print()
            
            print(f"{Colors.HEADER}{Colors.BOLD}=== TỔNG QUAN VPN ==={Colors.ENDC}")
            print(f"IPSec Peers: {len(vpn_manager.get_ipsec_peers())}")
            print(f"IPSec Policies: {len(vpn_manager.get_ipsec_policies())}")
            print(f"OpenVPN Servers: {len(vpn_manager.get_ovpn_servers())}")
            print(f"OpenVPN Clients: {len(vpn_manager.get_ovpn_clients())}")
            print(f"L2TP Clients: {len(vpn_manager.get_l2tp_clients())}")
            print(f"PPTP Clients: {len(vpn_manager.get_pptp_clients())}")
            print(f"SSTP Clients: {len(vpn_manager.get_sstp_clients())}")
            print(f"PPP Users: {len(vpn_manager.get_ppp_secrets())}")
            print(f"Active Connections: {len(vpn_manager.get_active_connections())}")
            print()
            
            # Hiển thị trợ giúp
            parser.print_help()
    
    finally:
        # Đảm bảo ngắt kết nối
        vpn_manager.disconnect()


if __name__ == "__main__":
    main()