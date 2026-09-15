from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['dmdeskadmin.digitalmesh.com', 'wiki.digitalmesh.com']

FERNET_KEY = str(os.getenv('FERNET_KEY'))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': str(os.getenv('DB_NAME')),
        'USER': str(os.getenv('DB_USER')),
        'PASSWORD': str(os.getenv('DB_PWD')),
        'HOST': str(os.getenv('DB_HOST')),
        'PORT': '3378',
    },

    'essl_db': {
        'ENGINE': 'mssql',
        'NAME': str(os.getenv('ESSL_DB_NAME')),
        'HOST': str(os.getenv('ESSL_DB_HOST')),
        'USER': str(os.getenv('ESSL_DB_USER')),
        'PASSWORD': str(os.getenv('ESSL_DB_PWD')),

        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
        }
    },

    'hrms_dm_db': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': str(os.getenv('DB_NAME')),
        'USER': str(os.getenv('DB_USER')),
        'PASSWORD': str(os.getenv('DB_PWD')),
        'HOST': str(os.getenv('DB_HOST')),
        'PORT': '3306',
    },

    'hrms_em_db': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': str(os.getenv('DB_NAME')),
        'USER': str(os.getenv('DB_USER')),
        'PASSWORD': str(os.getenv('DB_PWD')),
        'HOST': str(os.getenv('DB_HOST')),
        'PORT': '3306',
    },
}

STATIC_URL = '/static/'

# STATICFILES_DIRS = [
#         os.path.join(BASE_DIR, 'static')
#     ]
STATICFILES_DIRS = [
    BASE_DIR  ,"static",
    '/var/www/dm_ptracker/backend_app/static/',
]

MEDIA_ROOT = '/var/www/dm_ptracker/backend_app/media/'

# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

BASE_URL = "https://dmdesk.digitalmesh.com/#/"

OFFBOARD_DOCUMENT_URL = MEDIA_ROOT+'offboarding_documents'

DEFAULT_SITE_MEDIA_URL = "https://wiki.digitalmesh.com/media/employee_profile_photo/"


DEFUALT_API_URL = "https://wiki.digitalmesh.com/"


DM_DESK_MEDIA_URL = DEFUALT_API_URL + "media/"

HOLIDAY_IMAGE_URL = DM_DESK_MEDIA_URL + "/holiday_images/"

PROFILE_IMAGE_PROVISIONAL = DM_DESK_MEDIA_URL + 'confidential_docs/profile_image_provisional'

EVENTS_MEDIA_URL = DM_DESK_MEDIA_URL + "/event_images/"

CONFIDENTIAL_DOCS = '/var/www/dm_ptracker/confidential_docs/'

APPRISAL_LEADS = [7,8,11,12,15,16,17,18,24,27,54]

