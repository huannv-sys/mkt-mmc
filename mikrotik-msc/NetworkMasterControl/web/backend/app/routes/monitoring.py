import logging
from flask import Blueprint, render_template
from flask_socketio import emit
import psutil
from datetime import datetime
import threading
import time
from models import db, VPNMonitoring, VPNSession
from models import L2TPConfiguration, SSTPConfiguration, OpenVPNConfiguration, WireGuardConfiguration

logger = logging.getLogger(__name__)
monitoring = Blueprint('monitoring', __name__)

def get_vpn_stats(vpn_type, config_id):
    """Get VPN statistics for a specific configuration"""
    try:
        stats = {
            'bandwidth_in': psutil.net_io_counters().bytes_recv / 1024 / 1024,  # MB
            'bandwidth_out': psutil.net_io_counters().bytes_sent / 1024 / 1024,  # MB
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().used / 1024 / 1024,  # MB
            'active_sessions': VPNSession.query.filter_by(
                vpn_type=vpn_type,
                config_id=config_id,
                end_time=None
            ).count()
        }
        logger.debug(f"Retrieved stats for {vpn_type} config {config_id}: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Error getting VPN stats: {e}")
        return {
            'bandwidth_in': 0,
            'bandwidth_out': 0,
            'cpu_usage': 0,
            'memory_usage': 0,
            'active_sessions': 0
        }

@monitoring.route('/dashboard')
def dashboard():
    """Render the monitoring dashboard"""
    logger.info("Accessing monitoring dashboard")
    return render_template('monitoring/dashboard.html')

def emit_vpn_stats():
    """Emit VPN statistics for all configurations"""
    logger.debug("Emitting VPN stats")
    vpn_types = {
        'l2tp': L2TPConfiguration,
        'sstp': SSTPConfiguration,
        'openvpn': OpenVPNConfiguration,
        'wireguard': WireGuardConfiguration
    }

    all_stats = {}
    try:
        for vpn_type, model in vpn_types.items():
            configs = model.query.all()
            for config in configs:
                stats = get_vpn_stats(vpn_type, config.id)

                # Store monitoring data
                monitoring_data = VPNMonitoring(
                    vpn_type=vpn_type,
                    config_id=config.id,
                    connection_status='connected',  # Mock status for now
                    bandwidth_in=stats['bandwidth_in'],
                    bandwidth_out=stats['bandwidth_out'],
                    active_sessions=stats['active_sessions'],
                    cpu_usage=stats['cpu_usage'],
                    memory_usage=stats['memory_usage']
                )
                db.session.add(monitoring_data)

                all_stats[f"{vpn_type}_{config.id}"] = {
                    'name': config.name,
                    'type': vpn_type,
                    **stats
                }

        db.session.commit()
        emit('vpn_stats', all_stats, namespace='/monitoring', broadcast=True)
        logger.debug(f"Emitted stats: {all_stats}")
    except Exception as e:
        logger.error(f"Error emitting VPN stats: {e}")

def start_monitoring_loop():
    """Start a background thread to periodically emit VPN stats"""
    def monitoring_loop():
        while True:
            emit_vpn_stats()
            time.sleep(2)  # Update every 2 seconds

    thread = threading.Thread(target=monitoring_loop)
    thread.daemon = True
    thread.start()
    logger.info("Started VPN monitoring loop")