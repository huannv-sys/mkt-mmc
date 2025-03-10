import logging
from flask import Blueprint, render_template, request, jsonify
from models import (
    CAPInterface, CAPsMANChannel, CAPsMANDatapath,
    CAPsMANSecurity, RemoteCAP, CAPRegistration,
    CAPsMANRadio, CAPsMANProvisioning, CAPsMANConfiguration,
    db
)

logger = logging.getLogger(__name__)
capsman = Blueprint('capsman', __name__)

# CAP Interface routes
@capsman.route('/cap-interface')
def cap_interface():
    logger.debug("Accessing CAP Interface page")
    interfaces = CAPInterface.query.all()
    return render_template('cap_interface.html', interfaces=interfaces)

@capsman.route('/cap-interface/add', methods=['POST'])
def add_cap_interface():
    logger.debug("Adding new CAP Interface")
    try:
        data = request.form
        interface = CAPInterface(
            name=data['name'],
            mac_address=data.get('mac_address'),
            enabled=data.get('enabled', True),
            master_interface=data.get('master_interface'),
            configuration=data.get('configuration')
        )
        db.session.add(interface)
        db.session.commit()
        logger.info(f"Successfully added CAP Interface: {interface.name}")
        return jsonify({'success': True, 'message': 'Interface added successfully'})
    except Exception as e:
        logger.error(f"Error adding CAP Interface: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# Channel management routes
@capsman.route('/channel')
def channel():
    logger.debug("Accessing Channel Management page")
    channels = CAPsMANChannel.query.all()
    return render_template('channel.html', channels=channels)

@capsman.route('/channel/add', methods=['POST'])
def add_channel():
    logger.debug("Adding new Channel")
    try:
        data = request.form
        channel = CAPsMANChannel(
            name=data['name'],
            band=data.get('band'),
            frequency=data.get('frequency', type=int),
            width=data.get('width', type=int),
            tx_power=data.get('tx_power', type=int)
        )
        db.session.add(channel)
        db.session.commit()
        logger.info(f"Successfully added Channel: {channel.name}")
        return jsonify({'success': True, 'message': 'Channel added successfully'})
    except Exception as e:
        logger.error(f"Error adding Channel: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# Datapath management routes
@capsman.route('/datapath')
def datapath():
    logger.debug("Accessing Datapath Configuration page")
    datapaths = CAPsMANDatapath.query.all()
    return render_template('datapath.html', datapaths=datapaths)

@capsman.route('/datapath/add', methods=['POST'])
def add_datapath():
    logger.debug("Adding new Datapath")
    try:
        data = request.form
        datapath = CAPsMANDatapath(
            name=data['name'],
            bridge=data.get('bridge'),
            client_to_client_forwarding=data.get('client_to_client_forwarding', True),
            local_forwarding=data.get('local_forwarding', False)
        )
        db.session.add(datapath)
        db.session.commit()
        logger.info(f"Successfully added Datapath: {datapath.name}")
        return jsonify({'success': True, 'message': 'Datapath added successfully'})
    except Exception as e:
        logger.error(f"Error adding Datapath: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# Security management routes
@capsman.route('/security')
def security():
    logger.debug("Accessing Security Configuration page")
    security_configs = CAPsMANSecurity.query.all()
    return render_template('security.html', security_configs=security_configs)

@capsman.route('/security/add', methods=['POST'])
def add_security():
    logger.debug("Adding new Security Configuration")
    try:
        data = request.form
        security = CAPsMANSecurity(
            name=data['name'],
            authentication_types=data.get('authentication_types'),
            encryption=data.get('encryption'),
            group_encryption=data.get('group_encryption'),
            passphrase=data.get('passphrase')
        )
        db.session.add(security)
        db.session.commit()
        logger.info(f"Successfully added Security Configuration: {security.name}")
        return jsonify({'success': True, 'message': 'Security configuration added successfully'})
    except Exception as e:
        logger.error(f"Error adding Security Configuration: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# Remote CAP management routes
@capsman.route('/remote-cap')
def remote_cap():
    logger.debug("Accessing Remote CAP Management page")
    remote_caps = RemoteCAP.query.all()
    return render_template('remote_cap.html', remote_caps=remote_caps)

@capsman.route('/remote-cap/add', methods=['POST'])
def add_remote_cap():
    logger.debug("Adding new Remote CAP")
    try:
        data = request.form
        remote_cap = RemoteCAP(
            mac_address=data['mac_address'],
            name=data.get('name'),
            model=data.get('model'),
            version=data.get('version'),
            status=data.get('status', 'disconnected')
        )
        db.session.add(remote_cap)
        db.session.commit()
        logger.info(f"Successfully added Remote CAP: {remote_cap.mac_address}")
        return jsonify({'success': True, 'message': 'Remote CAP added successfully'})
    except Exception as e:
        logger.error(f"Error adding Remote CAP: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# Registration table routes
@capsman.route('/registration')
def registration():
    logger.debug("Accessing Registration table")
    registrations = (CAPRegistration.query
                    .join(RemoteCAP)
                    .join(CAPInterface)
                    .all())
    # Get lists for the registration form
    remote_caps = RemoteCAP.query.all()
    interfaces = CAPInterface.query.all()
    return render_template('registration.html', 
                         registrations=registrations,
                         remote_caps=remote_caps,
                         interfaces=interfaces)

@capsman.route('/registration/add', methods=['POST'])
def add_registration():
    logger.debug("Adding new Registration")
    try:
        data = request.form
        registration = CAPRegistration(
            remote_cap_id=data['remote_cap_id'],
            interface_id=data['interface_id'],
            status=data.get('status', 'registered')
        )
        db.session.add(registration)
        db.session.commit()
        logger.info(f"Successfully added Registration: Remote CAP ID {registration.remote_cap_id}, Interface ID {registration.interface_id}")
        return jsonify({'success': True, 'message': 'Registration added successfully'})
    except Exception as e:
        logger.error(f"Error adding Registration: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# Radio management routes
@capsman.route('/radio')
def radio():
    logger.debug("Accessing Radio Configuration page")
    radios = CAPsMANRadio.query.all()
    remote_caps = RemoteCAP.query.all()
    return render_template('radio.html', radios=radios, remote_caps=remote_caps)

@capsman.route('/radio/add', methods=['POST'])
def add_radio():
    logger.debug("Adding new Radio Configuration")
    try:
        data = request.form
        radio = CAPsMANRadio(
            name=data['name'],
            mac_address=data.get('mac_address'),
            mode=data.get('mode'),
            band=data.get('band'),
            channel_width=data.get('channel_width', type=int),
            frequency=data.get('frequency', type=int),
            tx_power=data.get('tx_power', type=int),
            antenna_gain=data.get('antenna_gain', type=float),
            remote_cap_id=data.get('remote_cap_id', type=int)
        )
        db.session.add(radio)
        db.session.commit()
        logger.info(f"Successfully added Radio Configuration: {radio.name}")
        return jsonify({'success': True, 'message': 'Radio configuration added successfully'})
    except Exception as e:
        logger.error(f"Error adding Radio Configuration: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# Provisioning management routes
@capsman.route('/provisioning')
def provisioning():
    logger.debug("Accessing Provisioning page")
    provisioning_tasks = CAPsMANProvisioning.query.all()
    remote_caps = RemoteCAP.query.all()
    return render_template('provisioning.html', 
                         provisioning_tasks=provisioning_tasks,
                         remote_caps=remote_caps)

@capsman.route('/provisioning/add', methods=['POST'])
def add_provisioning():
    logger.debug("Adding new Provisioning task")
    try:
        data = request.form
        task = CAPsMANProvisioning(
            name=data['name'],
            action=data.get('action'),
            target_version=data.get('target_version'),
            config_file=data.get('config_file'),
            remote_cap_id=data.get('remote_cap_id', type=int),
            status='pending'
        )
        db.session.add(task)
        db.session.commit()
        logger.info(f"Successfully added Provisioning task: {task.name}")
        return jsonify({'success': True, 'message': 'Provisioning task added successfully'})
    except Exception as e:
        logger.error(f"Error adding Provisioning task: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400