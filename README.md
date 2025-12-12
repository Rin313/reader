python -m pip install --upgrade pip //更新pip
pip install -r requirements.txt --upgrade
# 不要用webview系浏览器打开

终端解除权限

sudo chmod -R +x .
sudo xattr -r -d com.apple.quarantine .

出现了dist、model都在users/yuan导入的问题，而用户处理路径是users/yuan/desktop/deepreader