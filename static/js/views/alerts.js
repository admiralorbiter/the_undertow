/**
 * Alerts View - Display anomaly detection alerts
 */

import { api } from '../api.js';

export class AlertsView {
    constructor(container) {
        this.container = container;
        this.filters = {
            alert_type: null,
            severity: null
        };
    }
    
    /**
     * Load and render alerts
     */
    async load(filters = {}) {
        this.filters = { ...this.filters, ...filters };
        console.log('Loading Alerts View...');
        
        // Show loading state
        this.container.innerHTML = `
            <div style="text-align: center; padding: 4rem; color: #64748b;">
                <div style="font-size: 1.2rem; margin-bottom: 1rem;">Loading alerts...</div>
                <div style="font-size: 0.9rem;">Fetching anomaly detections...</div>
            </div>
        `;
        
        try {
            // Fetch alerts
            const data = await api.getAlerts(this.filters);
            
            // Render alerts
            this.render(data.alerts);
            
        } catch (error) {
            console.error('Error loading alerts:', error);
            this.container.innerHTML = `
                <div style="text-align: center; padding: 4rem; color: #ef4444;">
                    <h3>Error Loading Alerts</h3>
                    <p>${error.message}</p>
                    <p style="font-size: 0.9rem; margin-top: 1rem;">
                        Please try again or contact support.
                    </p>
                </div>
            `;
        }
    }
    
    /**
     * Render alerts timeline
     */
    render(alerts) {
        if (!alerts || alerts.length === 0) {
            this.container.innerHTML = `
                <div class="alerts-container">
                    <div class="alerts-header">
                        <h2>Alerts</h2>
                        <div class="alerts-filters">
                            ${this.renderFilters()}
                        </div>
                    </div>
                    <div style="text-align: center; padding: 4rem; color: #64748b;">
                        <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">No alerts found</div>
                        <div style="font-size: 0.9rem;">No anomaly detections in the selected time period</div>
                    </div>
                </div>
            `;
            return;
        }
        
        // Build HTML structure
        let html = `
            <div class="alerts-container">
                <div class="alerts-header">
                    <h2>Alerts (${alerts.length})</h2>
                    <div class="alerts-filters">
                        ${this.renderFilters()}
                    </div>
                </div>
                <div class="alerts-timeline">
                    ${alerts.map(alert => this.formatAlertCard(alert)).join('')}
                </div>
            </div>
        `;
        
        this.container.innerHTML = html;
        
        // Setup event listeners
        this.setupEventListeners();
    }
    
    /**
     * Render filter controls
     */
    renderFilters() {
        const alertTypes = [
            { value: '', label: 'All Types' },
            { value: 'topic_surge', label: 'Topic Surge' },
            { value: 'story_reactivation', label: 'Reactivation' },
            { value: 'new_actor', label: 'New Actor' },
            { value: 'divergence', label: 'Divergence' }
        ];
        
        const severities = [
            { value: '', label: 'All Severity' },
            { value: 'high', label: 'High' },
            { value: 'medium', label: 'Medium' },
            { value: 'low', label: 'Low' }
        ];
        
        return `
            <select id="filter-alert-type" class="filter-select">
                ${alertTypes.map(t => 
                    `<option value="${t.value}" ${this.filters.alert_type === t.value ? 'selected' : ''}>${t.label}</option>`
                ).join('')}
            </select>
            <select id="filter-severity" class="filter-select">
                ${severities.map(s => 
                    `<option value="${s.value}" ${this.filters.severity === s.value ? 'selected' : ''}>${s.label}</option>`
                ).join('')}
            </select>
        `;
    }
    
    /**
     * Format alert card HTML
     */
    formatAlertCard(alert) {
        const typeIcon = this.getTypeIcon(alert.alert_type);
        const severityColor = this.getSeverityColor(alert.severity);
        const typeLabel = this.getTypeLabel(alert.alert_type);
        const timeAgo = this.formatTimeAgo(alert.triggered_at);
        
        return `
            <div class="alert-card ${alert.acknowledged ? 'acknowledged' : ''}" data-alert-id="${alert.id}">
                <div class="alert-header">
                    <div class="alert-icon-type">
                        <span class="alert-icon">${typeIcon}</span>
                        <span class="alert-type">${typeLabel}</span>
                    </div>
                    <div class="alert-badges">
                        <span class="alert-severity-badge severity-${alert.severity}" style="background: ${severityColor};">${alert.severity}</span>
                        ${alert.acknowledged ? '<span class="acknowledged-badge">✓ Acknowledged</span>' : ''}
                    </div>
                </div>
                <div class="alert-description">${this.escapeHtml(alert.description)}</div>
                <div class="alert-footer">
                    <div class="alert-time">${timeAgo}</div>
                    ${!alert.acknowledged ? `
                        <button class="btn-acknowledge" onclick="window.acknowledgeAlertById(${alert.id})">
                            Acknowledge
                        </button>
                    ` : ''}
                </div>
                ${this.renderAlertDetails(alert)}
            </div>
        `;
    }
    
    /**
     * Render alert details (expandable)
     */
    renderAlertDetails(alert) {
        try {
            const entityData = JSON.parse(alert.entity_json);
            const detailRows = Object.entries(entityData)
                .filter(([key]) => key !== 'description')
                .map(([key, value]) => `<tr><td class="detail-key">${this.escapeHtml(key)}</td><td>${this.escapeHtml(String(value))}</td></tr>`)
                .join('');
            
            if (detailRows) {
                return `
                    <details class="alert-details">
                        <summary>View Details</summary>
                        <table class="detail-table">
                            ${detailRows}
                        </table>
                    </details>
                `;
            }
        } catch (e) {
            console.warn('Could not parse entity_json:', e);
        }
        return '';
    }
    
    /**
     * Get type icon
     */
    getTypeIcon(alertType) {
        const icons = {
            'topic_surge': '📈',
            'story_reactivation': '🔄',
            'new_actor': '⭐',
            'divergence': '⚠️'
        };
        return icons[alertType] || '🔔';
    }
    
    /**
     * Get type label
     */
    getTypeLabel(alertType) {
        const labels = {
            'topic_surge': 'Topic Surge',
            'story_reactivation': 'Story Reactivation',
            'new_actor': 'New Actor',
            'divergence': 'Divergence'
        };
        return labels[alertType] || alertType;
    }
    
    /**
     * Get severity color
     */
    getSeverityColor(severity) {
        const colors = {
            'high': '#ef4444',
            'medium': '#f59e0b',
            'low': '#3b82f6'
        };
        return colors[severity] || '#64748b';
    }
    
    /**
     * Format time ago
     */
    formatTimeAgo(timestamp) {
        try {
            const now = new Date();
            const then = new Date(timestamp);
            const diffMs = now - then;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);
            
            if (diffMins < 60) {
                return `${diffMins}m ago`;
            } else if (diffHours < 24) {
                return `${diffHours}h ago`;
            } else if (diffDays < 7) {
                return `${diffDays}d ago`;
            } else {
                return then.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            }
        } catch {
            return timestamp;
        }
    }
    
    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Filter dropdowns
        const filterType = this.container.querySelector('#filter-alert-type');
        const filterSeverity = this.container.querySelector('#filter-severity');
        
        if (filterType) {
            filterType.addEventListener('change', (e) => {
                this.filters.alert_type = e.target.value || null;
                this.load(this.filters);
            });
        }
        
        if (filterSeverity) {
            filterSeverity.addEventListener('change', (e) => {
                this.filters.severity = e.target.value || null;
                this.load(this.filters);
            });
        }
    }
    
    /**
     * Utility: Escape HTML
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global acknowledge function
window.acknowledgeAlertById = async function(alertId) {
    try {
        await api.acknowledgeAlert(alertId);
        
        // Reload alerts view
        const alertsView = window.alertsView;
        if (alertsView) {
            await alertsView.load(alertsView.filters);
        }
    } catch (error) {
        console.error('Error acknowledging alert:', error);
        alert('Failed to acknowledge alert. Please try again.');
    }
};

