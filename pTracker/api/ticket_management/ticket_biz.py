from hashlib import new
import json
import time
from types import SimpleNamespace
from datetime import date, datetime
import io
import os
import zipfile

from django.conf import settings
from django.db import  transaction
from django.http import HttpResponse

from celery.result import AsyncResult
from cryptography.fernet import Fernet
