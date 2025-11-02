"""API blueprints for News Relationship Explorer."""
from flask import Blueprint
from backend.api.articles import articles_bp
from backend.api.clusters import clusters_bp
from backend.api.umap import umap_bp
from backend.api.similar import similar_bp
from backend.api.timeline import timeline_bp
from backend.api.entities import entities_bp
from backend.api.storylines import storylines_bp
from backend.api.dashboard import dashboard_bp
from backend.api.monitoring import monitoring_bp


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
    
    # Register P2 endpoints
    api_bp.register_blueprint(entities_bp)
    api_bp.register_blueprint(storylines_bp)
    
    # Register P3 endpoints
    api_bp.register_blueprint(dashboard_bp)
    api_bp.register_blueprint(monitoring_bp)
    
    app.register_blueprint(api_bp)

