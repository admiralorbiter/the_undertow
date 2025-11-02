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
        if (params.cluster_id !== null && params.cluster_id !== undefined) {
            queryString.append('cluster_id', params.cluster_id);
        }
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
    },
    
    /**
     * Get dashboard summary
     */
    async getDashboardSummary(daysBack = 30) {
        const response = await fetch(`${API_BASE}/dashboard/summary?days_back=${daysBack}`);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return await response.json();
    },
    
    /**
     * Get alerts with optional filters
     */
    async getAlerts(filters = {}) {
        const queryString = new URLSearchParams();
        
        if (filters.alert_type) queryString.append('alert_type', filters.alert_type);
        if (filters.severity) queryString.append('severity', filters.severity);
        if (filters.since) queryString.append('since', filters.since);
        if (filters.limit) queryString.append('limit', filters.limit);
        
        const url = `${API_BASE}/alerts${queryString.toString() ? '?' + queryString.toString() : ''}`;
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        
        return await response.json();
    },
    
    /**
     * Acknowledge an alert
     */
    async acknowledgeAlert(alertId) {
        const response = await fetch(`${API_BASE}/alerts/${alertId}/acknowledge`, { method: 'POST' });
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return await response.json();
    },
    
    /**
     * Run monitoring detections
     */
    async runMonitoring() {
        const response = await fetch(`${API_BASE}/monitoring/run`, { method: 'POST' });
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return await response.json();
    },
    
    /**
     * Get monitoring statistics
     */
    async getMonitoringStats() {
        const response = await fetch(`${API_BASE}/monitoring/stats`);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return await response.json();
    }
};

