"""
MikroTik Management System Center
Main application file
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, g, send_file, abort, flash
from git import Repo
import datetime
import logging
import json
import os
import sys
import sqlite3
from werkzeug.utils import secure_filename

from utils import auth, notifications, mikrotik_utils, ip_monitoring

# Khởi tạo Flask app
app = Flask(__name__)
app.config.from_object('config')

# Thiết lập logging
logging.basicConfig(
    level=getattr(logging, app.config['LOG_LEVEL']),
    format=app.config['LOG_FORMAT'],
    datefmt=app.config['LOG_DATE_FORMAT'],
    handlers=[
        logging.FileHandler(app.config['LOG_FILE']),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Khởi tạo session
app.config['SESSION_TYPE'] = app.config['SESSION_TYPE']
app.config['UPLOAD_FOLDER'] = os.path.join(app.config['BASE_DIR'], 'uploads')

# Khởi tạo secret key
app.secret_key = app.config['SECRET_KEY']

# Tạo thư mục uploads nếu chưa tồn tại
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
@auth.login_required
def index():
    """Trang chủ"""
    # Dữ liệu phân tích repository
    repo_analysis = {
        'analysis_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'installation': {
            'compatible_os': ['Ubuntu 18.04+', 'Debian 10+', 'CentOS 8+'],
            'services': ['PostgreSQL', 'Nginx', 'Redis (tùy chọn)'],
            'database': 'SQLite (mặc định), PostgreSQL (cho môi trường production)',
            'requirements': [
                'Flask', 'JWT', 'bcrypt', 'SQLite', 'librouteros', 
                'requests', 'twilio', 'Jinja2', 'Werkzeug'
            ]
        },
        'components': [
            {
                'name': 'Quản lý xác thực',
                'file': 'utils/auth.py',
                'description': 'Xử lý đăng nhập, phân quyền và bảo mật'
            },
            {
                'name': 'MikroTik API',
                'file': 'utils/mikrotik_api.py',
                'description': 'Kết nối và tương tác với thiết bị MikroTik'
            },
            {
                'name': 'Giám sát IP',
                'file': 'utils/ip_monitoring.py',
                'description': 'Giám sát và quản lý trạng thái IP'
            },
            {
                'name': 'Thông báo',
                'file': 'utils/notifications.py',
                'description': 'Gửi thông báo qua SMS, email và Slack'
            },
            {
                'name': 'Utils MikroTik',
                'file': 'utils/mikrotik_utils.py',
                'description': 'Các tiện ích cho việc tương tác với MikroTik'
            }
        ]
    }
    return render_template('index.html', repo_analysis=repo_analysis)

@app.route('/dashboard')
@auth.login_required
def dashboard():
    """Trang dashboard"""
    return render_template('dashboard.html')

@app.route('/monitoring')
@auth.login_required
def monitoring():
    """Trang giám sát"""
    return render_template('monitoring.html')

@app.route('/clients')
@auth.login_required
def clients():
    """Trang quản lý client"""
    return render_template('clients.html')

@app.route('/interfaces')
@auth.login_required
def interfaces():
    """Trang quản lý interface"""
    return render_template('interfaces.html')

@app.route('/ip-monitor')
@auth.login_required
def ip_monitor():
    """Trang giám sát IP"""
    return render_template('ip_monitoring.html')

@app.route('/firewall')
@auth.login_required
def firewall():
    """Trang quản lý firewall"""
    return render_template('firewall.html')

@app.route('/vpn')
@auth.login_required
def vpn():
    """Trang quản lý VPN"""
    return render_template('vpn.html')

@app.route('/settings')
@auth.login_required
def settings():
    """Trang cài đặt chung"""
    return render_template('settings.html', 
                          current_year=datetime.datetime.now().year, 
                          version='1.0.0')

@app.route('/settings/mikrotik')
@auth.login_required
def settings_mikrotik():
    """Trang cài đặt kết nối MikroTik"""
    # Lấy thông tin hiện tại của MikroTik từ biến môi trường
    mikrotik_settings = {
        'host': os.getenv('MIKROTIK_HOST', '192.168.88.1'),
        'username': os.getenv('MIKROTIK_USERNAME', 'admin'),
        'password': os.getenv('MIKROTIK_PASSWORD', ''),
        'port': os.getenv('MIKROTIK_API_PORT', '8728'),
        'timeout': os.getenv('MIKROTIK_TIMEOUT', '10')
    }
    return render_template('settings/mikrotik.html', 
                          mikrotik_settings=mikrotik_settings,
                          current_year=datetime.datetime.now().year, 
                          version='1.0.0')

@app.route('/settings/notification')
@auth.login_required
def settings_notification():
    """Trang cài đặt thông báo"""
    # Lấy thông tin cài đặt thông báo từ biến môi trường
    notification_settings = {
        'email': {
            'enabled': os.getenv('EMAIL_ENABLED', 'false').lower() == 'true',
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': os.getenv('SMTP_PORT', '587'),
            'smtp_username': os.getenv('SMTP_USERNAME', ''),
            'smtp_password': os.getenv('SMTP_PASSWORD', ''),
            'default_recipients': os.getenv('DEFAULT_ADMIN_EMAIL', '').split(',')
        },
        'sms': {
            'enabled': os.getenv('SMS_ENABLED', 'false').lower() == 'true',
            'twilio_account_sid': os.getenv('TWILIO_ACCOUNT_SID', ''),
            'twilio_auth_token': os.getenv('TWILIO_AUTH_TOKEN', ''),
            'twilio_phone_number': os.getenv('TWILIO_PHONE_NUMBER', ''),
            'default_recipients': os.getenv('DEFAULT_SMS_RECIPIENTS', '').split(',')
        },
        'slack': {
            'enabled': os.getenv('SLACK_ENABLED', 'false').lower() == 'true',
            'webhook_url': os.getenv('SLACK_WEBHOOK_URL', '')
        }
    }
    return render_template('settings/notification.html', 
                          notification_settings=notification_settings,
                          current_year=datetime.datetime.now().year, 
                          version='1.0.0')

@app.route('/api/settings/mikrotik/test', methods=['POST'])
@auth.login_required
def test_mikrotik_connection():
    """API kiểm tra kết nối đến MikroTik"""
    try:
        data = request.json
        
        # Validate dữ liệu
        required_fields = ['host', 'username', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Thiếu trường {field}'})
        
        # Thiết lập các tham số kết nối
        host = data['host']
        username = data['username']
        password = data['password']
        port = int(data.get('port', 8728))
        timeout = int(data.get('timeout', 10))
        
        # Kiểm tra format của IP/hostname
        import socket
        try:
            socket.gethostbyname(host)
        except socket.gaierror:
            return jsonify({'success': False, 'error': f'Địa chỉ IP hoặc hostname không hợp lệ: {host}'})
        
        # Kiểm tra cổng có mở không
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  # Timeout nhanh hơn khi kiểm tra cổng
            result = sock.connect_ex((host, port))
            sock.close()
            if result != 0:
                return jsonify({'success': False, 'error': f'Không thể kết nối đến cổng {port} trên máy chủ {host}. Vui lòng kiểm tra lại cổng hoặc tường lửa.'})
        except Exception as e:
            logger.warning(f"Không thể kiểm tra cổng {port} trên {host}: {str(e)}")
            # Tiếp tục ngay cả khi không kiểm tra được cổng
        
        # Thiết lập kết nối thử nghiệm
        from librouteros import connect
        from librouteros.exceptions import ConnectionError, LoginError, TrapError
        
        try:
            # Thử kết nối với thông tin mới
            api = connect(
                username=username,
                password=password,
                host=host,
                port=port,
                timeout=timeout
            )
            
            # Lấy thông tin thiết bị để xác nhận kết nối thành công
            identity = api.path('/system/identity').get()[0]
            system_resource = api.path('/system/resource').get()[0]
            
            # Tính toán sử dụng bộ nhớ
            try:
                total_memory = int(system_resource.get('total-memory', 0))
                free_memory = int(system_resource.get('free-memory', 0))
                used_memory = total_memory - free_memory
                memory_percent = int((used_memory / total_memory) * 100) if total_memory > 0 else 0
                
                memory_info = {
                    'total': int(total_memory / 1024 / 1024),  # MB
                    'used': int(used_memory / 1024 / 1024),    # MB
                    'free': int(free_memory / 1024 / 1024),    # MB
                    'percent': memory_percent
                }
            except (ValueError, ZeroDivisionError) as e:
                logger.warning(f"Lỗi khi tính toán bộ nhớ: {str(e)}")
                memory_info = {
                    'total': 0,
                    'used': 0,
                    'free': 0,
                    'percent': 0
                }
            
            device_info = {
                'name': identity.get('name', 'Unknown'),
                'model': system_resource.get('board-name', 'Unknown'),
                'firmware': system_resource.get('version', 'Unknown'),
                'uptime': system_resource.get('uptime', 'Unknown'),
                'cpu_load': system_resource.get('cpu-load', 0),
                'memory': memory_info
            }
            
            # Đóng kết nối
            api.close()
            
            return jsonify({
                'success': True, 
                'message': f'Kết nối thành công đến thiết bị {device_info["name"]}',
                'device_info': device_info
            })
            
        except LoginError:
            logger.error(f"Lỗi xác thực khi kết nối đến MikroTik: {host}")
            return jsonify({'success': False, 'error': 'Sai tên đăng nhập hoặc mật khẩu'})
        except ConnectionError:
            logger.error(f"Lỗi kết nối đến MikroTik: {host}")
            return jsonify({'success': False, 'error': f'Không thể kết nối đến thiết bị MikroTik {host}:{port}. Vui lòng kiểm tra lại cài đặt mạng.'})
        except TrapError as e:
            logger.error(f"MikroTik trap error: {host} - {str(e)}")
            return jsonify({'success': False, 'error': f'Lỗi từ MikroTik: {str(e)}'})
        except Exception as e:
            logger.error(f"Lỗi không xác định khi kết nối đến MikroTik: {host} - {str(e)}")
            return jsonify({'success': False, 'error': f'Lỗi kết nối: {str(e)}'})
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra kết nối MikroTik: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings/mikrotik/save', methods=['POST'])
@auth.login_required
@auth.admin_required
def save_mikrotik_settings():
    """API lưu cài đặt kết nối MikroTik"""
    try:
        data = request.json
        
        # Validate dữ liệu
        required_fields = ['host', 'username', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Thiếu trường {field}'})
        
        # Đọc file .env hiện tại nếu tồn tại
        env_data = {}
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        env_data[key] = value
        
        # Cập nhật cài đặt MikroTik
        env_data["MIKROTIK_HOST"] = data['host']
        env_data["MIKROTIK_USERNAME"] = data['username']
        env_data["MIKROTIK_PASSWORD"] = data['password']
        env_data["MIKROTIK_API_PORT"] = str(data.get('port', 8728))
        env_data["MIKROTIK_TIMEOUT"] = str(data.get('timeout', 10))
        
        # Lưu lại file .env
        with open('.env', 'w') as f:
            for key, value in env_data.items():
                f.write(f"{key}={value}\n")
        
        # Tải lại biến môi trường
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        logger.info(f"Đã lưu cài đặt kết nối MikroTik mới")
        return jsonify({'success': True, 'message': 'Cài đặt đã được lưu thành công'})
    
    except Exception as e:
        logger.error(f"Lỗi khi lưu cài đặt MikroTik: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings/notification/sms', methods=['GET'])
@auth.login_required
def get_notification_sms_settings():
    """API lấy cài đặt thông báo SMS"""
    try:
        settings = {
            'enabled': os.getenv('SMS_ENABLED', 'false').lower() == 'true',
            'twilio_account_sid': os.getenv('TWILIO_ACCOUNT_SID', ''),
            'twilio_auth_token': os.getenv('TWILIO_AUTH_TOKEN', ''),
            'twilio_phone_number': os.getenv('TWILIO_PHONE_NUMBER', ''),
            'default_recipients': os.getenv('DEFAULT_SMS_RECIPIENTS', '')
        }
        
        # Che dấu thông tin nhạy cảm
        if settings['twilio_auth_token']:
            settings['twilio_auth_token'] = '••••••••' + settings['twilio_auth_token'][-4:] if len(settings['twilio_auth_token']) > 4 else '••••••••'
        
        return jsonify({'success': True, 'settings': settings})
    
    except Exception as e:
        logger.error(f"Lỗi khi lấy cài đặt thông báo SMS: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings/notification/sms/save', methods=['POST'])
@auth.login_required
@auth.admin_required
def save_notification_sms_settings():
    """API lưu cài đặt thông báo SMS"""
    try:
        data = request.json
        
        # Validate dữ liệu
        if 'enabled' not in data:
            return jsonify({'success': False, 'error': 'Thiếu trường enabled'})
        
        # Đọc file .env hiện tại nếu tồn tại
        env_data = {}
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        env_data[key] = value
        
        # Cập nhật cài đặt SMS
        env_data["SMS_ENABLED"] = str(data['enabled']).lower()
        
        if data['enabled']:
            if 'twilio_account_sid' in data and data['twilio_account_sid']:
                env_data["TWILIO_ACCOUNT_SID"] = data['twilio_account_sid']
            
            if 'twilio_auth_token' in data and data['twilio_auth_token']:
                env_data["TWILIO_AUTH_TOKEN"] = data['twilio_auth_token']
            
            if 'twilio_phone_number' in data and data['twilio_phone_number']:
                env_data["TWILIO_PHONE_NUMBER"] = data['twilio_phone_number']
            
            if 'default_recipients' in data and data['default_recipients']:
                env_data["DEFAULT_SMS_RECIPIENTS"] = data['default_recipients']
        
        # Lưu lại file .env
        with open('.env', 'w') as f:
            for key, value in env_data.items():
                f.write(f"{key}={value}\n")
        
        # Tải lại biến môi trường
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        # Nếu SMS được bật, khởi tạo lại client Twilio
        if data['enabled']:
            notifications.init_twilio_client()
        
        logger.info(f"Đã lưu cài đặt thông báo SMS mới")
        return jsonify({'success': True, 'message': 'Cài đặt thông báo SMS đã được lưu thành công'})
    
    except Exception as e:
        logger.error(f"Lỗi khi lưu cài đặt thông báo SMS: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/notifications/test-sms', methods=['POST'])
@auth.login_required
def test_sms_notification():
    """API gửi tin nhắn SMS thử nghiệm"""
    try:
        data = request.json
        
        # Validate dữ liệu
        required_fields = ['phone_number', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Thiếu trường {field}'})
        
        phone_number = data['phone_number']
        message = data['message']
        
        # Sử dụng cài đặt Twilio tạm thời nếu được cung cấp
        if 'twilio_settings' in data and data['twilio_settings']:
            twilio_settings = data['twilio_settings']
            account_sid = twilio_settings.get('account_sid')
            auth_token = twilio_settings.get('auth_token')
            from_number = twilio_settings.get('phone_number')
            
            # Sử dụng cài đặt tạm thời để gửi tin nhắn
            success = notifications.send_sms_notification(
                phone_number=phone_number,
                message=message,
                account_sid=account_sid,
                auth_token=auth_token,
                from_number=from_number
            )
        else:
            # Sử dụng cài đặt mặc định
            success = notifications.send_sms_notification(phone_number, message)
        
        if success:
            return jsonify({'success': True, 'message': f'Đã gửi tin nhắn thử nghiệm đến {phone_number}'})
        else:
            return jsonify({'success': False, 'error': 'Không thể gửi tin nhắn thử nghiệm'})
    
    except Exception as e:
        logger.error(f"Lỗi khi gửi tin nhắn thử nghiệm: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/backup')
@auth.login_required
def backup():
    """Trang quản lý backup"""
    return render_template('backup/manager.html')

# Backup/Restore API Endpoints
@app.route('/api/backup/list', methods=['GET'])
@auth.login_required
def api_backup_list():
    """API lấy danh sách các bản backup"""
    try:
        # Kiểm tra và tạo thư mục backup nếu không tồn tại
        backup_dir = os.path.join(os.getcwd(), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        # Lấy danh sách các file backup
        backup_files = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.rsc') or filename.endswith('.backup'):
                file_path = os.path.join(backup_dir, filename)
                file_stat = os.stat(file_path)
                
                # Tạo object chứa thông tin file
                file_info = {
                    'name': filename,
                    'path': file_path,
                    'size': file_stat.st_size,
                    'created': datetime.datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                    'modified': datetime.datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'type': 'export' if filename.endswith('.rsc') else 'backup'
                }
                
                backup_files.append(file_info)
                
        # Sắp xếp theo thời gian sửa đổi mới nhất
        backup_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': backup_files
        })
    
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách backup: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/backup/create', methods=['POST'])
@auth.login_required
def api_create_backup():
    """API tạo backup mới từ thiết bị MikroTik"""
    try:
        data = request.json
        backup_type = data.get('type', 'backup')  # 'backup' hoặc 'export'
        include_sensitive = data.get('include_sensitive', False)
        name = data.get('name', f"mikrotik_{backup_type}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
        schedule_type = data.get('schedule_type', 'now')
        device_id = data.get('device_id', 'current')
        
        # Xử lý thông tin lịch nếu là backup theo lịch
        if schedule_type == 'scheduled':
            # Lấy thông tin lịch
            schedule_date = data.get('schedule_date', datetime.datetime.now().strftime('%Y-%m-%d'))
            schedule_time = data.get('schedule_time', '00:00')
            schedule_recurring = data.get('schedule_recurring', False)
            schedule_interval = data.get('schedule_interval', 'daily')
            
            # Lưu lịch vào tệp hoặc cơ sở dữ liệu
            schedule_file = os.path.join(os.getcwd(), 'backups', 'schedules.json')
            schedules = []
            
            # Đọc tệp lịch đã có nếu tồn tại
            if os.path.exists(schedule_file):
                with open(schedule_file, 'r') as f:
                    schedules = json.load(f)
            
            # Thêm lịch mới
            schedule_id = len(schedules) + 1
            schedules.append({
                'id': schedule_id,
                'type': backup_type,
                'name': name,
                'device_id': device_id,
                'include_sensitive': include_sensitive,
                'date': schedule_date,
                'time': schedule_time,
                'recurring': schedule_recurring,
                'interval': schedule_interval if schedule_recurring else None,
                'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'pending'
            })
            
            # Lưu lại tệp lịch
            os.makedirs(os.path.join(os.getcwd(), 'backups'), exist_ok=True)
            with open(schedule_file, 'w') as f:
                json.dump(schedules, f, indent=4)
            
            return jsonify({
                'success': True,
                'message': f'Đã lên lịch tạo {backup_type} vào {schedule_date} {schedule_time}',
                'scheduled': True,
                'schedule_id': schedule_id
            })
            
        # Kiểm tra và tạo thư mục backup nếu không tồn tại
        backup_dir = os.path.join(os.getcwd(), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Kết nối đến MikroTik
        device = mikrotik_utils.get_mikrotik_connection()
        if not device:
            return jsonify({'success': False, 'error': 'Không thể kết nối đến MikroTik'})
        
        # Chuẩn bị tham số cho API command
        if backup_type == 'backup':
            # Thêm phần mở rộng .backup nếu chưa có
            if not name.endswith('.backup'):
                name += '.backup'
                
            file_path = os.path.join(backup_dir, name)
            
            # Tạo backup file
            device.system.backup.save(name=name)
            
            # Tạo filename để download backup
            download_filename = name
            
        else:  # export
            # Thêm phần mở rộng .rsc nếu chưa có
            if not name.endswith('.rsc'):
                name += '.rsc'
                
            file_path = os.path.join(backup_dir, name)
            
            # Tạo export file
            cmd = '/export'
            if not include_sensitive:
                cmd += ' hide-sensitive'
            
            export_result = device.command(cmd)
            
            # Lưu kết quả export vào file
            with open(file_path, 'w') as f:
                for line in export_result:
                    f.write(line + '\n')
            
            # Tạo filename để download export
            download_filename = name
        
        # Tạo file_info để trả về
        file_stat = os.stat(file_path)
        file_info = {
            'name': name,
            'path': file_path,
            'size': file_stat.st_size,
            'created': datetime.datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
            'modified': datetime.datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'type': backup_type,
            'device_id': device_id
        }
        
        logger.info(f"Đã tạo {backup_type} file: {name}")
        return jsonify({
            'success': True,
            'message': f'Đã tạo {backup_type} thành công',
            'data': file_info,
            'scheduled': False
        })
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo backup: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/backup/download/<filename>', methods=['GET'])
@auth.login_required
def api_download_backup(filename):
    """API tải xuống file backup/export"""
    try:
        # Kiểm tra và xác nhận đường dẫn file
        backup_dir = os.path.join(os.getcwd(), 'backups')
        file_path = os.path.join(backup_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'File không tồn tại'})
        
        # Xác định loại file
        file_type = 'application/octet-stream'
        if filename.endswith('.rsc'):
            file_type = 'text/plain'
        
        return send_file(file_path, 
                         mimetype=file_type, 
                         as_attachment=True, 
                         download_name=filename)
    
    except Exception as e:
        logger.error(f"Lỗi khi tải xuống backup {filename}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/backup/restore', methods=['POST'])
@auth.login_required
@auth.admin_required
def api_restore_backup():
    """API khôi phục từ file backup/export"""
    try:
        data = request.json
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'success': False, 'error': 'Thiếu tên file'})
        
        # Xác định đường dẫn file
        backup_dir = os.path.join(os.getcwd(), 'backups')
        file_path = os.path.join(backup_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'File không tồn tại'})
        
        # Kết nối đến MikroTik
        device = mikrotik_utils.get_mikrotik_connection()
        if not device:
            return jsonify({'success': False, 'error': 'Không thể kết nối đến MikroTik'})
        
        # Xác định loại file và khôi phục theo cách phù hợp
        if filename.endswith('.backup'):
            # Upload và restore backup file
            device.file.upload(file=file_path, name=filename)
            device.system.backup.load(name=filename)
            
            message = "Đã khôi phục thiết bị từ file backup. Thiết bị sẽ khởi động lại."
            
        elif filename.endswith('.rsc'):
            # Đọc nội dung file export và thực thi từng dòng
            with open(file_path, 'r') as f:
                export_content = f.read()
            
            # Thực thi script
            device.command('/import', input=export_content)
            
            message = "Đã áp dụng cấu hình từ file export."
            
        else:
            return jsonify({
                'success': False, 
                'error': 'Định dạng file không được hỗ trợ. Chỉ hỗ trợ .backup hoặc .rsc'
            })
        
        logger.info(f"Đã khôi phục từ file {filename}")
        return jsonify({
            'success': True,
            'message': message
        })
    
    except Exception as e:
        logger.error(f"Lỗi khi khôi phục backup: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/backup/delete/<filename>', methods=['DELETE'])
@auth.login_required
@auth.admin_required
def api_delete_backup(filename):
    """API xóa file backup/export"""
    try:
        # Xác định đường dẫn file
        backup_dir = os.path.join(os.getcwd(), 'backups')
        file_path = os.path.join(backup_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'File không tồn tại'})
        
        # Xóa file
        os.remove(file_path)
        
        logger.info(f"Đã xóa file {filename}")
        return jsonify({
            'success': True,
            'message': f'Đã xóa file {filename}'
        })
    
    except Exception as e:
        logger.error(f"Lỗi khi xóa backup {filename}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/backup/upload', methods=['POST'])
@auth.login_required
def api_upload_backup():
    """API tải lên file backup/export"""
    try:
        # Kiểm tra nếu không có file nào được tải lên
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Không có file nào được tải lên'})
        
        uploaded_file = request.files['file']
        
        # Kiểm tra nếu không chọn file
        if uploaded_file.filename == '':
            return jsonify({'success': False, 'error': 'Không có file nào được chọn'})
        
        # Kiểm tra và tạo thư mục backup nếu không tồn tại
        backup_dir = os.path.join(os.getcwd(), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Kiểm tra định dạng file
        if not (uploaded_file.filename.endswith('.backup') or uploaded_file.filename.endswith('.rsc')):
            return jsonify({
                'success': False, 
                'error': 'Định dạng file không được hỗ trợ. Chỉ hỗ trợ .backup hoặc .rsc'
            })
        
        # Lưu file
        filename = werkzeug.utils.secure_filename(uploaded_file.filename)
        file_path = os.path.join(backup_dir, filename)
        uploaded_file.save(file_path)
        
        # Tạo file_info để trả về
        file_stat = os.stat(file_path)
        file_info = {
            'name': filename,
            'path': file_path,
            'size': file_stat.st_size,
            'created': datetime.datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
            'modified': datetime.datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'type': 'backup' if filename.endswith('.backup') else 'export'
        }
        
        logger.info(f"Đã tải lên file {filename}")
        return jsonify({
            'success': True,
            'message': f'Đã tải lên file {filename} thành công',
            'data': file_info
        })
    
    except Exception as e:
        logger.error(f"Lỗi khi tải lên backup: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/logs')
@auth.login_required
def logs():
    """Trang quản lý log"""
    return render_template('logs/system.html')

# API routes
@app.route('/api/ip/list')
@auth.login_required
def api_ip_list():
    """API lấy danh sách IP"""
    try:
        # Lấy danh sách IP từ MikroTik
        device = mikrotik_utils.get_mikrotik_connection()
        if not device:
            return jsonify({'success': False, 'error': 'Không thể kết nối đến MikroTik'})
            
        ip_addresses = device.ip.address.get()
        
        # Xử lý và định dạng dữ liệu
        ips = []
        stats = {
            'total': 0,
            'active': 0,
            'inactive': 0,
            'monitored': 0
        }
        
        for ip in ip_addresses:
            ip_data = {
                'address': ip.get('address'),
                'interface': ip.get('interface'),
                'mac_address': mikrotik_utils.get_mac_address(ip.get('interface')),
                'status': 'active' if mikrotik_utils.is_ip_active(ip.get('address')) else 'inactive',
                'traffic_in': mikrotik_utils.get_interface_traffic(ip.get('interface'), 'in'),
                'traffic_out': mikrotik_utils.get_interface_traffic(ip.get('interface'), 'out'),
                'last_seen': mikrotik_utils.get_last_seen(ip.get('address')),
                'monitoring': ip_monitoring.is_ip_monitored(ip.get('address'))
            }
            
            ips.append(ip_data)
            
            # Cập nhật thống kê
            stats['total'] += 1
            if ip_data['status'] == 'active':
                stats['active'] += 1
            else:
                stats['inactive'] += 1
            if ip_data['monitoring']:
                stats['monitored'] += 1
        
        # Lấy dữ liệu cho biểu đồ
        charts = {
            'traffic': mikrotik_utils.get_traffic_chart_data(),
            'distribution': mikrotik_utils.get_ip_distribution_data()
        }
        
        return jsonify({
            'success': True,
            'data': {
                'ips': ips,
                'stats': stats,
                'charts': charts
            }
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách IP: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ip/<ip_address>')
@auth.login_required
def api_ip_details(ip_address):
    """API lấy chi tiết IP"""
    try:
        # Lấy thông tin chi tiết về IP từ MikroTik
        device = mikrotik_utils.get_mikrotik_connection()
        if not device:
            return jsonify({'success': False, 'error': 'Không thể kết nối đến MikroTik'})
            
        ip_data = device.ip.address.get(address=ip_address)
        
        if not ip_data:
            return jsonify({'success': False, 'error': 'IP không tồn tại'})
        
        # Lấy thông tin bổ sung
        interface = ip_data[0].get('interface')
        mac_address = mikrotik_utils.get_mac_address(interface)
        
        # Lấy lịch sử của IP
        history = ip_monitoring.get_ip_history(ip_address)
        
        # Tạo đối tượng response
        response = {
            'address': ip_address,
            'interface': interface,
            'mac_address': mac_address,
            'status': 'active' if mikrotik_utils.is_ip_active(ip_address) else 'inactive',
            'traffic_in': mikrotik_utils.get_interface_traffic(interface, 'in'),
            'traffic_out': mikrotik_utils.get_interface_traffic(interface, 'out'),
            'last_seen': mikrotik_utils.get_last_seen(ip_address),
            'monitoring': ip_monitoring.is_ip_monitored(ip_address),
            'history': history
        }
        
        return jsonify({'success': True, 'data': response})
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin IP {ip_address}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ip/add', methods=['POST'])
@auth.login_required
def api_add_ip():
    """API thêm IP mới"""
    try:
        data = request.json
        
        # Validate dữ liệu
        required_fields = ['address', 'interface']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Thiếu trường {field}'})
        
        # Thêm IP vào MikroTik
        device = mikrotik_utils.get_mikrotik_connection()
        if not device:
            return jsonify({'success': False, 'error': 'Không thể kết nối đến MikroTik'})
            
        device.ip.address.add(
            address=data['address'],
            interface=data['interface']
        )
        
        # Bật monitoring nếu được yêu cầu
        if data.get('monitoring'):
            ip_monitoring.enable_ip_monitoring(data['address'])
        
        logger.info(f"Đã thêm IP {data['address']}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Lỗi khi thêm IP: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ip/<ip_address>', methods=['DELETE'])
@auth.login_required
def api_delete_ip(ip_address):
    """API xóa IP"""
    try:
        # Xóa IP khỏi MikroTik
        device = mikrotik_utils.get_mikrotik_connection()
        if not device:
            return jsonify({'success': False, 'error': 'Không thể kết nối đến MikroTik'})
            
        device.ip.address.remove(address=ip_address)
        
        # Tắt monitoring nếu đang bật
        ip_monitoring.disable_ip_monitoring(ip_address)
        
        logger.info(f"Đã xóa IP {ip_address}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Lỗi khi xóa IP {ip_address}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ip/search')
@auth.login_required
def api_search_ip():
    """API tìm kiếm IP"""
    try:
        query = request.args.get('q', '')
        
        # Tìm kiếm IP từ MikroTik
        device = mikrotik_utils.get_mikrotik_connection()
        if not device:
            return jsonify({'success': False, 'error': 'Không thể kết nối đến MikroTik'})
            
        ip_addresses = device.ip.address.get()
        
        # Lọc kết quả theo query
        results = []
        for ip in ip_addresses:
            if query.lower() in ip.get('address', '').lower() or \
               query.lower() in ip.get('interface', '').lower():
                ip_data = {
                    'address': ip.get('address'),
                    'interface': ip.get('interface'),
                    'mac_address': mikrotik_utils.get_mac_address(ip.get('interface')),
                    'status': 'active' if mikrotik_utils.is_ip_active(ip.get('address')) else 'inactive',
                    'traffic_in': mikrotik_utils.get_interface_traffic(ip.get('interface'), 'in'),
                    'traffic_out': mikrotik_utils.get_interface_traffic(ip.get('interface'), 'out'),
                    'last_seen': mikrotik_utils.get_last_seen(ip.get('address')),
                    'monitoring': ip_monitoring.is_ip_monitored(ip.get('address'))
                }
                results.append(ip_data)
        
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm IP: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

# Route cho xác thực
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Trang đăng nhập"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        # Mô phỏng xác thực
        if username == 'admin' and password == 'admin':
            # Tạo token JWT và lưu vào session
            token = auth.generate_token('1', username, 'admin')
            session['token'] = token
            
            if remember:
                # Cài đặt cookie lâu dài (30 ngày)
                session.permanent = True
                app.permanent_session_lifetime = datetime.timedelta(days=30)
            
            # Redirect đến trang chính
            return redirect(url_for('index'))
        else:
            # Đăng nhập thất bại
            return render_template('auth/login.html', 
                                error='Tên đăng nhập hoặc mật khẩu không chính xác', 
                                current_year=datetime.datetime.now().year, 
                                version='1.0.0')
    
    # Hiển thị trang đăng nhập
    return render_template('auth/login.html', 
                        current_year=datetime.datetime.now().year, 
                        version='1.0.0')

@app.route('/logout')
def logout():
    """Đăng xuất"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/test-sms', methods=['GET'])
def test_sms():
    """Trang thử nghiệm gửi SMS"""
    return render_template('test_sms.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Trang quên mật khẩu"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        # TODO: Gửi email reset mật khẩu
        notifications.send_email_notification(
            subject='Đặt lại mật khẩu MikroTik MSC',
            message='Hướng dẫn đặt lại mật khẩu của bạn.',
            recipients=[email]
        )
        
        # Thông báo thành công
        return render_template('auth/forgot_password.html', 
                            success='Hướng dẫn đặt lại mật khẩu đã được gửi đến email của bạn.',
                            current_year=datetime.datetime.now().year, 
                            version='1.0.0')
    
    # Hiển thị form quên mật khẩu
    return render_template('auth/forgot_password.html', 
                        current_year=datetime.datetime.now().year, 
                        version='1.0.0')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Trang đặt lại mật khẩu"""
    # TODO: Xác thực token và xử lý đặt lại mật khẩu
    return redirect(url_for('login'))

# Middleware để bảo vệ routes
@app.before_request
def check_authentication():
    """Kiểm tra xác thực cho mọi request"""
    # Danh sách các routes không yêu cầu xác thực
    public_routes = ['/login', '/logout', '/forgot-password', '/static', '/favicon.ico', '/test-sms', '/api/notifications/test-sms']
    
    # Cho phép truy cập các routes công khai
    for route in public_routes:
        if request.path.startswith(route):
            return None
    
    # Kiểm tra xác thực cho các routes khác
    if 'token' not in session:
        return redirect(url_for('login'))
    
    # Xác thực token
    user_data = auth.decode_token(session['token'])
    if not user_data:
        session.clear()
        return redirect(url_for('login'))
    
    # Lưu thông tin người dùng vào g để sử dụng trong request
    g.user = user_data
    
    return None

# Xử lý lỗi
@app.errorhandler(404)
def page_not_found(e):
    """Trang không tồn tại"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Lỗi máy chủ"""
    error_info = None
    if app.debug:
        error_info = str(e)
    return render_template('errors/500.html', error_info=error_info, debug=app.debug), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)