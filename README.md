# AADX Hit

## 使用

如网络环境不好，请确保在终端中启用了代理。例如：

```powershell
$Env:http_proxy="http://127.0.0.1:7890";$Env:https_proxy="http://127.0.0.1:7890"
```

之后运行

```bash
pip install PyQt5 selenium webdriver_manager
python aadx.py
```

在左侧文本框粘贴一系列 hit 链接（表格里复制的、接龙的都可以）以后按 Parse Links 保存。接下来点击 Login，在弹出的浏览器界面里访问任意一个人的链接砸一下，会要求用 twitter 登录。登录后回到主界面，点 Hit 即可。