# Production Deployment Guide (Vercel & Hostinger VPS)

This guide provides instructions to host the Next.js frontend on **Vercel** and the Django backend on a **Hostinger VPS** without affecting other applications running on the same server.

---

## Part 1: Host the Next.js Frontend on Vercel (Recommended)

Vercel is the native platform for Next.js, offering global CDN caching, automatic scaling, and SSL support out-of-the-box.

### Steps:
1. Push your `kpsc-web` folder to a repository on **GitHub**, **GitLab**, or **Bitbucket**.
2. Log in to [Vercel](https://vercel.com) and click **Add New > Project**.
3. Select your repository and configure the framework preset as **Next.js**.
4. In the **Environment Variables** section, add:
   - `NEXT_PUBLIC_API_URL` = `https://api.yourdomain.com` (Your custom VPS backend subdomain)
   - `NEXT_PUBLIC_GOOGLE_CLIENT_ID` = `your-google-client-id`
5. Click **Deploy**.
6. (Optional) Under project settings, add a custom domain name (e.g. `kpsc.yourdomain.com`).

---

## Part 2: Isolated Django Backend Deployment on Hostinger VPS

To make sure this backend doesn't conflict with other databases or Python APIs running on your Hostinger VPS, we run it in an isolated workspace, on a dedicated local port, reverse proxied through **Nginx**.

### Step 1: Clone and Set Up Directories
Log in to your VPS via SSH and choose/create a dedicated folder:
```bash
mkdir -p /var/www/kpsc-backend
cd /var/www/kpsc-backend
# Clone or copy your backend files here
git clone <your-backend-repo-url> .
```

### Step 2: Isolated Python Environment
Set up a separate Python virtual environment to isolate the project dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### Step 3: Production Environment File (`.env`)
Create a new `.env` file in `/var/www/kpsc-backend/.env`:
```env
DEBUG=False
SECRET_KEY=generate_a_random_50_character_string_here
ALLOWED_HOSTS=api.yourdomain.com,localhost,127.0.0.1
DATABASE_URL=postgresql://kpsc_user:db_password@localhost:5432/kpsc_db
GOOGLE_CLIENT_ID=your_google_client_id_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 4: Systemd Service Configuration (Isolated Gunicorn)
Run the backend in the background as a system service on a custom port (e.g., `8005`) that is not used by your other backends:

1. Create a systemd service file:
   ```bash
   sudo nano /etc/systemd/system/kpsc-backend.service
   ```
2. Paste the following configuration:
   ```ini
   [Unit]
   Description=gunicorn daemon for KPSC backend
   After=network.target

   [Service]
   User=root
   WorkingDirectory=/var/www/kpsc-backend
   ExecStart=/var/www/kpsc-backend/venv/bin/gunicorn \
             --access-logfile - \
             --workers 3 \
             --bind 127.0.0.1:8005 \
             kpsc_backend.wsgi:application

   [Install]
   WantedBy=multi-user.target
   ```
3. Start and enable the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start kpsc-backend
   sudo systemctl enable kpsc-backend
   ```

### Step 5: Nginx Configuration (Reverse Proxy)
Redirect external HTTPS requests to your custom port `8005` using Nginx.

1. Create a new server configuration file:
   ```bash
   sudo nano /etc/nginx/sites-available/kpsc-backend
   ```
2. Paste the configuration (replace `api.yourdomain.com` with your actual domain):
   ```nginx
   server {
       listen 80;
       server_name api.yourdomain.com;

       location = /favicon.ico { access_log off; log_not_found off; }
       
       location /static/ {
           root /var/www/kpsc-backend;
       }

       location /media/ {
           root /var/www/kpsc-backend;
       }

       location / {
           include proxy_params;
           proxy_pass http://127.0.0.1:8005;
       }
   }
   ```
3. Enable the config and restart Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/kpsc-backend /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### Step 6: Secure with Let's Encrypt SSL (HTTPS)
Vercel requires the backend API URL to use `https` for security reasons. Secure your Nginx proxy for free:
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d api.yourdomain.com
```
Follow the prompts, and certbot will automatically configure the SSL certs and rewrite Nginx to route all traffic securely over HTTPS.

---

## Part 3: Automated Daily Current Affairs Updates (Cron Job)

To keep current affairs and MCQs updated automatically every day, configure a cron job on your Hostinger VPS.

### Step 1: Make the runner script executable
Log in to your VPS via SSH and run:
```bash
chmod +x /var/www/kpsc-backend/run_daily_current_affairs.sh
```

### Step 2: Open Crontab
Open the system crontab editor for the `root` user (or the user running the django backend):
```bash
crontab -e
```

### Step 3: Add Cron Entry
Add the following line at the bottom of the crontab file to trigger the update script every morning at 6:00 AM (server local time):
```cron
0 6 * * * /bin/bash /var/www/kpsc-backend/run_daily_current_affairs.sh >> /var/www/kpsc-backend/cron_current_affairs.log 2>&1
```

This will automatically execute the daily current affairs generator, pull fresh news/MCQs via the LLM router (Groq -> Gemini -> GLM), and log execution results to `/var/www/kpsc-backend/cron_current_affairs.log`.

