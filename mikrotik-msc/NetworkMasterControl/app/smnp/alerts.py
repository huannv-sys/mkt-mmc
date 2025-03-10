import smtplib
from email.mime.text import MIMEText

def send_alert(subject, message, to_email):
    from_email = "your_email@example.com"
    password = "your_password"

    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    with smtplib.SMTP_SSL('smtp.example.com', 465) as server:
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())

# Example usage
if __name__ == "__main__":
    send_alert("Test Alert", "This is a test alert message.", "recipient@example.com")
