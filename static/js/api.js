/**
 * API client for News Relationship Explorer
 */

const API_BASE = '/api';

export const api = {
    /**
     * Get articles with optional filters
     */
    async getArticles(params = {}) {
        const queryString = new URLSearchParams();
        
        if (params.q) queryString.append('q', params.q);
        if (params.from) queryString.append('from', params.from);
        if (params.to) queryString.append('to', params.to);
        if (params.outlet) queryString.append('outlet', params.outlet);
        if (params.limit) queryString.append('limit', params.limit);
        if (params.offset) queryString.append('offset', params.offset);
        
        const url = `${API_BASE}/articles?${queryString.toString()}`;
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        
        return await response.json();
    },
    
    /**
     * Ingest CSV file
     */
    async ingestCSV(csvPath) {
        const url = `${API_BASE}/ingest/csv?path=${encodeURIComponent(csvPath)}`;
        
        const response = await fetch(url, { method: 'POST' });
        if (!response.ok) {
            throw new Error(`Ingest error: ${response.statusText}`);
        }
        
        return await response.json();
    },
    
    /**
     * Get clusters
     */
    async getClusters() {
        const response = await fetch(`${API_BASE}/clusters`);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return await response.json();
    },
    
    /**
     * Get UMAP projection data
     */
    async getUMAP() {
        const response = await fetch(`${API_BASE}/umap`);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return await response.json();
    },
    
    /**
     * Get timeline data
     */
    async getTimeline(params = {}) {
        const queryString = new URLSearchParams();
        if (params.cluster_id) queryString.append('cluster_id', params.cluster_id);
        if (params.group_by) queryString.append('group_by', params.group_by);
        
        const url = `${API_BASE}/timeline${queryString.toString() ? '?' + queryString.toString() : ''}`;
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return await response.json();
    },
    
    /**
     * Get similar articles
     */
    async getSimilar(articleId, k = 10) {
        const response = await fetch(`${API_BASE}/similar/${articleId}?k=${k}`);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return await response.json();
    }
};

