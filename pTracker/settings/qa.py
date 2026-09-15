from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': {
             'sql_mode': 'traditional',},
        'NAME': str(os.getenv('DB_NAME')),
        'USER': str(os.getenv('DB_USER')),
        'PASSWORD': str(os.getenv('DB_PWD')),
        'HOST': str(os.getenv('DB_HOST')),
        'PORT': '3306',
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


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'

# STATICFILES_DIRS = [
#         os.path.join(BASE_DIR, 'static')
#     ]
STATICFILES_DIRS = [
    BASE_DIR  ,"static",
    '/home/tyson/projects/pTracker/backend_app/static/',
]

MEDIA_ROOT = '/var/www/dm_ptracker/backend_app/media/'

#MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
BASE_URL = 'http://localhost:4200/#/'

OFFBOARD_DOCUMENT_URL = MEDIA_ROOT+'offboarding_documents'

DEFAULT_SITE_MEDIA_URL = "http://dmdeskadminqa.digitalmesh.com/media/employee_profile_photo/"

#EMP_PROFILE_IMAGE_URL = DEFAULT_SITE_MEDIA_URL+ 'employee_profile_photo/' TODO

DEFUALT_API_URL = "http://dmdeskadminqa.digitalmesh.com/"


DM_DESK_MEDIA_URL = DEFUALT_API_URL+ "media/"

HOLIDAY_IMAGE_URL = DM_DESK_MEDIA_URL + "/holiday_images/"

# CONFIDENTIAL_MEDIA= "http://dmdeskadminqa.digitalmesh.com/media/confidential_docs/"

PROFILE_IMAGE_PROVISIONAL = DM_DESK_MEDIA_URL + 'confidential_docs/profile_image_provisional'

CONFIDENTIAL_DOCS = '/var/www/dm_ptracker/confidential_docs/'

# PROFILE_IMAGE_PROVISIONAL = CONFIDENTIAL_MEDIA+'profile_image_provisional'

