import os
import time
import json
import random
import string
import secrets
import asyncio
from faker import Faker
from get_token import get_access_token
from patchright.async_api import async_playwright


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

async def OpenBrowser(p):
    try:
        launch_options = {
            "headless": False,
            "args": ['--lang=zh-CN']
        }
        if proxy:
            launch_options["proxy"] = {
                "server": proxy,
                "bypass": "localhost",
            }
        browser = await p.chromium.launch(**launch_options) 
        return browser

    except Exception as e:
        print(f"[Error: Browser] - {e}")
        return None

async def Outlook_register(page, email, password):

    fake = Faker()

    lastname = fake.last_name()
    firstname = fake.first_name()
    year = str(random.randint(1960, 2005))
    month = str(random.randint(1, 12))
    day = str(random.randint(1, 28))

    try:

        await page.goto("https://outlook.live.com/mail/0/?prompt=create_account", timeout=20000, wait_until="domcontentloaded")
        await page.get_by_text('同意并继续').wait_for(timeout=30000)
        start_time = time.time()
        await page.wait_for_timeout(0.1 * bot_protection_wait)
        await page.get_by_text('同意并继续').click(timeout=30000)

    except: 

        print("[Error: IP] - IP质量不佳，无法进入注册界面。 ")
        return False

    try:

        await page.locator('[aria-label="新建电子邮件"]').type(email,delay=0.006 * bot_protection_wait,timeout=10000)
        await page.locator('[data-testid="primaryButton"]').click(timeout=5000)
        await page.wait_for_timeout(0.02 * bot_protection_wait)
        await page.locator('[type="password"]').type(password,delay=0.004 * bot_protection_wait, timeout=10000)
        await page.wait_for_timeout(0.02 * bot_protection_wait)
        await page.locator('[data-testid="primaryButton"]').click(timeout=5000)
        
        await page.wait_for_timeout(0.03 * bot_protection_wait)
        await page.locator('[name="BirthYear"]').fill(year,timeout=10000)

        try:

            await page.wait_for_timeout(0.02 * bot_protection_wait)
            await page.locator('[name="BirthMonth"]').select_option(value=month,timeout=1000)
            await page.wait_for_timeout(0.05 * bot_protection_wait)
            await page.locator('[name="BirthDay"]').select_option(value=day)
        
        except:

            await page.locator('[name="BirthMonth"]').click()
            await page.wait_for_timeout(0.02 * bot_protection_wait)
            await page.locator(f'[role="option"]:text-is("{month}月")').click()
            await page.wait_for_timeout(0.04 * bot_protection_wait)
            await page.locator('[name="BirthDay"]').click()
            await page.wait_for_timeout(0.03 * bot_protection_wait)
            await page.locator(f'[role="option"]:text-is("{day}日")').click()
            await page.locator('[data-testid="primaryButton"]').click(timeout=5000)

        await page.locator('#lastNameInput').type(lastname,delay=0.002 * bot_protection_wait,timeout=10000)
        await page.wait_for_timeout(0.02 * bot_protection_wait)
        await page.locator('#firstNameInput').fill(firstname,timeout=10000)

        if time.time() - start_time < bot_protection_wait / 1000:
            await page.wait_for_timeout(bot_protection_wait - (time.time() + start_time) * 1000)
        
        await page.locator('[data-testid="primaryButton"]').click(timeout=5000)
        await page.locator('span > [href="https://go.microsoft.com/fwlink/?LinkID=521839"]').wait_for(state='detached',timeout=22000)

        await page.wait_for_timeout(400)

        if await page.get_by_text('一些异常活动').count() or await page.get_by_text('此站点正在维护，暂时无法使用，请稍后重试。').count() > 0:
            print("[Error: IP or broswer] - 当前IP注册频率过快。检查IP与是否为指纹浏览器并关闭了无头模式。")
            return False

        if await page.locator('iframe#enforcementFrame').count() > 0:
            print("[Error: FunCaptcha] - 验证码类型错误，非按压验证码。 ")
            return False

        frame1 = page.frame_locator('iframe[title="验证质询"]')
        frame2 = frame1.frame_locator('iframe[style*="display: block"]')

        for _ in range(0, max_captcha_retries + 1):

            await frame2.locator('[stroke="transparent"]').click(timeout=15000)
            await frame2.locator('[aria-label="再次按下"]').click(timeout=30000)

            try:
                await page.locator('.draw').wait_for(state="detached")

                try:

                    await page.locator('[role="status"][aria-label="正在加载..."]').wait_for(timeout=5000)
                    await page.wait_for_timeout(8000)
                    if await page.get_by_text('一些异常活动').count() or await page.get_by_text('此站点正在维护，暂时无法使用，请稍后重试。').count() > 0:
                        print("[Error: Rate limit] - 正常通过验证码，但当前IP注册频率过快。")
                        return False
                    break

                except:

                    if await page.get_by_text('取消').count() > 0:
                        break
                    await frame1.get_by_text("请再试一次").wait_for(timeout=15000)
                    continue

            except:
                raise asyncio.TimeoutError

        else: 
            raise asyncio.TimeoutError

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
        await page.get_by_text('取消').click(timeout=20000)

    except:
        print(f"[Error: Timeout] - 无法找到按钮。")
        return False   

    try:

        try:
            # 这个不确定是不是一定出现
            await page.get_by_text('无法创建通行密钥').wait_for(timeout=25000)
            await page.get_by_text('取消').click(timeout=7000)

        except:
            pass

        await page.locator('[aria-label="新邮件"]').wait_for(timeout=26000)
        return True

    except:

        print(f'[Error: Timeout] - 邮箱未初始化，无法正常收件。')
        return False

async def process_single_flow(p, semaphore):
    async with semaphore:
        browser = None
        try:
            browser = await OpenBrowser(p)
            if not browser:
                return False
            page = await browser.new_page()

            email =  random_email(random.randint(12, 14))
            password = generate_strong_password(random.randint(11, 15))
            result = await Outlook_register(page, email, password)

            if result and not enable_oauth2:
                return True

            elif not result:
                return False

            token_result = await get_access_token(page, email)
            if token_result[0]:
                refresh_token, access_token, expire_at =  token_result
                with open(r'Results\outlook_token.txt', 'a') as f2:
                    f2.write(email + "@outlook.com---" + password + "---" + refresh_token + "---" + access_token  + "---" + str(expire_at) + "\n") 
                print(f'[Success: TokenAuth] - {email}@outlook.com')
                return True
            else:
                return False

        except Exception as e:
            print(f"[Error: Flow] - {e}")
            return False
        
        finally:
            if browser:
                try:
                    await browser.close()
                except:
                    pass

async def main(concurrent_flows=10, max_tasks=1000):

    succeeded_tasks = 0 
    failed_tasks = 0 

    async with async_playwright() as p:
        semaphore = asyncio.Semaphore(concurrent_flows)
        tasks = []
        for _ in range(max_tasks):
            tasks.append(process_single_flow(p, semaphore))
        
        results = await asyncio.gather(*tasks)
        for result in results:
            if result:
                succeeded_tasks += 1
            else:
                failed_tasks += 1

        print(f"[Info: Result] - 共 {max_tasks} 个，成功 {succeeded_tasks}，失败 {failed_tasks}")

if __name__ == '__main__':

    with open('config.json', 'r', encoding='utf-8') as f:
        data = json.load(f) 

    os.makedirs("Results", exist_ok=True)

    bot_protection_wait = data['Bot_protection_wait'] * 1000
    max_captcha_retries = data['max_captcha_retries']
    proxy = data['proxy']
    enable_oauth2 = data['enable_oauth2']
    concurrent_flows = data["concurrent_flows"]
    max_tasks = data["max_tasks"]

    asyncio.run(main(concurrent_flows, max_tasks))
