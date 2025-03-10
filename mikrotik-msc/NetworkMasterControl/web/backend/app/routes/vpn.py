import logging
from flask import Blueprint, render_template, request, jsonify
from models import (
    db, L2TPConfiguration, SSTPConfiguration,
    OpenVPNConfiguration, WireGuardConfiguration,
    VPNPeer
)

logger = logging.getLogger(__name__)
vpn = Blueprint('vpn', __name__, url_prefix='/vpn')

# L2TP/IPsec routes
@vpn.route('/l2tp')
def l2tp():
    logger.debug("Accessing L2TP/IPsec page")
    configs = L2TPConfiguration.query.all()
    peers = VPNPeer.query.filter_by(vpn_type='l2tp').all()
    return render_template('vpn/l2tp.html', 
                         active_tab='l2tp',
                         configs=configs,
                         peers=peers)

@vpn.route('/l2tp/add', methods=['POST'])
def add_l2tp():
    logger.debug("Adding new L2TP/IPsec Configuration")
    try:
        data = request.form
        config = L2TPConfiguration(
            name=data['name'],
            interface=data.get('interface'),
            local_address=data.get('local_address'),
            remote_address=data.get('remote_address'),
            authentication=data.get('authentication'),
            require_ipsec=data.get('require_ipsec', True, type=bool),
            ipsec_secret=data.get('ipsec_secret'),
            mtu=data.get('mtu', 1400, type=int),
            mru=data.get('mru', 1400, type=int),
            enabled=data.get('enabled', True, type=bool)
        )
        db.session.add(config)
        db.session.commit()
        logger.info(f"Successfully added L2TP Configuration: {config.name}")
        return jsonify({'success': True, 'message': 'L2TP configuration added successfully'})
    except Exception as e:
        logger.error(f"Error adding L2TP Configuration: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# SSTP routes
@vpn.route('/sstp')
def sstp():
    logger.debug("Accessing SSTP page")
    configs = SSTPConfiguration.query.all()
    return render_template('vpn/sstp.html', 
                         active_tab='sstp',
                         configs=configs)

@vpn.route('/sstp/add', methods=['POST'])
def add_sstp():
    logger.debug("Adding new SSTP Configuration")
    try:
        data = request.form
        config = SSTPConfiguration(
            name=data['name'],
            interface=data.get('interface'),
            local_address=data.get('local_address'),
            remote_address=data.get('remote_address'),
            mtu=data.get('mtu', 1400, type=int),
            mru=data.get('mru', 1400, type=int),
            certificate=data.get('certificate'),
            authentication=data.get('authentication'),
            verify_client_cert=data.get('verify_client_cert', False, type=bool),
            enabled=data.get('enabled', True, type=bool)
        )
        db.session.add(config)
        db.session.commit()
        logger.info(f"Successfully added SSTP Configuration: {config.name}")
        return jsonify({'success': True, 'message': 'SSTP configuration added successfully'})
    except Exception as e:
        logger.error(f"Error adding SSTP Configuration: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# OpenVPN routes
@vpn.route('/openvpn')
def openvpn():
    logger.debug("Accessing OpenVPN page")
    configs = OpenVPNConfiguration.query.all()
    return render_template('vpn/openvpn.html', 
                         active_tab='openvpn',
                         configs=configs)

@vpn.route('/openvpn/add', methods=['POST'])
def add_openvpn():
    logger.debug("Adding new OpenVPN Configuration")
    try:
        data = request.form
        config = OpenVPNConfiguration(
            name=data['name'],
            interface=data.get('interface'),
            port=data.get('port', 1194, type=int),
            protocol=data.get('protocol', 'udp'),
            mode=data.get('mode', 'server'),
            topology=data.get('topology', 'subnet'),
            ca_certificate=data.get('ca_certificate'),
            server_certificate=data.get('server_certificate'),
            server_key=data.get('server_key'),
            dh_params=data.get('dh_params'),
            cipher=data.get('cipher', 'AES-256-GCM'),
            enabled=data.get('enabled', True, type=bool)
        )
        db.session.add(config)
        db.session.commit()
        logger.info(f"Successfully added OpenVPN Configuration: {config.name}")
        return jsonify({'success': True, 'message': 'OpenVPN configuration added successfully'})
    except Exception as e:
        logger.error(f"Error adding OpenVPN Configuration: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# WireGuard routes
@vpn.route('/wireguard')
def wireguard():
    logger.debug("Accessing WireGuard page")
    configs = WireGuardConfiguration.query.all()
    return render_template('vpn/wireguard.html', 
                         active_tab='wireguard',
                         configs=configs)

@vpn.route('/wireguard/add', methods=['POST'])
def add_wireguard():
    logger.debug("Adding new WireGuard Configuration")
    try:
        data = request.form
        config = WireGuardConfiguration(
            name=data['name'],
            interface=data.get('interface'),
            private_key=data.get('private_key'),
            public_key=data.get('public_key'),
            listen_port=data.get('listen_port', 51820, type=int),
            address=data.get('address'),
            dns=data.get('dns'),
            mtu=data.get('mtu', 1420, type=int),
            enabled=data.get('enabled', True, type=bool)
        )
        db.session.add(config)
        db.session.commit()
        logger.info(f"Successfully added WireGuard Configuration: {config.name}")
        return jsonify({'success': True, 'message': 'WireGuard configuration added successfully'})
    except Exception as e:
        logger.error(f"Error adding WireGuard Configuration: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# VPN Peer management
@vpn.route('/peer/add', methods=['POST'])
def add_peer():
    logger.debug("Adding new VPN Peer")
    try:
        data = request.form
        peer = VPNPeer(
            name=data['name'],
            vpn_type=data['vpn_type'],
            username=data.get('username'),
            password=data.get('password'),
            public_key=data.get('public_key'),
            allowed_ips=data.get('allowed_ips'),
            endpoint=data.get('endpoint'),
            client_config=data.get('client_config'),
            enabled=True
        )
        db.session.add(peer)
        db.session.commit()
        logger.info(f"Successfully added VPN Peer: {peer.name}")
        return jsonify({'success': True, 'message': 'VPN peer added successfully'})
    except Exception as e:
        logger.error(f"Error adding VPN Peer: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400