# OutlookRegister  

简体中文 | [English](./readme_en.md)  

Outlook 注册机  
选择器经常更新，不保证时效性，自行测试。  

- 模拟人类填表操作  
- 自动过验证码  
- 注册成功  

---

### 使用步骤

1. `pip install -r requirements.txt`  
2. `python -m ruyipage install`（推荐，如果使用 ruyipage）  
3. `patchright install chromium`（如果使用 patchright）  
4. 在 `config.json` 中配置代理、并发，并选定一种辅助邮箱方式填写相关内容。  
5. `python main.py`  

---

| 配置项 | 说明 |
| :--- | :--- |
| **`choose_browser`** | `"patchright"` ， `"playwright"` 或者 `ruyipage` ，最推荐 `"ruyipage"`。 |
| **`choosed_mail`** | `"moemail"` 或 `"outlookgraph"`。 |
| **`email_suffix`** | `"@outlook.com"` 或 `"@hotmail.com"`。 |
| **`bot_protection_wait`** | 单位为秒。 |
| **`ruyipage.browser_path`** | 留空则自动获取 |
| **`ruyipage.traffic_mode`** | 可留空，或填入 `"aggressive"` |
| **`moemail.apikey`** | moemail 的 key。 |
| **`moemail.base_url`** | moemail api 基础地址。 |
| **`moemail.suffix`** | 使用的域名，留空则自动获取，逗号分隔多个域名。 |
| **`outlookgraph.strategy`** | `"file"` 或 `"single_email"`。 |
| **`outlookgraph.client_id`** | 辅助邮箱使用的 client id。 |
| **`outlookgraph.single_email`** | 单邮箱配置 `{ "email": "...", "refresh_token": "..." }`。 |
| **`outlookgraph.file.path`** | 数据格式为`账号---密码---refresh_token---access_token---expire_at` |


---

### 补充说明  

1. playwright使用性较差,如果使用playwright，则需要自行寻找指纹浏览器并填写绝对路径。  
2. 若需 OAuth2，可前往 [Azure](https://azure.microsoft.com/zh-cn/) 申请并在配置中填入 `client_id`、`redirect_url` 与 `Scopes`；不需要可留空。  
3. `client_id`与`redirect_url`格式通常类似于`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`和`http://localhost:8000`。  
4. 使用本地代理IP搭建代理池，在`config.json`填写你的代理地址。IP与成功率高度相关，同一IP短时间不宜多次注册。  
5. 邮箱自动存储到工作目录的`Results`下。  
