#!/bin/bash

# VARIABLES
PROJECT_NAME="hospital_management"
PROJECT_DIR="/home/$PROJECT_NAME"
REPO_URL="https://github.com/Avaneesh-Pathak/Hospital_Management_Software.git"
DB_NAME="hospital_db"
DB_USER="hospital_user"
DB_PASSWORD="19Piyush95@245132"
VENV_DIR="$PROJECT_DIR/venv"

# Install dependencies
apt update && apt upgrade -y
apt install python3-pip python3-dev libpq-dev postgresql postgresql-contrib nginx curl python3-venv git -y

# Clone your project
cd /home
git clone $REPO_URL $PROJECT_NAME
cd $PROJECT_DIR

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Configure PostgreSQL
sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

# Update settings.py automatically
SETTINGS_FILE="$PROJECT_DIR/hospital_management/settings.py"

sed -i "s|ALLOWED_HOSTS = .*|ALLOWED_HOSTS = ['*']|" $SETTINGS_FILE
sed -i "s|TIME_ZONE = .*|TIME_ZONE = 'Asia/Kolkata'|" $SETTINGS_FILE

# Inject DB config
sed -i "/'ENGINE': 'django.db.backends.postgresql'/,/}/c\\
        'ENGINE': 'django.db.backends.postgresql',\\
        'NAME': '$DB_NAME',\\
        'USER': '$DB_USER',\\
        'PASSWORD': '$DB_PASSWORD',\\
        'HOST': 'localhost',\\
        'PORT': '',
" $SETTINGS_FILE

# Migrate and collect static
source $VENV_DIR/bin/activate
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput

# Gunicorn service
cat <<EOF > /etc/systemd/system/gunicorn.service
[Unit]
Description=gunicorn daemon for $PROJECT_NAME
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/gunicorn --workers 3 --bind unix:$PROJECT_DIR/gunicorn.sock hospital_management.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reexec
systemctl start gunicorn
systemctl enable gunicorn

# Nginx setup
cat <<EOF > /etc/nginx/sites-available/$PROJECT_NAME
server {
    listen 80;
    server_name 148.135.136.159;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root $PROJECT_DIR;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$PROJECT_DIR/gunicorn.sock;
    }
}
EOF

ln -s /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx
ufw allow 'Nginx Full'

echo "✅ Deployment complete!"
echo "🌐 Visit: http://148.135.136.159"
