"""API blueprints for News Relationship Explorer."""
from flask import Blueprint
from backend.api.articles import articles_bp


def register_blueprints(app):
    """Register all API blueprints with the Flask app."""
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    
    # Register article endpoints
    api_bp.register_blueprint(articles_bp)
    
    app.register_blueprint(api_bp)

