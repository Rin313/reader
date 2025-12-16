# 部署说明
## 项目目录安装模型
spacy en_core_web_lg
xx_sent_ud_sm
## 前端打包
npm run build
## 后端打包
cd server
pyinstaller main.spec --noconfirm --clean
## mac 终端解除权限
sudo chmod -R +x .
sudo xattr -r -d com.apple.quarantine .
## 不要使用webview系浏览器访问