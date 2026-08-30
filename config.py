"""
Configuração centralizada da aplicação Flask
"""
import os
from datetime import timedelta

class Config:
    """Configuração base"""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Flask Session
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.environ.get('SESSION_TIMEOUT_MINUTES', 30)))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_NAME = 'PRAZER_SESSION'
    
    # Database
    MONGO_URI = os.environ.get('MONGODB_URI')
    MONGO_DBNAME = os.environ.get('MONGODB_DB_NAME', 'prazer_burguer')
    
    # Rate Limiting
    RATELIMIT_DEFAULT = os.environ.get('RATE_LIMIT', '10 per minute')
    
    # Security
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    LOCKOUT_DURATION = int(os.environ.get('LOCKOUT_DURATION_MINUTES', 15))
    
    # WhatsApp
    WHATSAPP_API_TOKEN = os.environ.get('WHATSAPP_API_TOKEN')
    WHATSAPP_BUSINESS_PHONE_ID = os.environ.get('WHATSAPP_BUSINESS_PHONE_ID')
    WHATSAPP_BUSINESS_NUMBER = os.environ.get('WHATSAPP_BUSINESS_NUMBER')
    WHATSAPP_API_URL = 'https://graph.instagram.com/v18.0/me/messages'
    
    # Sentry
    SENTRY_DSN = os.environ.get('SENTRY_DSN')

class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    FLASK_DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Configuração para produção"""
    FLASK_DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Configuração para testes"""
    TESTING = True
    MONGO_URI = 'mongodb://localhost:27017/prazer_burguer_test'
    SESSION_COOKIE_SECURE = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
