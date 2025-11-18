import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------
# SECURITY
# -----------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-default-key")
DEBUG = os.getenv("DEBUG", "True") == "True"

# Allow frontend + backend + local development
ALLOWED_HOSTS = [
    "*",                                # Accept all hosts (Render requires this)
    "vervehire-api.onrender.com",
    "localhost",
    "127.0.0.1",
]

# -----------------------------------------
# INSTALLED APPS
# -----------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",

    # Local apps
    "api",
]

# -----------------------------------------
# MIDDLEWARE
# -----------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # MUST be at top
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "mockbackend.urls"

# -----------------------------------------
# TEMPLATES
# -----------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mockbackend.wsgi.application"
ASGI_APPLICATION = "mockbackend.asgi.application"

# -----------------------------------------
# DATABASE (SQLite → fine for Render)
# -----------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# -----------------------------------------
# PASSWORD VALIDATION
# -----------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------
# CORS CONFIG (THE MOST IMPORTANT)
# -----------------------------------------

CORS_ALLOW_ALL_ORIGINS = False

# Allowed React frontend origins (local + vercel)
CORS_ALLOWED_ORIGINS = [
    "https://vervehire-ui.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Allow cookies/token refresh from frontend
CORS_ALLOW_CREDENTIALS = True

# Allow all headers (fixes OPTIONS + file upload issues)
CORS_ALLOW_HEADERS = ["*"]

# Allow all methods
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]

# Required for POST requests from Vercel
CSRF_TRUSTED_ORIGINS = [
    "https://vervehire-ui.vercel.app",
    "https://vervehire-api.onrender.com",
]

# -----------------------------------------
# REST FRAMEWORK + JWT
# -----------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=90),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# -----------------------------------------
# STATIC & MEDIA
# -----------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------------------
# OPENAI
# -----------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
