import requests
import base64
from datetime import datetime
from flask import current_app, url_for


class MPesaService:
    def __init__(self):
        self.consumer_key = current_app.config['MPESA_CONSUMER_KEY']
        self.consumer_secret = current_app.config['MPESA_CONSUMER_SECRET']
        self.shortcode = current_app.config['MPESA_SHORTCODE']
        self.passkey = current_app.config['MPESA_PASSKEY']
        self.environment = current_app.config['MPESA_ENVIRONMENT']

        if self.environment == 'production':
            self.base_url = 'https://api.safaricom.co.ke'
        else:
            self.base_url = 'https://sandbox.safaricom.co.ke'

    def get_access_token(self):
        url = f'{self.base_url}/oauth/v1/generate?grant_type=client_credentials'
        auth_str = f'{self.consumer_key}:{self.consumer_secret}'
        auth_bytes = auth_str.encode('ascii')
        auth_base64 = base64.b64encode(auth_bytes).decode('ascii')

        headers = {'Authorization': f'Basic {auth_base64}'}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json().get('access_token')
        return None

    def stk_push(self, phone_number, amount, account_reference, description):
        access_token = self.get_access_token()
        if not access_token:
            return {'success': False, 'message': 'Failed to get access token'}

        url = f'{self.base_url}/mpesa/stkpush/v1/processrequest'
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f'{self.shortcode}{self.passkey}{timestamp}'
        password = base64.b64encode(password_str.encode()).decode('utf-8')

        phone = phone_number.replace('+', '').replace(' ', '')
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif not phone.startswith('254'):
            phone = '254' + phone

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone,
            'PartyB': self.shortcode,
            'PhoneNumber': phone,
            'CallBackURL': url_for('licensing.mpesa_callback', _external=True),
            'AccountReference': account_reference,
            'TransactionDesc': description
        }

        response = requests.post(url, json=payload, headers=headers)
        return response.json()