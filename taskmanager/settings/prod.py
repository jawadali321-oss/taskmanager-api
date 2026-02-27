from .base import *
import os
import dj_database_url

DEBUG = False

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
    )
}
