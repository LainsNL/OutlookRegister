# OutlookRegister  

Outlook 注册机  
不保证可用性，自行测试。 

- 模拟人类填表操作  
- 自动过验证码  
- 注册成功  

你需要做的内容只有：  

1.使用本地代理IP**搭建代理池**。  
2.在`config.json`填写你的**浏览器目录**和**代理**，并调整数量与最大注册量。  
3.如果你需要Oauth2，请在`config.json`中修改`"enable_oauth2"`的值为`true`并填写`Scopes`与`redirect_url`。  

注意事项：  
选用好的**IP**与**浏览器**，否则可能过不去检测，同一IP短时间不宜多次注册。  
邮箱自动存储到工作目录的`Results`下。 
如果使用无头模式，请自己注意反爬的应对手段。 
高并发还是得走协议。
