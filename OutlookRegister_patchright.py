import os
import time
import json
import random
import string
import secrets
from faker import Faker
from get_token import get_access_token
from patchright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor


def generate_strong_password(length=16):

    chars = string.ascii_letters + string.digits + "!@#$%^&*"

    while True:
        password = ''.join(secrets.choice(chars) for _ in range(length))

        if (any(c.islower() for c in password) 
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)):
            return password

def random_email(length):

    first_char = random.choice(string.ascii_lowercase)

    other_chars = []
    for _ in range(length - 1):  
        if random.random() < 0.07:  
            other_chars.append(random.choice(string.digits))
        else: 
            other_chars.append(random.choice(string.ascii_lowercase))

    return first_char + ''.join(other_chars)

def OpenBrowser():
    try:
        p = sync_playwright().start()
        browser = p.chromium.launch(
            headless=False,            
            args=[
                '--lang=zh-CN'
            ],
            proxy={
                "server": proxy,
                "bypass": "localhost",
            }
        ) 
        return browser,p

    except Exception as e:
        print(e)

def Outlook_register(page, email, password):

    fake = Faker()

    lastname = fake.last_name()
    firstname = fake.first_name()
    year = str(random.randint(1960, 2005))
    month = str(random.randint(1, 12))
    day = str(random.randint(1, 28))

    try:

        page.goto("https://outlook.live.com/mail/0/?prompt=create_account", timeout=20000, wait_until="domcontentloaded")
        page.get_by_text('同意并继续').wait_for(timeout=30000)
        start_time = time.time()
        page.wait_for_timeout(0.1 * bot_protection_wait)
        page.get_by_text('同意并继续').click(timeout=30000)

    except: 

        print("[Error: IP] - IP质量不佳，无法进入注册界面。 ")
        return False

    try:

        page.locator('[aria-label="新建电子邮件"]').type(email,delay=0.006 * bot_protection_wait,timeout=10000)
        page.locator('[data-testid="primaryButton"]').click(timeout=5000)
        page.wait_for_timeout(0.02 * bot_protection_wait)
        page.locator('[type="password"]').type(password,delay=0.004 * bot_protection_wait, timeout=10000)
        page.wait_for_timeout(0.02 * bot_protection_wait)
        page.locator('[data-testid="primaryButton"]').click(timeout=5000)
        
        page.wait_for_timeout(0.03 * bot_protection_wait)
        page.locator('[name="BirthYear"]').fill(year,timeout=10000)

        try:

            page.wait_for_timeout(0.02 * bot_protection_wait)
            page.locator('[name="BirthMonth"]').select_option(value=month,timeout=1000)
            page.wait_for_timeout(0.05 * bot_protection_wait)
            page.locator('[name="BirthDay"]').select_option(value=day)
        
        except:

            page.locator('[name="BirthMonth"]').click()
            page.wait_for_timeout(0.02 * bot_protection_wait)
            page.locator(f'[role="option"]:text-is("{month}月")').click()
            page.wait_for_timeout(0.04 * bot_protection_wait)
            page.locator('[name="BirthDay"]').click()
            page.wait_for_timeout(0.03 * bot_protection_wait)
            page.locator(f'[role="option"]:text-is("{day}日")').click()
            page.locator('[data-testid="primaryButton"]').click(timeout=5000)

        page.locator('#lastNameInput').type(lastname,delay=0.002 * bot_protection_wait,timeout=10000)
        page.wait_for_timeout(0.02 * bot_protection_wait)
        page.locator('#firstNameInput').fill(firstname,timeout=10000)

        if time.time() - start_time < bot_protection_wait / 1000:
            page.wait_for_timeout(bot_protection_wait - (time.time() + start_time) * 1000)
        
        page.locator('[data-testid="primaryButton"]').click(timeout=5000)
        page.locator('span > [href="https://go.microsoft.com/fwlink/?LinkID=521839"]').wait_for(state='detached',timeout=22000)

        page.wait_for_timeout(400)

        if page.get_by_text('一些异常活动').count() or page.get_by_text('此站点正在维护，暂时无法使用，请稍后重试。').count() > 0:
            print("[Error: IP or broswer] - 当前IP注册频率过快。检查IP与是否为指纹浏览器并关闭了无头模式。")
            return False

        if page.locator('iframe#enforcementFrame').count() > 0:
            print("[Error: FunCaptcha] - 验证码类型错误，非按压验证码。 ")
            return False

        frame1 = page.frame_locator('iframe[title="验证质询"]')
        frame2 = frame1.frame_locator('iframe[style*="display: block"]')

        for _ in range(0, max_captcha_retries + 1):

            frame2.locator('[stroke="transparent"]').click(timeout=15000)
            frame2.locator('[aria-label="再次按下"]').click(timeout=30000)

            try:
                page.locator('.draw').wait_for(state="detached")

                try:

                    page.locator('[role="status"][aria-label="正在加载..."]').wait_for(timeout=5000)
                    page.wait_for_timeout(8000)
                    if page.get_by_text('一些异常活动').count() or page.get_by_text('此站点正在维护，暂时无法使用，请稍后重试。').count() > 0:
                        print("[Error: Rate limit] - 正常通过验证码，但当前IP注册频率过快。")
                        return False
                    break

                except:
                    frame1.get_by_text("请再试一次").wait_for(timeout=15000)
                    continue

            except:
                raise TimeoutError

        else: 
            raise TimeoutError

    except:

        print(f"[Error: IP] - 加载超时或因触发机器人检测导致按压次数达到最大仍未通过。")
        return False 

    filename = 'Results\\logged_email.txt' if enable_oauth2 else 'Results\\unlogged_email.txt'
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"{email}@outlook.com: {password}\n")
    print(f'[Success: Email Registration] - {email}@outlook.com: {password}')

    if not enable_oauth2:
        return True

    try:
        page.get_by_text('取消').click(timeout=20000)

    except:

        print(f"[Error: Timeout] - 无法找到按钮。")
        return False   

    try:

        try:
            # 这个不确定是不是一定出现
            page.get_by_text('无法创建通行密钥').wait_for(timeout=25000)
            page.get_by_text('取消').click(timeout=7000)

        except:
            pass

        page.locator('[aria-label="新邮件"]').wait_for(timeout=26000)
        return True

    except:

        print(f'[Error: Timeout] - 邮箱未初始化，无法正常收件。')
        return False

def process_single_flow():

    try:
        browser = None
        browser, p = OpenBrowser()
        page = browser.new_page()

        email =  random_email(random.randint(12, 14))
        password = generate_strong_password(random.randint(11, 15))
        result = Outlook_register(page, email, password)
        if result and not enable_oauth2:

            return True
        
        elif not result:
            return False
        
        token_result = get_access_token(page, email)
        if token_result[0]:
            refresh_token, access_token, expire_at =  token_result
            with open(r'Results\outlook_token.txt', 'a') as f2:
                f2.write(email + "@outlook.com---" + password + "---" + refresh_token + "---" + access_token  + "---" + str(expire_at) + "\n") 
            print(f'[Success: TokenAuth] - {email}@outlook.com')
            return True
        else:
            return False

    except:
        return False
    
    finally:
        browser.close()
        p.stop()

def main(concurrent_flows=10, max_tasks=1000):

    task_counter = 0  
    succeeded_tasks = 0 
    failed_tasks = 0 

    with ThreadPoolExecutor(max_workers=concurrent_flows) as executor:
        running_futures = set()

        while task_counter < max_tasks or len(running_futures) > 0:

            done_futures = {f for f in running_futures if f.done()}
            for future in done_futures:
                try:
                    result = future.result()
                    if result:
                        succeeded_tasks += 1
                    else:
                        failed_tasks += 1

                except Exception as e:
                    failed_tasks += 1
                    print(e)

                running_futures.remove(future)
            
            while len(running_futures) < concurrent_flows and task_counter < max_tasks:
                time.sleep(0.2)
                new_future = executor.submit(process_single_flow)
                running_futures.add(new_future)
                task_counter += 1

            time.sleep(0.5)

        print(f"[Info: Result] - 共 {max_tasks} 个，成功 {succeeded_tasks}，失败 {failed_tasks}")

if __name__ == '__main__':

    
    with open('config.json', 'r', encoding='utf-8') as f:
        data = json.load(f) 

    os.makedirs("Results", exist_ok=True)

    browser_path = data['browser_path']
    bot_protection_wait = data['Bot_protection_wait'] * 1000
    max_captcha_retries = data['max_captcha_retries']
    proxy = data['proxy']
    enable_oauth2 = data['enable_oauth2']
    concurrent_flows = data["concurrent_flows"]
    max_tasks = data["max_tasks"]

    main(concurrent_flows, max_tasks)