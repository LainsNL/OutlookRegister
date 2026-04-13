import json
import base64
import string
import hashlib
import secrets
import requests
from datetime import datetime
from urllib.request import getproxies
from urllib.parse import quote, parse_qs

def get_proxy():
    proxies = getproxies()
    http_proxy = proxies.get('http') or proxies.get('https')
    if http_proxy:
        return {"http": http_proxy, "https": http_proxy}
    return {"http": None, "https": None}

def generate_code_verifier(length=128):
    alphabet = string.ascii_letters + string.digits + '-._~'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_code_challenge(code_verifier):
    sha256_hash = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(sha256_hash).decode().rstrip('=')

def handle_oauth2_form(page, email):
    try:
        page.locator('[name="loginfmt"]').fill(f'{email}@outlook.com', timeout=20000)
        page.locator('#idSIButton9').click(timeout=7000)

        consent_btn = page.locator('[data-testid="appConsentPrimaryButton"]')
        consent_btn.wait_for(state='visible', timeout=20000)
        consent_btn.click(timeout=10000)
    except:
        pass

def get_access_token(page, email, max_retries=3):
    for attempt in range(max_retries):
        result = _try_get_access_token(page, email)
        if result[0] is not False:
            return result
    return False, False, False

def _try_get_access_token(page, email):
    with open('config.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    SCOPES = data['oauth2']['Scopes']
    client_id = data['oauth2']['client_id']
    redirect_url = data['oauth2']['redirect_url']

    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_url,
        'scope': ' '.join(SCOPES),
        'response_mode': 'query',
        'prompt': 'select_account',
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }

    authorize_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{'&'.join(f'{k}={quote(v)}' for k, v in params.items())}"

    captured_url = None

    def on_request(request):
        nonlocal captured_url
        if redirect_url in request.url and 'code=' in request.url:
            captured_url = request.url

    page.on("request", on_request)

    try:
        try:
            page.wait_for_timeout(250)
            page.goto(authorize_url, timeout=30000)
        except:
            return False, False, False

        handle_oauth2_form(page, email)

        max_refreshes = 1
        refresh_count = 0
        refresh_interval = 200 

        for i in range(400):
            page.wait_for_timeout(100)
            if captured_url:
                break

            current_url = page.url
            if 'res=error' in current_url or 'error' in current_url.split('?')[-1]:
                return False, False, False

            if i > 0 and i % refresh_interval == 0:
                if refresh_count >= max_refreshes:
                    return False, False, False
                refresh_count += 1
                try:
                    page.reload(timeout=10000)
                except:
                    pass
        else:
            return False, False, False

    finally:
        page.remove_listener("request", on_request)

    if not captured_url or 'code=' not in captured_url:
        return False, False, False

    auth_code = parse_qs(captured_url.split('?')[1])['code'][0]

    try:
        response = requests.post(
            'https://login.microsoftonline.com/common/oauth2/v2.0/token',
            data={
                'client_id': client_id,
                'code': auth_code,
                'redirect_uri': redirect_url,
                'grant_type': 'authorization_code',
                'code_verifier': code_verifier,
                'scope': ' '.join(SCOPES)
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            proxies=get_proxy()
        )

        if 'refresh_token' in response.json():
            tokens = response.json()
            return (
                tokens['refresh_token'],
                tokens.get('access_token', ''),
                datetime.now().timestamp() + tokens['expires_in']
            )
    except:
        return False, False, False

    return False, False, False