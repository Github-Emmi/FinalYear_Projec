
import os 
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = ['www.febmexinternationalschools.com', 'febmexinternationalschools.com']

# Application definition
AUTH_USER_MODEL = "schoolapp.CustomUser"
AUTHENTICATION_BACKENDS = ["schoolapp.EmailBackEnd.EmailBackEnd"]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Custom apps
    'schoolapp.apps.SchoolappConfig',
    'cloudinary',
    'cloudinary_storage',
    'notifications',
    'django.contrib.humanize',
]



# Cloudinary configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'dmkcqgan1',          # Replace with your Cloud Name
    'API_KEY': '716231591674135',      # Replace with your API Key
    'API_SECRET': 'lVtlknqZrOUITzpCqmQjWNMUvkQ',  # Replace with your API Secret
    'DEFAULT_RESOURCE_TYPE': 'raw',  # Set to 'raw' for non-image files
    'OPTIONS': {
        'resource_type': 'raw',
        'type': 'upload'
    }
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this line
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'schoolapp.middleware.RememberMeMiddleware', # Custom middleware for "Remember Me"
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'schoolapp.LoginCheckMiddleWare.LoginCheckMiddleWare',
]

ROOT_URLCONF = 'school_management_system.urls'

TEMPLATES_DIR = os.path.join(BASE_DIR, 'schoolapp/templates/jobs')
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # ⬇️ Add this line below
                'schoolapp.context_processors.student_sessions_context',  # ✅ Add this line
            ],
        },
    },
]

WSGI_APPLICATION = 'school_management_system.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        # 'ENGINE': 'django.db.backends.sqlite3',
        # 'NAME': BASE_DIR / 'db.sqlite3',
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'emmidev$febmexdb',
        'USER': 'emmidev',
        'PASSWORD': 'Febmexdb1999',
        'HOST': 'emmidev.mysql.pythonanywhere-services.com',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },

    }
}



# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

# Static files configuration
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'cloudinary_storage.storage.StaticHashedCloudinaryStorage'

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'


# Static root (for Heroku)
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')


# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


