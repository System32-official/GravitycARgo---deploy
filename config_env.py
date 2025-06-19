"""
Environment-based configuration for the container packing application.
This module provides centralized configuration management using environment variables
with sensible defaults for development and production environments.
"""
import os
from pathlib import Path

class Config:
    """Base configuration class with environment variable support"""
    
    # Base paths
    BASE_DIR = Path(__file__).parent.absolute()
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # File upload settings
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', str(BASE_DIR / 'uploads'))
    PLANS_FOLDER = os.getenv('PLANS_FOLDER', str(BASE_DIR / 'container_plans'))
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(16 * 1024 * 1024)))  # 16MB
    
    # Server ports
    MAIN_APP_PORT = int(os.getenv('MAIN_APP_PORT', '5000'))
    JSON_SERVER_PORT = int(os.getenv('JSON_SERVER_PORT', '8000'))
    ROUTE_TEMP_PORT = int(os.getenv('ROUTE_TEMP_PORT', '5001'))
    
    # External services
    NGROK_DOMAIN = os.getenv('NGROK_DOMAIN', 'destined-mammoth-flowing.ngrok-free.app')
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', str(1024 * 1024)))  # 1MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '10'))
    
    # Optimization settings
    GENETIC_ALGORITHM_GENERATIONS = int(os.getenv('GA_GENERATIONS', '50'))
    GENETIC_ALGORITHM_POPULATION = int(os.getenv('GA_POPULATION', '100'))
    OPTIMIZATION_TIMEOUT = int(os.getenv('OPTIMIZATION_TIMEOUT', '300'))  # 5 minutes
    
    # JSON server settings
    STANDARD_JSON_FILENAME = os.getenv('JSON_FILENAME', 'latest_container_plan.json')
    
    # Database settings (if needed in future)
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///container_packing.db')
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.PLANS_FOLDER, exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
    @classmethod
    def validate_config(cls):
        """Validate configuration values"""
        errors = []
        
        if cls.MAX_CONTENT_LENGTH <= 0:
            errors.append("MAX_CONTENT_LENGTH must be positive")
            
        if not (1 <= cls.MAIN_APP_PORT <= 65535):
            errors.append("MAIN_APP_PORT must be between 1 and 65535")
            
        if not (1 <= cls.JSON_SERVER_PORT <= 65535):
            errors.append("JSON_SERVER_PORT must be between 1 and 65535")
            
        if not (1 <= cls.ROUTE_TEMP_PORT <= 65535):
            errors.append("ROUTE_TEMP_PORT must be between 1 and 65535")
            
        if cls.GENETIC_ALGORITHM_GENERATIONS <= 0:
            errors.append("GENETIC_ALGORITHM_GENERATIONS must be positive")
            
        if cls.GENETIC_ALGORITHM_POPULATION <= 0:
            errors.append("GENETIC_ALGORITHM_POPULATION must be positive")
            
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))
            
        return True

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SECRET_KEY = os.getenv('SECRET_KEY')  # Must be set in production
    LOG_LEVEL = 'WARNING'
    
    @classmethod
    def validate_config(cls):
        """Additional validation for production"""
        super().validate_config()
        
        if not cls.SECRET_KEY or cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            raise ValueError("SECRET_KEY must be set for production")

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    UPLOAD_FOLDER = str(Config.BASE_DIR / 'test_uploads')
    PLANS_FOLDER = str(Config.BASE_DIR / 'test_plans')

# Configuration selection based on environment
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on FLASK_ENV environment variable"""
    env = os.getenv('FLASK_ENV', 'default')
    config_class = config_map.get(env, DevelopmentConfig)
    
    # Validate and prepare configuration
    config_class.validate_config()
    config_class.ensure_directories()
    
    return config_class

# Export the active configuration
active_config = get_config()
