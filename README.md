# Cloud Setup Guide

## For ubuntu 20.04 minimal
```
sudo apt update
sudo apt install python3-venv nano vim git ffmpeg cmake
sudo apt-get install libmagic1

```
### Add these Script in ~/.bashrc for auto activate python virtual env.
```
function cd() {
  builtin cd "$@"

  if [[ -z "$VIRTUAL_ENV" ]] ; then
    ## If env folder is found then activate the vitualenv
      if [[ -d ./.env ]] ; then
        source ./.env/bin/activate
      fi
  else
    ## check the current folder belong to earlier VIRTUAL_ENV folder
    # if yes then do nothing
    # else deactivate
      parentdir="$(dirname "$VIRTUAL_ENV")"
      if [[ "$PWD"/ != "$parentdir"/* ]] ; then
        deactivate
      fi
  fi
}
```

### Clone project dir
```
mkdir VideoAutomation && python3 -m venv .env
git config --global credential.helper store
git clone https://github.com/HacxS/SalesPageBackend src
cd src && pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
```

### setup nginx gunicorn and postgresql
(keep database name and databaseuser as small letter)
```
sudo apt install python3-dev libpq-dev postgresql postgresql-contrib nginx curl
sudo -u postgres psql

CREATE DATABASE videoautomationdata;
CREATE USER videoautomationdatauser WITH PASSWORD 'password';
ALTER ROLE videoautomationdatauser SET client_encoding TO 'utf8';
ALTER ROLE videoautomationdatauser SET default_transaction_isolation TO 'read committed';
ALTER ROLE videoautomationdatauser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE videoautomationdata TO videoautomationdatauser;
\q;

pip install gunicorn psycopg2-binary

```

### Change Settings for production
```
ALLOWED_HOSTS = ['localhost','your-server-ip']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'videoAutomation',
        'USER': 'videoAutomationUser',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '',
    }
}

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

python manange.py createsuperuser
python manage.py collectstatic
```
### Create socket service for gunicorn
```
sudo nano /etc/systemd/system/gunicorn.socket
```
```
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target

```

```
sudo nano /etc/systemd/system/gunicorn.service
```
```
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
User=govind
Group=www-data
WorkingDirectory=/home/govind/VideoAutomation/src
ExecStart=/home/govind/VideoAutomation/.env/bin/gunicorn \
          --access-logfile - \
          --workers 2 \
          --bind unix:/run/gunicorn.sock \
          videoAutomation.wsgi:application

[Install]
WantedBy=multi-user.target

```
```
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket
sudo systemctl status gunicorn.socket
sudo systemctl status gunicorn
```

### check gunicorn log
```
sudo journalctl -u gunicorn
```

Check your /etc/systemd/system/gunicorn.service file for problems. If you make changes to the /etc/systemd/system/gunicorn.service file, reload the daemon to reread the service definition and restart the Gunicorn process by typing:
```
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

### Configure Nginx to Proxy Pass to Gunicorn
```
sudo nano /etc/nginx/sites-available/videoAutomation
```
```
server {
    listen 80;
    server_name 34.121.47.255;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root /home/govind/VideoAutomation/src;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```
```
sudo ln -s /etc/nginx/sites-available/videoAutomation /etc/nginx/sites-enabled
sudo systemctl restart nginx

```

## Setup Nvidia Driver and Cuda
```
sudo ubuntu-drivers devices
sudo apt install nvidia-driver-440
sudo apt install nvidia-cuda-toolkit
sudo reboot
```

## install pytorch
```
wget https://download.pytorch.org/whl/cu101/torch-1.4.0-cp38-cp38-linux_x86_64.whl
pip install torch-1.4.0-cp38-cp38-linux_x86_64.whl
or pip install torch==1.4.0 torchvision==0.5.0

cd /home/govind/VideoAutomation/src/AiHandler/wav2lip/face_detection/detection/sfd
wget https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth -O s3fd.pth
```
### put ai-models inside
1) /home/govind/VideoAutomation/src/AiHandler/wav2lip/ai-models/wav2lip_gan.pth
2) /home/govind/VideoAutomation/src/AiHandler/first_order/ai-models/vox-512.pth.tar  and vox-512.yaml


### setup moviepy

1) Install ImageMagick
```
mkdir ~/imageMagic
cd ~/imageMagic
wget https://www.imagemagick.org/download/ImageMagick.tar.gz
tar xvzf ImageMagick.tar.gz
cd ImageMagick-7.0.11-1/
./configure
make
sudo make install 
sudo ldconfig /usr/local/lib


## edit moviepy circle
:~/VideoAutomation/.env/lib/python3.8/site-packages/moviepy/video/tools$ nano drawing.py
Line 140
    if vector is None:
        if p2 is not None:
            p2 = np.array(p2[::-1])
            vector = p2 - p1
```

### setup ChromeDriver (screenshot)
```
sudo apt-get install -y unzip openjdk-8-jre-headless xvfb libxi6 libgconf-2-4
wget -qO - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
sudo apt-get -y update
sudo apt-get -y install google-chrome-stable

google-chrome --version
wget https://chromedriver.storage.googleapis.com/89.0.4389.23/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
rm chromedriver_linux64.zip
sudo mv -f chromedriver /usr/local/bin/chromedriver
sudo chown root:root /usr/local/bin/chromedriver
sudo chmod 0755 /usr/local/bin/chromedriver

cd ~/VideoAutomation/
pip install selenium
```

## First Time Setup
```
1) Check AddAvatars.md
2) Create Video Template Theme with name ("Only Avatar")
  {
    "id": 1,
    "name": "Only Avatar",
    "thumbnail": "http://34.121.47.255/media/videotemplate/thumbnail/onlyAvatar.jpg",
    "filePreview": null,
    "themeColor": null,
    "config": null
  }
3) Put snapshotDefault.jpg in MediaRoot Directory

```

## Setup Websocket (Follow Github) =>
### https://github.com/ranjanmp/django-channels2-notifications
```
sudo apt install redis-server
sudo systemctl status redis-server
pip install channels-redis
pip install django-channels
sudo apt install nginx supervisor
```

### Supervisor Conf
```
[fcgi-program:asgi]
# TCP socket used by Nginx backend upstream
socket=tcp://localhost:8001

# Directory where your site's project files are located
directory=/home/govind/VideoAutomation/src

# Each process needs to have a separate socket file, so we use process_num
# Make sure to update "mysite.asgi" to match your project name
command=/home/govind/VideoAutomation/.env/bin/daphne -u /run/daphne/daphne%(process_num)d.sock --fd 0 --access-log - --proxy-headers videoAutomation.asgi:application

# Number of processes to startup, roughly the number of CPUs you have
numprocs=1

# Give each process a unique name so they can be told apart
process_name=asgi%(process_num)d

# Automatically start and recover processes
autostart=true
autorestart=true

# Choose where you want your log to go
stdout_logfile=/home/govind/VideoAutomation/logs/asgi.out.log
stderr_logfile=/home/govind/VideoAutomation/logs/asgi.err.log
redirect_stderr=true
```

### Nginx Conf
```
upstream channels-backend {
    server localhost:8001;
}
server {
    listen 80;
    server_name 34.121.47.255;
    location = /favicon.ico { access_log off; log_not_found off; }
    location /static {
        add_header Access-Control-Allow-Origin *;
        root /home/govind/VideoAutomation/src;
    }

    location /media {
        add_header Access-Control-Allow-Origin *;
        alias /home/govind/VideoAutomation/src/uploads;
    }
    location / {
        try_files $uri @proxy_to_app;
    }

    location @proxy_to_app {
        proxy_pass http://channels-backend;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_redirect off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $server_name;
    }
 }
```

### setup supervisor and nginx
```
sudo mkdir /run/daphne/

sudo nano /usr/lib/tmpfiles.d/daphne.conf
  d /run/daphne 0755 <user> <group>

sudo supervisorctl reread
sudo supervisorctl update

```


### add emoji font on linux server
```
sudo apt install libicu-dev
sudo apt install fonts-noto
```
# Extra font setup
```
sudo apt install ttf-mscorefonts-installer
mkdir ~/.fonts
wget -qO- http://plasmasturm.org/code/vistafonts-installer/vistafonts-installer | bash
```