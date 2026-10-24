# OutlookRegister

[简体中文](./readme.md) | English

Outlook Account Auto-Register Tool.  
Selectors may change frequently; timeliness is not guaranteed—please test on your own.

- Human-like form filling simulation
- Automatic CAPTCHA solving
- Account registration & security email binding

---

### Quick Start

1. `pip install -r requirements.txt`
2. `python -m ruyipage install` (Recommended if using `ruyipage`)
3. `patchright install chromium` (If using `patchright`)
4. Configure proxy, concurrency , and recovery email provider settings in `config.json`.
5. `python main.py`

---

### Configuration

| Key | Description |
| :--- | :--- |
| **`choose_browser`** | `"patchright"`, `"playwright"`, or `"ruyipage"`. `"ruyipage"` is recommended. |
| **`choosed_mail`** | `"moemail"` or `"outlookgraph"`. |
| **`email_suffix`** | `"@outlook.com"` or `"@hotmail.com"`. |
| **`bot_protection_wait`** | Wait time in seconds before submitting registration. |
| **`ruyipage.browser_path`** | Leave empty to resolve automatically. |
| **`ruyipage.traffic_mode`** | Leave empty, or set to `"aggressive"` . |
| **`moemail.apikey`** | API key for MoeMail. |
| **`moemail.base_url`** | Base URL of the MoeMail API. |
| **`moemail.suffix`** | Domain suffix to use. Leave empty for random selection; separate multiple domains with commas. |
| **`outlookgraph.strategy`** | `"file"` or `"single_email"`. |
| **`outlookgraph.client_id`** | Client ID for the recovery email account. |
| **`outlookgraph.single_email`** | Single recovery email config: `{ "email": "...", "refresh_token": "..." }`. |
| **`outlookgraph.file.path`** | Path to account file formatted as: `email---password---refresh_token---access_token---expire_at`. |

---

### Notes

1. Standard `playwright` has poor anti-bot pass rates. If you choose `playwright`, you must use an anti-detect browser and specify its executable path.  
2. If you need OAuth2 tokens, register an app on [Azure](https://azure.microsoft.com/) and fill in `client_id`, `redirect_url`, and `Scopes` in `config.json`; otherwise, leave them empty.  
3. `client_id` and `redirect_url` typically look like `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` and `http://localhost:8000`.  
4. Set up a local proxy pool and fill in your proxy address in `config.json`. IP quality is critical to success rates—avoid registering multiple accounts from the same IP within a short period.  
5. Registered accounts are saved automatically in the `Results` folder.  