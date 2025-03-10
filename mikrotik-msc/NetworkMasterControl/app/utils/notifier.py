# File: app/utils/notifier.py
import requests

def send_to_slack(message):
    webhook_url = config['slack_webhook']
    payload = {"text": message}
    requests.post(webhook_url, json=payload)
