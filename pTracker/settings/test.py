""" Settings for `manage.py test` only:
    DJANGO_SETTINGS_MODULE=pTracker.settings.test python manage.py test pTracker.tests

The MySQL user has no CREATE DATABASE grant and the eSSL/HRMS databases are
external, so tests run on an in-memory SQLite database built from the managed
apps' migrations (platform_access, auth, ...). Tests that need the unmanaged
legacy tables cannot run here. """

import tempfile

from .development import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

COMPANY_DOCUMENT_STORAGE_ROOT = tempfile.mkdtemp(prefix='company-docs-test-')
