"""
WSGI config for pTracker project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pTracker.settings')



if settings.DEBUG:
    import debugpy
    debugpy.listen(("0.0.0.0", 3000))
    # debugpy.wait_for_client()
    print('Attached!')
    

application = get_wsgi_application()
