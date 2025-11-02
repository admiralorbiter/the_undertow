"""API blueprints for News Relationship Explorer."""
from flask import Blueprint
from backend.api.articles import articles_bp
from backend.api.clusters import clusters_bp
from backend.api.umap import umap_bp
from backend.api.similar import similar_bp
from backend.api.timeline import timeline_bp


def register_blueprints(app):
    """Register all API blueprints with the Flask app."""
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    
    # Register article endpoints
    api_bp.register_blueprint(articles_bp)
    
    # Register P1 endpoints
    api_bp.register_blueprint(clusters_bp)
    api_bp.register_blueprint(umap_bp)
    api_bp.register_blueprint(similar_bp)
    api_bp.register_blueprint(timeline_bp)
    
    app.register_blueprint(api_bp)

