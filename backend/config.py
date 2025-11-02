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
    MODEL_CACHE_DIR = os.getenv('MODEL_CACHE_DIR', os.path.join('data', 'models'))
    
    # P1: ML/NLP Configuration
    # Similarity and clustering
    SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', 0.60))
    CLUSTER_MIN_SIZE = int(os.getenv('CLUSTER_MIN_SIZE', 8))
    CLUSTER_MIN_SAMPLES = int(os.getenv('CLUSTER_MIN_SAMPLES', 1))
    KNN_K = int(os.getenv('KNN_K', 20))  # Top-k neighbors for similarity graph
    
    # UMAP configuration
    UMAP_N_NEIGHBORS = int(os.getenv('UMAP_N_NEIGHBORS', 15))
    UMAP_MIN_DIST = float(os.getenv('UMAP_MIN_DIST', 0.1))
    UMAP_METRIC = os.getenv('UMAP_METRIC', 'cosine')
    
    # FAISS index
    FAISS_INDEX_PATH = os.getenv('FAISS_INDEX_PATH', os.path.join('data', 'faiss.index'))
    
    # Embedding model
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    EMBEDDING_DIM = int(os.getenv('EMBEDDING_DIM', 384))
    
    # KeyBERT configuration
    KEYBERT_TOP_N = int(os.getenv('KEYBERT_TOP_N', 10))
    KEYBERT_TOP_K_LABELS = int(os.getenv('KEYBERT_TOP_K_LABELS', 3))
    
    # Ensure data directory exists
    @staticmethod
    def ensure_directories():
        """Create necessary directories if they don't exist."""
        Path(Config.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(Config.DATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(Config.MODEL_CACHE_DIR).mkdir(parents=True, exist_ok=True)

