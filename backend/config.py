"""
Configuration management for the Flask application.
Loads settings from environment variables or uses sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Application configuration."""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    PORT = int(os.getenv('PORT', 5000))
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'instance/app.db')
    
    # Data paths
    DATA_DIR = os.getenv('DATA_DIR', 'data')
    
    # Ensure data directory exists
    @staticmethod
    def ensure_directories():
        """Create necessary directories if they don't exist."""
        Path(Config.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(Config.DATA_DIR).mkdir(parents=True, exist_ok=True)

