import os
from pathlib import Path
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

# Load .env from backend directory if present
env_path = Path(__file__).resolve().parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

class Config:
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'
    
    # PaaS providers (Render, Railway, Heroku) pass port as PORT
    FLASK_PORT = int(os.getenv('PORT') or os.getenv('FLASK_PORT', 5000))
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    
    SECRET_KEY = os.getenv('SECRET_KEY', 'attendx_default_secret_key_dev_2026')
    JWT_SECRET = os.getenv('JWT_SECRET', 'attendx_super_secure_jwt_secret_key_2026_dev_environment_hmac_sha256_token')
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))

    # MySQL / Managed Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if DATABASE_URL:
        # Parse URI format: mysql://user:password@host:port/dbname
        parsed = urlparse(DATABASE_URL)
        DB_HOST = parsed.hostname or 'localhost'
        DB_PORT = parsed.port or 3306
        DB_USER = unquote(parsed.username) if parsed.username else 'root'
        DB_PASSWORD = unquote(parsed.password) if parsed.password else ''
        # Strip leading slash from path
        DB_NAME = parsed.path.lstrip('/') if parsed.path else 'attendx_db'
    else:
        DB_HOST = os.getenv('DB_HOST', 'localhost')
        DB_PORT = int(os.getenv('DB_PORT', 3306))
        DB_NAME = os.getenv('DB_NAME', 'attendx_db')
        DB_USER = os.getenv('DB_USER', 'user1')
        DB_PASSWORD = os.getenv('DB_PASSWORD', 'user123')

    # SSL / TLS support for Managed Cloud MySQL (e.g. Aiven, PlanetScale, AWS RDS)
    DB_SSL_ENABLED = os.getenv('DB_SSL', 'false').lower() in ('true', '1', 't', 'yes')
    DB_SSL_CA = os.getenv('DB_SSL_CA')

    # Production CORS Allowed Origins
    raw_cors = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000,*')
    if raw_cors.strip() == '*':
        CORS_ORIGINS = '*'
    else:
        CORS_ORIGINS = [origin.strip() for origin in raw_cors.split(',') if origin.strip()]
