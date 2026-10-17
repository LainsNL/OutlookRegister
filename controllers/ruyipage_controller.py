import re
import json
import time
import random
from types import SimpleNamespace
from .base_controller import BaseBrowserController
from ruyipage import FirefoxOptions, FirefoxPage, resolve_firefox_path


#  --- 兼容层 ---
WAIT_MAP = {"domcontentloaded": "interactive", "load": "complete", "commit": "none"}

def _normalize_timeout(t, default=None):
    if t is None:
        return default
    t = float(t)
    if t >= 40:
        return max(t / 1000.0, 0.04)
    return max(t, 0.01)

def _normalize_sel(sel: str) -> str:
    sel = sel.strip()

    # :text-is("xxx")
    m = re.match(r'^(.*):text-is\(["\'](.*)["\']\)$', sel)
    if m:
        base, txt = m.groups()
        base = base.strip()

        # 处理属性选择器，如 [role="option"]
        m_attr = re.match(r'^([a-zA-Z0-9_-]*)\[([a-zA-Z0-9_-]+)=["\']?(.*?)["\']?\]$', base)
        if m_attr:
            tag, attr, val = m_attr.groups()
            tag = tag or "*"
            return f"xpath://{tag}[@{attr}='{val}' and normalize-space()='{txt}']"
        elif base:
            return f"xpath://{base}[normalize-space()='{txt}']"
        return f"xpath://*[normalize-space()='{txt}']"

    # :has-text("xxx") 
    m2 = re.match(r'^(.*):has-text\(["\'](.*)["\']\)$', sel)
    if m2:
        base, txt = m2.groups()
        base = base.strip()
        m_attr = re.match(r'^([a-zA-Z0-9_-]*)\[([a-zA-Z0-9_-]+)=["\']?(.*?)["\']?\]$', base)
        if m_attr:
            tag, attr, val = m_attr.groups()
            tag = tag or "*"
            return f"xpath://{tag}[@{attr}='{val}' and contains(normalize-space(), '{txt}')]"
        elif base:
            return f"xpath://{base}[contains(normalize-space(), '{txt}')]"
        return f"xpath://*[contains(normalize-space(), '{txt}')]"

    #  CSS 属性选择器（补齐 css: 前缀）
    if not sel.startswith(('css:', 'c:', 'xpath:', 'x:', 'text:', 'text=', 'tag:', '#', '.', '/')):
        return f"css:{sel}"
    return sel


class LazyLocator:
    def __init__(self, page: FirefoxPage, ruyi_selector: str, timeout=None):
        self.page = page
        self.selector = _normalize_sel(ruyi_selector)
        self.normal_timeout = _normalize_timeout(timeout, default=15.0)

    def resolve(self, timeout=None):
        sec = _normalize_timeout(timeout, default=self.normal_timeout)
        ele = self.page.ele(self.selector, timeout=sec)
        if not ele:
            raise TimeoutError(f"未找到元素 ({sec}s): {self.selector}")
        return ele

    def count(self) -> int:
        eles = self.page.eles(self.selector, timeout=0.05)
        return len(eles) if eles else 0

    def wait_for(self, state="visible", timeout=None):
        sec = _normalize_timeout(timeout, default=self.normal_timeout)
        deadline = time.time() + sec

        if state in ("hidden", "detached"):
            while time.time() < deadline:
                try:
                    eles = self.page.eles(self.selector, timeout=0.1)
                    if not eles:
                        return True
                    if state == "hidden":
                        disp = getattr(eles[0], "is_displayed", False)
                        if callable(disp):
                            disp = disp()
                        if not disp:
                            return True
                except Exception:
                    pass
                self.page.wait(0.1)
            raise TimeoutError(f"等待元素 [{state}] 状态超时: {self.selector}")

        while time.time() < deadline:
            try:
                ele = self.page.ele(self.selector, timeout=0.1)
                if ele:
                    if state == "attached":
                        return ele
                    disp = getattr(ele, "is_displayed", True)
                    if callable(disp):
                        disp = disp()
                    if disp:
                        return ele
            except Exception:
                pass
            self.page.wait(0.15)

        raise TimeoutError(f"等待元素 [{state}] 状态超时 ({sec}s): {self.selector}")

    def fill(self, text, timeout=None):
        ele = self.wait_for(state="visible", timeout=timeout)
        ele.input(str(text), clear=True)
        return self

    def click(self, timeout=None):
        ele = self.resolve(timeout=timeout)
        self.page.actions.human_move(ele).human_click().perform()
        return self

    def type(self, text, delay=30, timeout=None):
        ele = self.resolve(timeout=timeout)
        self.page.actions.move_to(ele).click().type(str(text), interval=delay).perform()
        return self

    def __getattr__(self, name):
        return getattr(self.resolve(), name)


def _goto(self, url, wait_until=None, timeout=None):
    mode = WAIT_MAP.get(wait_until, "complete")
    sec = _normalize_timeout(timeout)
    if sec is not None:
        return self.get(url, wait=mode, timeout=sec)
    return self.get(url, wait=mode)

def _wait_for_timeout(self, timeout):
    res = self.wait(_normalize_timeout(timeout, default=0.0))
    if getattr(self, "_req_listeners", None):
        try:
            _dispatch_request_url(self, self.url)
        except Exception:
            pass
    return res

def _reload(self, timeout=10000):
    return self.refresh()

def _get_by_text(self, text, timeout=None):
    return LazyLocator(self, f"text:{text}", timeout=timeout)

def _locator(self, sel, timeout=None):
    return LazyLocator(self, _normalize_sel(sel), timeout=timeout)

def _dispatch_request_url(page: FirefoxPage, url: str):
    listeners = getattr(page, "_req_listeners", None)
    if not listeners or not url:
        return
    req_obj = SimpleNamespace(url=url)
    for cb in list(listeners):
        try:
            cb(req_obj)
        except Exception:
            pass

def _on(self: FirefoxPage, event_name: str, callback):
    if event_name != "request":
        return
    if not hasattr(self, "_req_listeners"):
        self._req_listeners = []
    if callback not in self._req_listeners:
        self._req_listeners.append(callback)

    if not getattr(self, "_intercept_running", False):
        def _handler(req):
            try:
                _dispatch_request_url(self, getattr(req, "url", ""))
            finally:
                try:
                    req.continue_request()
                except Exception:
                    pass
        try:
            self.intercept.start_requests(_handler)
            self._intercept_running = True
        except Exception:
            pass

def _remove_listener(self: FirefoxPage, event_name: str, callback):
    if event_name != "request":
        return
    listeners = getattr(self, "_req_listeners", None)
    if listeners and callback in listeners:
        listeners.remove(callback)
    if not listeners and getattr(self, "_intercept_running", False):
        try:
            self.intercept.stop()
        except Exception:
            pass
        self._intercept_running = False

def _wait_closed_text(self, keywords=("请再试一次", "Keep going", "a few more tries"), timeout=15.0):
    deadline = time.time() + float(timeout)
    while time.time() < deadline:
        try:
            for root in self.shadow_roots(mode="closed", include_frames=True):
                try:
                    alert_ele = root.ele('css:p[role="alert"]', timeout=0.1)
                    if alert_ele:
                        txt = getattr(alert_ele, "text", "") or ""
                        if any(k in txt for k in keywords):
                            return True
                except Exception:
                    continue
        except Exception:
            pass
        self.wait(0.3)
    return False


FirefoxPage.on = _on
FirefoxPage.goto = _goto
FirefoxPage.reload = _reload
FirefoxPage.locator =_locator
FirefoxPage.get_by_text = _get_by_text
FirefoxPage.remove_listener = _remove_listener
FirefoxPage.wait_closed_text = _wait_closed_text
FirefoxPage.wait_for_timeout = _wait_for_timeout


class RuyipageController(BaseBrowserController):
    def __init__(self):
        super().__init__()
        with open('config.json', 'r', encoding='utf-8') as f:
            data = json.load(f)  
        self.traffic_mode = data["ruyipage"]["traffic_mode"]
        self.browser_path = data["ruyipage"]["browser_path"] if data["ruyipage"]["browser_path"] else resolve_firefox_path()

    def wait_random_ratio(self, page, min_ratio, delta=0.02):
        actual_ratio = random.uniform(min_ratio, min_ratio + delta)
        page.wait(_normalize_timeout(actual_ratio * self.wait_time))

    def _unwrap_ele(self, ele_or_loc):
        if isinstance(ele_or_loc, LazyLocator):
            return ele_or_loc.resolve()
        return ele_or_loc
    
    def smooth_click(self, page, ele):
        real_ele = self._unwrap_ele(ele)
        page.actions.human_move(real_ele).human_click().perform()

    def smooth_type(self, page, ele, text):
        real_ele = self._unwrap_ele(ele)
        page.actions.human_move(real_ele).perform()
        real_ele.click_self()
        page.actions.human_type(str(text)).perform()

    # 可以使用一个浏览器 + 多个 Tab 的形式降低内存
    def launch_browser(self):
        try:
            opts = FirefoxOptions()
            opts.headless(False)
            opts.private_mode(True)
            opts.close_on_exit(True)
            opts.set_proxy(self.proxy)
            opts.set_window_size(1440, 900)
            opts.set_human_algorithm("windmouse")
            opts.set_pref("intl.locale.requested", "zh-CN")
            opts.set_pref("intl.accept_languages", "zh-CN, zh, en-US, en")
            opts.set_browser_path(self.browser_path)

            opts.set_pref("browser.cache.disk.enable", True)
            opts.set_pref("browser.cache.memory.enable", True)
            opts.set_pref("browser.cache.disk_cache_ssl", True)
            opts.set_pref("media.autoplay.default", 5)
            opts.set_pref("media.preload.default", 1)
            opts.set_pref("media.preload.auto", 1)
            opts.set_pref("browser.safebrowsing.malware.enabled", False)
            opts.set_pref("browser.safebrowsing.phishing.enabled", False)
            opts.set_pref("browser.safebrowsing.downloads.enabled", False)
            opts.set_pref("browser.safebrowsing.downloads.remote.enabled", False)
            opts.set_pref("browser.safebrowsing.downloads.remote.url", "")
            opts.set_pref("media.gmp-gmpopenh264.enabled", False)
            opts.set_pref("media.gmp-gmpopenh264.autoupdate", False)
            opts.set_pref("media.gmp-widevinecdm.enabled", False)
            opts.set_pref("media.gmp-widevinecdm.autoupdate", False)
            opts.set_pref("media.gmp-manager.url", "")
            opts.set_pref("app.update.auto", False)
            opts.set_pref("extensions.update.enabled", False)
            opts.set_pref("extensions.getAddons.cache.enabled", False)
            opts.set_pref("extensions.blocklist.enabled", False)
            opts.set_pref("network.prefetch-next", False)
            opts.set_pref("network.dns.disablePrefetch", True)
            opts.set_pref("network.dns.disablePrefetchFromHTTPS", True)
            opts.set_pref("network.predictor.enabled", False)
            opts.set_pref("network.predictor.enable-prefetch", False)
            opts.set_pref("network.http.speculative-parallel-limit", 0)
            opts.set_pref("datareporting.healthreport.uploadEnabled", False)
            opts.set_pref("datareporting.policy.dataSubmissionEnabled", False)
            opts.set_pref("toolkit.telemetry.enabled", False)
            opts.set_pref("toolkit.telemetry.unified", False)
            opts.set_pref("toolkit.telemetry.archive.enabled", False)
            opts.set_pref("app.normandy.enabled", False)
            opts.set_pref("app.shield.optoutstudies.enabled", False)
            opts.set_pref("browser.newtabpage.activity-stream.feeds.telemetry", False)
            opts.set_pref("browser.newtabpage.activity-stream.telemetry", False)
            opts.set_pref("browser.newtabpage.activity-stream.feeds.section.topstories", False)
            opts.set_pref("browser.ping-centre.telemetry", False)
            opts.set_pref("extensions.pocket.enabled", False)

            if self.traffic_mode == "aggressive":
                opts.set_pref("permissions.default.image", 2)             # 禁止加载所有图片
                opts.set_pref("gfx.downloadable_fonts.enabled", False)    # 禁止下载远程 Web 字体
                opts.set_pref("dom.serviceWorkers.enabled", False)        # 禁用 ServiceWorker 后台缓存脚本
                opts.set_pref("media.peerconnection.enabled", False)

            page = FirefoxPage(opts)
            return opts, page

        except Exception as e:
            print(f"启动浏览器失败: {e}")
            return False, False

    def get_thread_page(self):
        return self.get_thread_browser()

    def handle_captcha(self, page):

        page.wait_for_timeout(random.randint(400, 700))

        for _ in range(0, 3):
            loc = None
            end_time = time.time() + 15
            while time.time() < end_time and not loc:
                for f in page.get_all_frames():
                    b = f.ele('css:[aria-label="可访问性挑战"]', timeout=0.05)
                    if b:
                        frame2, loc = f, b
                        frame2.actions.human_move(loc).human_click().perform()
                        break


            page.wait_for_timeout(random.randint(300, 400))
            loc2 = frame2.ele('css:[aria-label="再次按下"]')
            frame2.actions.human_move(loc2).human_click().perform()

            try:
                page.locator('.draw').wait_for(state="detached", timeout=14000)
                try:
                    # 简单的认为加载8秒后成功，暂不考虑请求.
                    page.locator('[role="status"][aria-label="正在加载..."]').wait_for(timeout=5000)

                    captcha_passed = False
                    for _ in range(20):
                        if page.get_by_text('一些异常活动').count() or page.get_by_text('此站点正在维护，暂时无法使用，请稍后重试。').count() > 0:
                            print("[Error: Rate limit] - 正常通过验证码，但当前IP注册频率过快。")
                            return False
                        elif any(f.ele('css:[aria-label="可访问性挑战"]', timeout=0.02) for f in page.get_all_frames()):
                            captcha_passed = False
                            page.wait_for_timeout(random.randint(500, 1000))
                            break
                        elif page.get_by_text('保护你的帐户').count() > 0 or page.locator('[data-testid="primaryButton"]').count() > 0:
                            captcha_passed = True
                            break
                        page.wait_for_timeout(random.randint(375, 425))
                    else:
                        # 部分会一直加载，不确定是否注册成功
                        if not any(f.ele('css:[aria-label="可访问性挑战"]', timeout=0.02) for f in page.get_all_frames()):
                            captcha_passed = True

                    if captcha_passed:
                        break

                except Exception:
                    if page.get_by_text('保护你的帐户').count() > 0 or page.locator('[data-testid="primaryButton"]').count() > 0:
                        break
                    if page.wait_closed_text(("请再试一次", "Keep going", "a few more tries"), timeout=15):
                        continue

            except Exception:
                if page.get_by_text('保护你的帐户').count() > 0 or page.locator('[data-testid="primaryButton"]').count() > 0:
                        break
                return False
        else: 
            return False

        return True

    def clean_up(self, page=None, type="all_browser"):
        if type == "done_browser" and page is not None:
            try:
                page.quit() 
            except Exception:
                pass
            with self.cleanup_lock:
                self.active_resources = [item for item in self.active_resources if item[1] != page]
            if hasattr(self.thread_local, "browser"):
                del self.thread_local.browser
            if hasattr(self.thread_local, "playwright"):
                del self.thread_local.playwright
        elif type == "all_browser":
            with self.cleanup_lock:
                for _, b in self.active_resources:
                    try:
                        b.quit()
                    except Exception:
                        pass
                self.active_resources.clear()