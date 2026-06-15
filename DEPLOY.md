# Baby Tracker VPS Deployment Guide (Ubuntu / Debian Linux)

This guide walks you through deploying the Baby Tracker Flask application to your Linux VPS (Ubuntu/Debian) using **Gunicorn** as the WSGI server, **Systemd** for auto-starting the service, and **Nginx** as the reverse proxy.

---

## Step 1: Copy Project Files to the VPS

On your local machine, upload the `baby_tracker` folder to your VPS (e.g., using `scp` or `rsync`):

```bash
scp -r "C:\Users\Marco Nie\Development\Web\baby_tracker" user@your_vps_ip:/var/www/
```

*Note: Replace `user` with your VPS SSH username, `your_vps_ip` with your VPS IP, and `/var/www/` with your preferred target directory.*

---

## Step 2: Set Up Python Virtual Environment on the VPS

SSH into your VPS and install Python virtual environment tools:

```bash
ssh user@your_vps_ip
sudo apt update
sudo apt install python3-pip python3-venv python3-dev sqlite3 -y
```

Navigate to the directory and create the virtual environment:

```bash
cd /var/www/baby_tracker
python3 -m venv venv
source venv/bin/activate
```

Install the dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 3: Configure Systemd Service (Auto-Start)

1. Copy the systemd service configuration file to the system systemd directory:

   ```bash
   sudo cp baby_tracker.service /etc/systemd/system/
   ```

2. (Optional) Adjust permissions if needed:
   Make sure the `www-data` user has read/write permissions to the directory so it can create and update the SQLite database file `baby_tracker.db`:

   ```bash
   sudo chown -R www-data:www-data /var/www/baby_tracker
   ```

3. Enable and start the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable baby_tracker
   sudo systemctl start baby_tracker
   ```

4. Check the service status to make sure it is running:

   ```bash
   sudo systemctl status baby_tracker
   ```

---

## Step 4: Configure Nginx (Reverse Proxy)

1. Copy the Nginx server block configuration to Nginx's configurations:

   ```bash
   sudo cp baby_tracker.nginx /etc/nginx/sites-available/baby_tracker
   ```

2. Link the configuration to enable it:

   ```bash
   sudo ln -s /etc/nginx/sites-available/baby_tracker /etc/nginx/sites-enabled/
   ```

3. Edit the server block to replace `babytracker.local` with your domain name or VPS public IP address:

   ```bash
   sudo nano /etc/nginx/sites-available/baby_tracker
   ```

4. Test Nginx configuration and reload the service:

   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

---

## Step 5: Configure Firewall (UFW)

Ensure port 80 (HTTP) is open through your VPS firewall:

```bash
sudo ufw allow 'Nginx Full'
```

---

## Step 6: Log & Debug Commands

* **View live service logs**: `sudo journalctl -u baby_tracker -f`
* **Restart service**: `sudo systemctl restart baby_tracker`
* **Nginx logs**: `/var/log/nginx/error.log` and `/var/log/nginx/access.log`
