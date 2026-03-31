import base64
import hashlib
import json
import secrets
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

import requests

try:
    import winreg  # type: ignore
except ImportError:
    winreg = None


class OAuthCallbackServer:
    """本地 OAuth 回调接收器，仅用于 localhost/127.0.0.1。"""

    def __init__(self, redirect_url):
        parsed = urlparse(redirect_url)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
            raise ValueError("仅支持 http://localhost 或 http://127.0.0.1 回调地址")

        self.expected_path = parsed.path or "/"
        self.bind_host = parsed.hostname
        self.bind_port = parsed.port or 80
        self.callback_url = None
        self._callback_event = threading.Event()

        parent = self

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                request = urlparse(self.path)
                if request.path != parent.expected_path:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write("Not Found".encode("utf-8"))
                    return

                host = self.headers.get("Host") or f"{parent.bind_host}:{parent.bind_port}"
                parent.callback_url = f"http://{host}{self.path}"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("授权成功，可关闭此页面。".encode("utf-8"))
                parent._callback_event.set()

            def log_message(self, format, *args):
                return

        self._server = ThreadingHTTPServer((self.bind_host, self.bind_port), CallbackHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self):
        self._thread.start()

    def wait_for_callback(self, timeout):
        if not self._callback_event.wait(timeout):
            return None
        return self.callback_url

    def close(self):
        self._server.shutdown()
        self._server.server_close()


def get_system_proxy():
    """读取 Windows 系统代理；非 Windows 直接返回 None。"""
    if winreg is None:
        return None

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
            proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
            if proxy_enable and proxy_server:
                return {"http": f"http://{proxy_server}", "https": f"http://{proxy_server}"}
    except OSError:
        return None

    return None


def build_requests_proxy(proxy_url=None):
    """优先使用配置文件里的代理，避免浏览器链路和 requests 链路出口不一致。"""
    if proxy_url:
        return {"http": proxy_url, "https": proxy_url}
    return get_system_proxy()


def is_local_redirect_url(redirect_url):
    parsed = urlparse(redirect_url)
    return parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}

def generate_code_verifier(length=128):
    alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_code_challenge(code_verifier):
    sha256_hash = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(sha256_hash).decode().rstrip('=')

def handle_oauth2_form(page,email):
    try:

        page.locator('[name="loginfmt"]').fill(f'{email}@outlook.com',timeout=20000)
        page.locator('#idSIButton9').click(timeout=7000)
        page.locator('[data-testid="appConsentPrimaryButton"]').click(timeout=20000)

    except Exception:
        pass


def build_authorize_url(params):
    return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{'&'.join(f'{k}={quote(v)}' for k,v in params.items())}"


def navigate_to_authorize(page, authorize_url, email):
    max_time = 2
    current_times = 0
    while current_times < max_time:
        try:
            page.wait_for_timeout(250)
            page.goto(authorize_url)
            break
        except Exception:
            current_times += 1
            if current_times == max_time:
                return False

    handle_oauth2_form(page, email)
    return True


def wait_for_redirect_callback(page, email, authorize_url, redirect_url):
    """按 redirect_url 类型分别等待远端回调或本地 localhost 回调。"""
    if is_local_redirect_url(redirect_url):
        callback_server = OAuthCallbackServer(redirect_url)
        try:
            callback_server.start()
            if not navigate_to_authorize(page, authorize_url, email):
                return None
            return callback_server.wait_for_callback(timeout=50)
        finally:
            callback_server.close()

    with page.expect_response(lambda response: redirect_url in response.url, timeout=50000) as response_info:
        if not navigate_to_authorize(page, authorize_url, email):
            return None
    return response_info.value.url


def get_access_token(page, email, proxy_url=None):

    with open('config.json', 'r', encoding='utf-8') as f:
        data = json.load(f) 
    SCOPES = data['Scopes']
    client_id = data['client_id']
    redirect_url = data['redirect_url']

    if not client_id or not redirect_url or not SCOPES:
        print("OAuth2 配置缺失：请检查 client_id / redirect_url / Scopes")
        return False, False, False

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

    authorize_url = build_authorize_url(params)
    try:
        callback_url = wait_for_redirect_callback(page, email, authorize_url, redirect_url)
    except Exception as exc:
        print(f"等待 OAuth 回调失败: {type(exc).__name__}: {exc}")
        return False, False, False

    if not callback_url:
        print("Authorization failed: OAuth 回调超时或未收到 code")
        return False, False, False

    callback_query = parse_qs(urlparse(callback_url).query)
    auth_code = callback_query.get('code', [None])[0]
    if not auth_code:
        print("Authorization failed: No code in callback URL")
        return False, False, False

    token_data = {
        'client_id': client_id,
        'code': auth_code,
        'redirect_uri': redirect_url,
        'grant_type': 'authorization_code',
        'code_verifier': code_verifier,
        'scope': ' '.join(SCOPES)
    }

    try:
        response = requests.post(
            'https://login.microsoftonline.com/common/oauth2/v2.0/token',
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            proxies=build_requests_proxy(proxy_url),
            timeout=30,
        )
        tokens = response.json()
    except requests.RequestException as exc:
        print(f"Token 请求失败: {type(exc).__name__}: {exc}")
        return False, False, False
    except ValueError as exc:
        print(f"Token 响应不是合法 JSON: {type(exc).__name__}: {exc}")
        return False, False, False

    if 'refresh_token' in tokens:
        token_result = {
            'refresh_token': tokens['refresh_token'],
            'access_token': tokens.get('access_token', ''),
            'expires_at': datetime.now().timestamp() + tokens['expires_in']
        }
        refresh_token = token_result['refresh_token']
        access_token = token_result['access_token']
        expire_at = token_result['expires_at']
        return refresh_token, access_token, expire_at

    print(f"Token 交换失败: status={response.status_code}, body={tokens}")
    return False, False, False
