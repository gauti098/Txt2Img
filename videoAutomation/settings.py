from pathlib import Path
import os
import environ
from google.cloud import texttospeech
from google.oauth2 import service_account
from utils.common import convertInt
import sys

if sys.platform == "linux":
    os.environ['IMAGEMAGICK_BINARY'] = '/usr/local/bin/magick'
    os.environ['FFMPEG_BINARY'] = '/usr/bin/ffmpeg'

BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env'))

GOOGLE_TTS_CLIENT = texttospeech.TextToSpeechClient(credentials=service_account.Credentials.from_service_account_file('credentials/GoogleAuthAccount.json'))


SECRET_KEY = 'h98pdqx0$mm8*6-pxm*vlk_b4=g3z=)o(b65m^&v!^_%jj24-4'

DEBUG = False

ALLOWED_HOSTS = ['172.31.16.194','localhost','127.0.0.1','api.autogenerate.ai','autogenerate.ai','autovid.ai','aivideo-api-1','app.autovid.ai','54.187.239.71']
WEBSOCKET_ALLOWED_HOSTS = ['localhost','127.0.0.1','api.autogenerate.ai','aivideo-api-1','54.187.239.71']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',

    #third party app
    'phonenumber_field',
    'rest_framework',
	'rest_framework.authtoken',
    'corsheaders',
	'authemail',
    #'django_hosts',
    'channels',
    'django_extensions',
    'django_celery_results',


	'accounts',
    "appAssets",
    'userlibrary',
    'salesPage',
    'aiQueueManager',
    "backgroundclip",
    "campaign",
    "campaignAnalytics",
    "subscriptions",
    "videoThumbnail",
    "urlShortner",
    "aiAudio",

    "externalAssets",
    "newVideoCreator",
    "newImageEditor",
    "videoCredit",
    "paymentHandler",

    "colors"
    
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'videoAutomation.custom_middleware.XForwardedForMiddleware',
]
'''
### domain change
MIDDLEWARE = [
    'django_hosts.middleware.HostsRequestMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_hosts.middleware.HostsResponseMiddleware',
]
ROOT_HOSTCONF = 'videoAutomation.hosts'
DEFAULT_HOST = "www"
'''

ROOT_URLCONF = 'videoAutomation.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'videoAutomation.wsgi.application'


# Database
# Dump (pg_dump -h localhost -U videoautomationdatauser -W -F t videoautomationdata > /home/govind/db_dumb.tar)
# Restore (pg_restore -h localhost -d videoautomationdata dump_name.tar -c -U videoautomationdatauser)

DATABASES_TYPE = os.environ.get('DATABASES_TYPE') or ''
DATABASES_PASSWORD = os.environ.get('DATABASES_PASSWORD') or 'password'

if DATABASES_TYPE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'videoautomationdata',
            'USER': 'videoautomationdatauser',
            'PASSWORD': DATABASES_PASSWORD,
            'HOST': 'localhost',
            'PORT': '',
            'CONN_MAX_AGE': 500,
            'OPTIONS': {
                'sslmode': 'disable',
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        }
    },
    
]

'''
{
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
{
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
'''


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

BASE_URL = "https://api.autogenerate.ai"

STATIC_URL = f'{BASE_URL}/static/'
MEDIA_URL =  f'{BASE_URL}/media/'
MEDIA_ROOT = "uploads/"

STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

REST_FRAMEWORK = {
	'DEFAULT_AUTHENTICATION_CLASSES': (
		'rest_framework.authentication.TokenAuthentication',
	),
    
}

ASGI_APPLICATION = "videoAutomation.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("localhost", 6379)],   # Change localhost to the ip in which you have redis server running on.
        },
    },
}


AUTH_USER_MODEL = 'accounts.MyUser'
AUTH_SIGNUP_AUTO_VERIFY = False
AUTH_SIGNUP_AUTO_REDIRECT = "https://autovid.ai/pricing"


AVATAR_AUDIO_CHARACTER_LIMIT = 1000
WEBSOCKET_SERVER_TOKEN = os.environ.get('WEBSOCKET_SERVER_TOKEN') or ''
SERVER_TOKEN = os.environ.get('SERVER_TOKEN') or ''

NODE_SERVER_BASE_URL = "http://localhost:3303"
REAL_TIME_THUMBNAIL_GENERATE_BASE_URL = "http://localhost:3300"

EMAIL_FROM = os.environ.get('AUTHEMAIL_DEFAULT_EMAIL_FROM') or ''
EMAIL_BCC = os.environ.get('AUTHEMAIL_DEFAULT_EMAIL_BCC') or ''

EMAIL_HOST = os.environ.get('AUTHEMAIL_EMAIL_HOST') or 'smtp.gmail.com'
EMAIL_PORT = convertInt(os.environ.get('AUTHEMAIL_EMAIL_PORT') or 587,587) 
EMAIL_HOST_USER = os.environ.get('AUTHEMAIL_EMAIL_HOST_USER') or ''
EMAIL_HOST_PASSWORD = os.environ.get('AUTHEMAIL_EMAIL_HOST_PASSWORD') or ''

MAILER_LIST = ['govind.autogenerate.ai@gmail.com']
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
ADMINS = [("Govind Kumar", MAILER_LIST[0])]

EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY','')
STRIPE_ENDPOINT_SECRET = os.environ.get('STRIPE_ENDPOINT_SECRET','')

PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY')
UNSPLASH_API_KEY = os.environ.get('UNSPLASH_API_KEY','')
PIXABAY_API_KEY = os.environ.get('PIXABAY_API_KEY')


# Google configuration
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY') or ''
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET') or ''

# Define SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE to get extra permissions from Google.
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]


FRONTEND_URL = "https://salespage.autogenerate.ai"

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "https://autogenerate.ai",
    "https://autogenerateai.com",
    "http://staging.autogenerate.ai",
    "http://video.autogenerate.ai",
    "https://autovid.ai",
    "https://app.autovid.ai",
    "http://app.autovid.ai",
    "http://autovid.ai:8888",
    "http://autovid.ai:5000",
    "http://autovid.ai:3000",
    "http://salespage.autogenerate.ai:8888",
    FRONTEND_URL
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://\w+\.autovid\.ai$",
    r"^https://\w+\.autogenerate\.ai$",
]


VIDEO_CREATOR_URL = "https://video.autogenerate.ai"


VIDEO_DEFAULT_FPS = 30
VIDEOCREDIT_RATE = 70
VIDEO_PROGRESS_UPDATE_FRAME = 30
VIDEO_SNAPSHOT_DEFAULT_IMAGE_PATH = "snapshotDefault.jpg"

## setup RabbitMQ
import pika
RABBITMQ_USERNAME = os.environ.get('RABBITMQ_USERNAME') or 'guest'
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASSWORD') or 'guest'
RABBITMQ_HOST,RABBITMQ_PORT = ('localhost',5672)
RABBITMQ_CREDS = pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)
RABBITMQ_CONNECTIONS = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST,RABBITMQ_PORT,'/',RABBITMQ_CREDS))

CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_BROKER_URL = f'amqp://{RABBITMQ_USERNAME}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}'

CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'



VIDEO_DEFAULT_COLOR = []#'#00FFFF', '#000000', '#FCA311', '#FF00FF', '#F1FAEE', '#1D3557', '#00FF00', '#800000', '#000080', '#808000', '#800080', '#FF0000','#1E212D','#FF6B6B', '#C0C0C0', '#008080', '#FFFFFF', '#FFFF00']

DEFAULT_MERGE_TAG = ["{{Custom Variable}}","{{Name}}", "{{Company}}", "{{Job Title}}", "{{Number}}", "{{Location}}"]
SPECIAL_MERGE_TAG = ["{{WebsiteScreenshot}}","{{Logo}}","{{Profile}}"]
MERGE_TAG_PATTERN = r"\{{(.*?)\}}"

LOGGING_CONFIG = None

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,

    'formatters': {
        'verbose': {
            'format': '%(levelname)s [%(asctime)s] %(process)d %(processName)s %(thread)d %(threadName)s %(module)s %(message)s'
        },
    },
    'filters': {
        'skip_unwanted_email': {
            '()': 'videoAutomation.filterEmail.FilterErrorEmail',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': '../logs/backend/djangoMain.log',
            'maxBytes': 1024000,
            'backupCount': 3,
            'level': "INFO"
        },
        
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['skip_unwanted_email'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        }

    },

    'loggers': {
        '': {
            'handlers': ['console','file'],
            'level': 'INFO'
        },
        'django': {
            'handlers': ['console','file','mail_admins']
        },
        'django.request': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG'
        },
    }
}


import logging.config
logging.config.dictConfig(LOGGING)

LOAD_GPU_MODEL = False
WAVLIPBATCHSIZE = 128
WAVLIPIMAGESIZE = 96
WAVLIPMELSTEPSIZE = 16
DEVICE = 'cpu'

if  os.environ.get('LOAD_GPU_MODEL',False):
    LOAD_GPU_MODEL = True

if LOAD_GPU_MODEL:
    import torch

    DEVICE = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    WAVLIPBATCHSIZE = 128
    WAVLIPIMAGESIZE = 96
    WAVLIPMELSTEPSIZE = 16
    def load_model(path):
        from AiHandler.wav2lip import Wav2Lip
        model = Wav2Lip()
        if DEVICE == 'cuda:0':
            checkpoint = torch.load(path)
        else:
            checkpoint = torch.load(path,map_location=lambda storage, loc: storage)

        s = checkpoint["state_dict"]
        new_s = {}
        for k, v in s.items():
            new_s[k.replace('module.', '')] = v
        model.load_state_dict(new_s)
        model = model.to(DEVICE)
        return model.eval()

    WAVLIPMODEL = load_model(os.path.join(BASE_DIR,'AiHandler/wav2lip/ai-models/wav2lip_gan.pth'))


    #load first order model
    import yaml
    from AiHandler.first_order.sync_batchnorm import DataParallelWithCallback
    from AiHandler.first_order.modules.generator import OcclusionAwareGenerator
    from AiHandler.first_order.modules.keypoint_detector import KPDetector

    def load_first_order_checkpoints(config_path=os.path.join(BASE_DIR,"AiHandler/first_order/ai-models/vox-512.yaml"), checkpoint_path=os.path.join(BASE_DIR,"AiHandler/first_order/ai-models/vox-512.pth.tar"), device=DEVICE,cpu=False):
        with open(config_path) as f:
            config = yaml.load(f)

        generator = OcclusionAwareGenerator(**config['model_params']['generator_params'],**config['model_params']['common_params'])
        if not cpu:
            generator.to(device)

        kp_detector = KPDetector(**config['model_params']['kp_detector_params'],
                                **config['model_params']['common_params'])
        if not cpu:
            kp_detector.to(device)
        
        if cpu:
            checkpoint = torch.load(checkpoint_path, map_location=torch.device('cpu'))
        else:
            checkpoint = torch.load(checkpoint_path, map_location=torch.device(device))

        generator.load_state_dict(checkpoint['generator'])
        kp_detector.load_state_dict(checkpoint['kp_detector'])
        
        if not cpu:
            generator = DataParallelWithCallback(generator)
            kp_detector = DataParallelWithCallback(kp_detector)

        generator.eval()
        kp_detector.eval()
        return generator, kp_detector

    FIRSTORDERGENERATOR, FIRSTORDERKPDETECTOR = load_first_order_checkpoints()
