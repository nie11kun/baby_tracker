# 宝宝中控面板 VPS 部署指南 (Ubuntu / Debian Linux)

本指南将指导您如何使用 **Gunicorn** 作为 WSGI 服务器，**Systemd** 进行服务自启动管理，以及 **Nginx** 作为反向代理，将宝宝智能中控面板项目部署到您的 Linux VPS 上。

---

## 步骤 1：将项目文件复制到 VPS

在本地电脑上，将 `baby_tracker` 文件夹上传至您的 VPS（例如使用 `scp` 或 `rsync` 命令行工具）：

```bash
scp -r "C:\Users\Marco Nie\Development\Web\baby_tracker" user@your_vps_ip:/home/www/
```

*注意：请将 `user` 替换为您的 VPS SSH 用户名，将 `your_vps_ip` 替换为您的 VPS 公网 IP 地址，`/home/www/` 为目标部署目录。*

---

## 步骤 2：在 VPS 上配置 Python 虚拟环境

使用 SSH 连接至您的 VPS，并安装 Python 及 SQLite 所需的系统依赖：

```bash
ssh user@your_vps_ip
sudo apt update
sudo apt install python3-pip python3-venv python3-dev sqlite3 -y
```

进入项目部署目录，并创建 Python 虚拟环境：

```bash
cd /home/www/baby_tracker
python3 -m venv venv
source venv/bin/activate
```

升级 pip 并安装项目依赖包：

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 步骤 3：配置 Systemd 系统服务 (自启动)

1. 将项目目录中的系统服务配置文件复制到系统的 systemd 目录：

   ```bash
   sudo cp baby_tracker.service /etc/systemd/system/
   ```

2. （可选，但强烈推荐）配置目录所有权：
   确保 `www-data` 用户对项目目录拥有读写权限，以便能够正常创建和更新 SQLite 数据库文件 `baby_tracker.db`：

   ```bash
   sudo chown -R www-data:www-data /home/www/baby_tracker
   ```

3. 重载 systemd 配置，并启动和启用自启动服务：

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable baby_tracker
   sudo systemctl start baby_tracker
   ```

4. 检查服务运行状态，确保其显示为 `active (running)`：

   ```bash
   sudo systemctl status baby_tracker
   ```

---

## 步骤 4：配置 Nginx 反向代理

1. 将项目目录中的 Nginx 配置文件复制到 Nginx 的配置目录：

   ```bash
   sudo cp baby_tracker.nginx /etc/nginx/sites-available/baby_tracker
   ```

2. 建立软链接以启用此配置文件：

   ```bash
   sudo ln -s /etc/nginx/sites-available/baby_tracker /etc/nginx/sites-enabled/
   ```

3. 编辑该 Nginx 配置文件，将默认的 `server_name babytracker.local;` 替换为您实际拥同的域名或 VPS 的公网 IP 地址：

   ```bash
   sudo nano /etc/nginx/sites-available/baby_tracker
   ```

4. 测试 Nginx 配置文件语法是否正确，并重载 Nginx 服务：

   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

---

## 步骤 5：配置系统防火墙 (UFW)

确保您的 VPS 防火墙已开放 80 端口（HTTP）以允许外部浏览器访问：

```bash
sudo ufw allow 'Nginx Full'
```

---

## 步骤 6：日常维护与日志调试命令

* **查看实时运行日志**：`sudo journalctl -u baby_tracker -f`
* **重启后端服务**：`sudo systemctl restart baby_tracker`
* **查看 Nginx 报错日志**：`sudo tail -f /var/log/nginx/error.log`
* **查看 Nginx 访问日志**：`sudo tail -f /var/log/nginx/access.log`
