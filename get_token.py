import json
import base64
import random
import string
import winreg
import hashlib
import secrets
import requests
from datetime import datetime
from urllib.parse import quote, parse_qs

def get_proxy():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
            proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
            if proxy_enable and proxy_server:
                return {"http": f"http://{proxy_server}", "https": f"http://{proxy_server}"}
    except WindowsError:
        pass
    return {"http": None, "https": None}

def generate_code_verifier(length=128):
    alphabet = string.ascii_letters + string.digits + '-._~'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_code_challenge(code_verifier):
    sha256_hash = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(sha256_hash).decode().rstrip('=')

def handle_oauth2_form(page,email):
    try:

        page.locator('[name="loginfmt"]').fill(f'{email}@outlook.com',timeout=20000)
        page.locator('#idSIButton9').click(timeout=7000)
        page.locator('[data-testid="appConsentPrimaryButton"]').click(timeout=20000)

    except:
        pass

def get_access_token(page, email):

    with open('config.json', 'r', encoding='utf-8') as f:
        data = json.load(f) 
    SCOPES = data['Scopes']
    client_id = data['client_id']
    redirect_url = data['redirect_url']

    code_verifier = generate_code_verifier()  
    code_challenge = generate_code_challenge(code_verifier) 
    scope = ' '.join(SCOPES)
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_url,
        'scope': scope,
        'response_mode': 'query',
        'prompt': 'select_account',
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }

    max_time = 2 
    current_times = 0
    while current_times < max_time:

        try:

            page.wait_for_timeout(250)
            url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{'&'.join(f'{k}={quote(v)}' for k,v in params.items())}"
            page.goto(url)

            break

        except:
                current_times = current_times + 1 
                if current_times == max_time:
                    return False, False, False
                continue

    with page.expect_response(lambda response: redirect_url in response.url,timeout=50000) as response_info:

        handle_oauth2_form(page, email)

        response = response_info.value
        callback_url = response.url

        if 'code=' not in callback_url:

            print("Authorization failed: No code in callback URL")
            return False, False, False
        auth_code = parse_qs(callback_url.split('?')[1])['code'][0]

    token_data = {
        'client_id': client_id,
        'code': auth_code,
        'redirect_uri': redirect_url,
        'grant_type': 'authorization_code',
        'code_verifier': code_verifier,
        'scope': ' '.join(SCOPES)
    }

    response = requests.post('https://login.microsoftonline.com/common/oauth2/v2.0/token', data=token_data, headers={
        'Content-Type': 'application/x-www-form-urlencoded'
    }, proxies=get_proxy())

    if 'refresh_token' in response.json():

        tokens = response.json()
        token_data = {
            'refresh_token': tokens['refresh_token'],
            'access_token': tokens.get('access_token', ''),
            'expires_at': datetime.now().timestamp() + tokens['expires_in']
    }
        refresh_token = token_data['refresh_token']
        access_token = token_data['access_token']
        expire_at = token_data['expires_at']
        return refresh_token, access_token, expire_at

    else:

        return False, False, False