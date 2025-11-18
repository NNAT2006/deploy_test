from pathlib import Path
import os

# --- 1. TẢI BIẾN MÔI TRƯỜNG TỪ .ENV (TÊN FILE LÀ .env, CÙNG CẤP VỚI THƯ MỤC SETTINGS NÀY) ---
try:
    from dotenv import load_dotenv
    # Đường dẫn giả định file .env nằm ở thư mục gốc (cùng cấp với manage.py)
    # Tức là một cấp trên thư mục chứa settings.py
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(env_path)
    # NOTE: ĐÃ BỎ CODE DEBUG PRINT Ở ĐÂY ĐỂ TRÁNH NHẦM LẪN
except ImportError:
    # python-dotenv not installed; environment variables must be set externally
    pass
except Exception as e:
    print(f'Warning: Could not load .env: {e}')


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- 2. CẤU HÌNH API KEY/URL VÀ CÁC BIẾN MÔI TRƯỜNG CHÍNH ---

# Gemini / Generative API settings - Lấy trực tiếp từ môi trường
# Nếu bạn không muốn giá trị mặc định là None, hãy dùng os.getenv('TEN_BIEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
# Đặt giá trị mặc định cho URL để tránh lỗi, nhưng nó sẽ được kiểm tra lại trong views
GEMINI_API_URL = os.getenv('GEMINI_API_URL')


# Email configuration (read from .env for SMTP)
# Sử dụng os.getenv để tránh lỗi lặp lại ở cuối file
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') in ('True', 'true', '1')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'no-reply@example.com')
SITE_URL = os.getenv('SITE_URL', '')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-2xr3+k=j0dvns9x86vts)qv$&9@o@3v@8l3!iu01w20r=sm49n'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['.render.com', '127.0.0.1']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'social_django',
    'django_celery_beat',
    'django_celery_results',
    'accounts',
]

# Social Auth settings
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = '1054490141259-q58r613bd9fgcevibu6htttau6nceeco.apps.googleusercontent.com'  # Client ID
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = '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'  # Client Secret

AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

# Social Auth Pipeline
# settings.py

# settings.py

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',

    # Nếu user đã tồn tại -> login luôn
    'social_core.pipeline.social_auth.social_user',

    # Tạo username từ email (nếu user chưa tồn tại)
    'accounts.pipeline.create_username',

    # BẮT BUỘC: cho phép pipeline dùng username bạn trả về
    'social_core.pipeline.user.get_username',

    # Tạo user mới
    'social_core.pipeline.user.create_user',

    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)



# Social Auth Settings
SOCIAL_AUTH_URL_NAMESPACE = 'social'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:user_dashboard'
LOGOUT_URL = 'accounts:logout'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Celery Configuration using SQLite as broker (for development only)
CELERY_BROKER_URL = 'sqla+sqlite:///celerydb.sqlite3'
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Ho_Chi_Minh'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Celery Beat settings
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# --- EMAIL CONFIGURATION (ĐÃ CHUYỂN LÊN TRÊN, CHỈ ĐỂ LOGIC) ---

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # LocaleMiddleware should be after SessionMiddleware and before CommonMiddleware
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mysite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
                # Add user progress context processor
                'accounts.context_processors.user_progress',
            ],
        },
    },
]

WSGI_APPLICATION = 'mysite.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600
    )
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

# Set default language to Vietnamese for the site/admin UI
LANGUAGE_CODE = 'vi'

TIME_ZONE = 'Asia/Ho_Chi_Minh'

USE_I18N = True

USE_TZ = True

# Available languages
from django.utils.translation import gettext_lazy as _
LANGUAGES = [
    ('vi', _('Vietnamese')),
    ('en', _('English')),
]


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [
    BASE_DIR / 'accounts' / 'static',
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media files (Uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- ĐÃ XÓA KHỐI CẤU HÌNH EMAIL VÀ GEMINI LẶP LẠI Ở CUỐI FILE ---
import sys
if 'runserver' in sys.argv:
    print("\n--- DEBUG GEMINI API KEY ---")
    FINAL_KEY_VALUE = os.getenv('GEMINI_API_KEY')
    FINAL_URL_VALUE = os.getenv('GEMINI_API_URL')
    print(f"FINAL GEMINI_API_KEY (Is set?): {bool(FINAL_KEY_VALUE)}")
    print(f"FINAL GEMINI_API_URL (Is set?): {bool(FINAL_URL_VALUE)}")
    if FINAL_KEY_VALUE:
         print(f"KEY LENGTH: {len(FINAL_KEY_VALUE)}")
    print("----------------------------\n")