# OutlookRegister  

Outlook 注册机  
不保证可用性，自行测试。 

- 模拟人类填表操作  
- 自动过验证码  
- 注册成功  

设置相关：
1.如果使用`OutlookRegister.py`(playwright)，则需要自行寻找指纹浏览器并填写绝对路径到`browser_path`。  
2.如果使用`OutlookRegister_patchright.py`(patchright)，`browser_path`可以留空。  
3.`Bot_protection_wait`单位为秒,可填0。  
4.`client_id`与`redirect_url`可以前往[Azure](https://azure.microsoft.com/zh-cn?OCID=cmmyhidqdn5_brandzone__EFID__)注册获取，不需要Oauth2可留空。  
5.`client_id`与`redirect_url`格式通常类似于`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`和`http://localhost:8000`。  
6.`Scopes`按照申请的权限填，不需要Oauth2可留空。  

使用教程：  
1.使用本地代理IP**搭建代理池**，在`config.json`填写你的代理地址。  
2.在设置中调整并发与最大注册量。  
3.如果你需要Oauth2，请在`config.json`中修改`"enable_oauth2"`的值为`true`并填写`Scopes`、`client_id`与`redirect_url`。  
4.安装相关依赖`pip install -r requirements.txt`，如果未安装相关浏览器，使用`playwright install chromium`。  
5.视运行脚本填写或留空`browser_path`。  
6.`python OutlookRegister_patchright.py`或者`python OutlookRegister.py`。  

注意事项：  
**IP**与成功率高度正相关，同一IP短时间不宜多次注册。  
邮箱自动存储到工作目录的`Results`下。  
