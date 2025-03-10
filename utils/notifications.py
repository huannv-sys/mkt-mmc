"""
Module quản lý thông báo
"""

import os
import json
import logging
import smtplib
import requests
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Khởi tạo logger
logger = logging.getLogger(__name__)

# Khởi tạo Twilio client
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

twilio_client = None

def init_twilio_client():
    """Khởi tạo Twilio client"""
    global twilio_client, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
    
    # Cập nhật biến môi trường từ hệ thống
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
    
    # Tạo client mới nếu có đủ thông tin
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        try:
            twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            logger.info("Đã khởi tạo Twilio client thành công")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo Twilio client: {str(e)}")
            twilio_client = None
            return False
    else:
        logger.warning("Thiếu thông tin để khởi tạo Twilio client")
        twilio_client = None
        return False

# Khởi tạo client khi import module
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    init_twilio_client()

def send_sms_notification(phone_number, message, max_retries=3, retry_delay=2, account_sid=None, auth_token=None, from_number=None):
    """Gửi thông báo qua SMS sử dụng Twilio với cơ chế retry
    
    Args:
        phone_number (str): Số điện thoại nhận SMS
        message (str): Nội dung tin nhắn
        max_retries (int): Số lần thử lại tối đa
        retry_delay (int): Thời gian chờ giữa các lần thử (giây)
        account_sid (str, optional): Twilio Account SID tạm thời
        auth_token (str, optional): Twilio Auth Token tạm thời
        from_number (str, optional): Số điện thoại gửi Twilio tạm thời
        
    Returns:
        bool: True nếu gửi tin nhắn thành công, False nếu thất bại
    """
    # Kiểm tra cấu hình Twilio
    global twilio_client, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
    
    # Khởi tạo client tạm thời nếu có cung cấp thông tin
    temp_client = None
    temp_from_number = None
    
    if account_sid and auth_token:
        try:
            temp_client = Client(account_sid, auth_token)
            temp_from_number = from_number
            logger.info("Đã khởi tạo Twilio client tạm thời")
        except Exception as e:
            logger.error(f"Không thể khởi tạo Twilio client tạm thời: {str(e)}")
            temp_client = None
    
    # Sử dụng client tạm thời hoặc thử tạo lại client mặc định nếu chưa có
    if not temp_client and not twilio_client:
        TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
        TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
        TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
        
        if all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
            try:
                twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            except Exception as e:
                logger.error(f"Không thể khởi tạo Twilio client: {str(e)}")
    
    # Chọn client để sử dụng
    client_to_use = temp_client if temp_client else twilio_client
    phone_from = temp_from_number if temp_from_number else TWILIO_PHONE_NUMBER
    
    if not client_to_use or not phone_from:
        logger.error("Chưa cấu hình đầy đủ thông tin Twilio")
        return False
    
    # Định dạng số điện thoại
    if not phone_number.startswith('+'):
        phone_number = f"+{phone_number}"
    
    # Kiểm tra xem số điện thoại người nhận có trùng với số gửi không
    if phone_from and phone_number == phone_from:
        logger.error(f"Số điện thoại người nhận và người gửi không thể giống nhau: {phone_number}")
        return False
    
    # Rút gọn tin nhắn nếu quá dài
    if len(message) > 1600:  # Twilio có giới hạn kích thước tin nhắn
        message = message[:1597] + "..."
    
    # Thử gửi tin nhắn với số lần thử lại
    retry_count = 0
    last_error = None
    import time
    
    while retry_count < max_retries:
        try:
            # Sử dụng client được chọn
            result = client_to_use.messages.create(
                body=message,
                from_=phone_from,
                to=phone_number
            )
            
            logger.info(f"Đã gửi SMS thành công đến {phone_number}: {result.sid}")
            return True
            
        except TwilioRestException as e:
            retry_count += 1
            last_error = e
            
            # Phân tích lỗi
            error_code = getattr(e, 'code', None)
            error_msg = str(e)
            
            # Xử lý các lỗi theo mã
            if error_code == 21211:  # Số điện thoại không hợp lệ
                logger.error(f"Số điện thoại không hợp lệ: {phone_number}")
                return False  # Không cần thử lại
                
            elif error_code == 21608:  # Số điện thoại không được xác nhận
                logger.error(f"Số điện thoại Twilio chưa được xác nhận để gửi SMS đến {phone_number}")
                return False  # Không cần thử lại
                
            elif error_code == 21612:  # Twilio trial account chỉ gửi được tới số đã xác nhận
                logger.error(f"Tài khoản Twilio thử nghiệm chỉ có thể gửi SMS đến số điện thoại đã xác nhận")
                return False  # Không cần thử lại
            
            logger.warning(f"Lần thử {retry_count}/{max_retries} gửi SMS thất bại: {error_msg}")
            
            if retry_count < max_retries:
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Tăng thời gian chờ mỗi lần thử
    
    # Ghi log chi tiết về lỗi cuối cùng
    logger.error(f"Không thể gửi SMS sau {max_retries} lần thử: {str(last_error)}")
    return False

def send_email_notification(subject, message, recipients=None):
    """Gửi thông báo qua email"""
    if not recipients:
        recipients = [os.getenv('DEFAULT_ADMIN_EMAIL')]
    
    try:
        # Cấu hình SMTP
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        if not all([smtp_server, smtp_port, smtp_username, smtp_password]):
            logger.error("Thiếu thông tin cấu hình SMTP")
            return False
        
        # Tạo email
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = smtp_username
        msg['To'] = ', '.join(recipients)
        msg.attach(MIMEText(message, 'html'))
        
        # Gửi email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        logger.info(f"Đã gửi email đến {recipients}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi gửi email: {str(e)}")
        return False

def send_slack_notification(title, message):
    """Gửi thông báo qua Slack webhook"""
    slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not slack_webhook_url:
        logger.error("Chưa cấu hình Slack webhook")
        return False
    
    try:
        payload = {
            "text": f"*{title}*\n{message}",
            "mrkdwn": True
        }
        response = requests.post(slack_webhook_url, json=payload)
        response.raise_for_status()
        
        logger.info("Đã gửi thông báo đến Slack")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Lỗi khi gửi thông báo đến Slack: {str(e)}")
        return False

def send_system_notification(title, message, level='info', notify_email=True, notify_slack=True, notify_sms=False, phone_numbers=None):
    """Gửi thông báo hệ thống"""
    # Log thông báo
    log_func = getattr(logger, level, logger.info)
    log_func(f"{title}: {message}")
    
    # Tạo nội dung thông báo
    notification_text = f"{title}\n\n{message}\n\nThời gian: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Gửi thông báo qua các kênh
    results = []
    
    if notify_email:
        email_success = send_email_notification(title, notification_text)
        results.append(('email', email_success))
    
    if notify_slack:
        slack_success = send_slack_notification(title, message)
        results.append(('slack', slack_success))
    
    if notify_sms and phone_numbers:
        for phone in phone_numbers:
            sms_success = send_sms_notification(phone, notification_text)
            results.append(('sms', sms_success))
    
    return all(success for _, success in results)

def notify_device_connection_status(device_name, status, ip_address=None):
    """Thông báo về trạng thái kết nối thiết bị"""
    title = f"Trạng thái thiết bị: {device_name}"
    message = f"Thiết bị {device_name}"
    if ip_address:
        message += f" ({ip_address})"
    message += f" hiện đang {status}"
    
    level = 'warning' if status.lower() == 'offline' else 'info'
    notify_sms = status.lower() == 'offline'  # Chỉ gửi SMS khi thiết bị offline
    
    return send_system_notification(
        title=title,
        message=message,
        level=level,
        notify_sms=notify_sms
    )

def notify_high_resource_usage(device_name, resource_type, value, threshold):
    """Thông báo về việc sử dụng tài nguyên cao"""
    title = f"Cảnh báo tài nguyên: {device_name}"
    message = f"Thiết bị {device_name} có mức sử dụng {resource_type} cao: {value}% (ngưỡng: {threshold}%)"
    
    return send_system_notification(
        title=title,
        message=message,
        level='warning',
        notify_sms=True
    )

def notify_new_client_connected(client_name, client_ip, client_mac, interface):
    """Thông báo về việc có client mới kết nối"""
    title = "Client mới kết nối"
    message = f"""
    Phát hiện client mới:
    - Tên: {client_name}
    - IP: {client_ip}
    - MAC: {client_mac}
    - Interface: {interface}
    """
    
    return send_system_notification(
        title=title,
        message=message,
        level='info'
    )

def notify_firewall_block(ip_address, reason=None):
    """Thông báo về việc firewall chặn kết nối"""
    title = "Cảnh báo Firewall"
    message = f"Firewall đã chặn IP {ip_address}"
    if reason:
        message += f"\nLý do: {reason}"
    
    return send_system_notification(
        title=title,
        message=message,
        level='warning',
        notify_sms=True
    )