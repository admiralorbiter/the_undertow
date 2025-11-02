"""
News Relationship Explorer - Flask Application Entry Point

Run with: python app.py
"""
from flask import Flask, send_from_directory
from backend.db import init_db
from backend.api import register_blueprints
import os


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder='static', static_url_path='')
    
    # Load configuration
    try:
        from backend.config import Config
        app.config.from_object(Config)
    except ImportError:
        # Fallback if config module doesn't exist yet
        app.config['DATABASE'] = os.path.join('instance', 'app.db')
        app.config['SECRET_KEY'] = os.urandom(24).hex()
        app.config['PORT'] = 5000
    
    # Ensure instance directory exists
    os.makedirs('instance', exist_ok=True)
    
    # Initialize database
    init_db()
    
    # Register API blueprints
    register_blueprints(app)
    
    # Serve index.html at root
    @app.route('/')
    def index():
        return send_from_directory('static', 'index.html')
    
    return app


if __name__ == '__main__':
    app = create_app()
    port = app.config.get('PORT', 5000)
    app.run(debug=True, host='127.0.0.1', port=port)

