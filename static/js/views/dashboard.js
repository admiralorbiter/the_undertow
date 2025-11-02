/**
 * Dashboard View - State-of-the-World summary
 */

import { api } from '../api.js';

export class DashboardView {
    constructor(container) {
        this.container = container;
        this.daysBack = 30;  // Default
        this.charts = {};    // Store ECharts instances
        this.data = null;
    }
    
    /**
     * Load and render dashboard
     */
    async load(daysBack = 30) {
        this.daysBack = daysBack;
        console.log('Loading Dashboard View...');
        
        // Show loading state
        this.container.innerHTML = `
            <div style="text-align: center; padding: 4rem; color: #64748b;">
                <div style="font-size: 1.2rem; margin-bottom: 1rem;">Loading dashboard...</div>
                <div style="font-size: 0.9rem;">Fetching aggregated data...</div>
            </div>
        `;
        
        try {
            // Fetch dashboard data
            const data = await api.getDashboardSummary(daysBack);
            this.data = data;
            
            // Render full dashboard
            this.render(data);
            
        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.container.innerHTML = `
                <div style="text-align: center; padding: 4rem; color: #ef4444;">
                    <h3>Error Loading Dashboard</h3>
                    <p>${error.message}</p>
                    <p style="font-size: 0.9rem; margin-top: 1rem;">
                        Please try again or contact support.
                    </p>
                </div>
            `;
        }
    }
    
    /**
     * Render full dashboard layout
     */
    render(data) {
        if (!window.echarts) {
            console.error('ECharts not loaded');
            return;
        }
        
        // Build HTML structure
        let html = `
            <div class="dashboard-layout">
                <!-- Date Range Selector -->
                <div class="dashboard-controls">
                    <button class="btn-range ${this.daysBack === 7 ? 'active' : ''}" data-days="7">7 Days</button>
                    <button class="btn-range ${this.daysBack === 30 ? 'active' : ''}" data-days="30">30 Days</button>
                    <button class="btn-range ${this.daysBack === 90 ? 'active' : ''}" data-days="90">90 Days</button>
                    <button class="btn-range ${this.daysBack === 365 ? 'active' : ''}" data-days="365">All</button>
                </div>
                
                <!-- Stats Cards -->
                <div class="dashboard-stats">
                    ${this.renderStatsCard('Total Articles', data.stats.total_articles, '#2563eb')}
                    ${this.renderStatsCard('Active Storylines', data.stats.active_storylines_count, '#10b981')}
                    ${this.renderStatsCard('Dormant Storylines', data.stats.dormant_storylines_count, '#64748b')}
                    ${this.renderStatsCard('Total Entities', data.stats.total_entities, '#f59e0b')}
                    ${this.renderStatsCard('New (7d)', data.stats.new_articles_7d, '#8b5cf6')}
                    ${this.renderStatsCard('Unacknowledged Alerts', data.stats.unacknowledged_alerts || 0, '#ef4444')}
                </div>
                
                <!-- Main Content Grid -->
                <div class="dashboard-content">
                    <!-- Left: Active Storylines -->
                    <div class="dashboard-panel">
                        <h3>Active Storylines</h3>
                        <div class="storyline-list" id="storylines-list">
                            ${this.renderStorylines(data.active_storylines)}
                        </div>
                    </div>
                    
                    <!-- Center: Temporal Heatmap -->
                    <div class="dashboard-panel">
                        <h3>Temporal Heatmap</h3>
                        <div class="chart-container" id="heatmap-chart"></div>
                    </div>
                    
                    <!-- Right: Key Actors -->
                    <div class="dashboard-panel">
                        <h3>Key Actors (7d)</h3>
                        <div class="actor-list" id="actors-list">
                            ${this.renderActors(data.key_actors)}
                        </div>
                    </div>
                </div>
                
                <!-- Bottom: Cluster Evolution -->
                <div class="dashboard-bottom">
                    <h3>Cluster Evolution</h3>
                    <div class="chart-container" id="evolution-chart"></div>
                </div>
            </div>
        `;
        
        this.container.innerHTML = html;
        
        // Setup event listeners for date range buttons
        this.setupEventListeners();
        
        // Render ECharts visualizations
        this.renderHeatmap(data.temporal_heatmap);
        this.renderClusterEvolution(data.cluster_evolution);
    }
    
    /**
     * Render stats card
     */
    renderStatsCard(label, value, color) {
        return `
            <div class="stat-card" style="border-left: 4px solid ${color};">
                <div class="stat-value" style="color: ${color};">${value.toLocaleString()}</div>
                <div class="stat-label">${label}</div>
            </div>
        `;
    }
    
    /**
     * Render storylines list
     */
    renderStorylines(storylines) {
        if (!storylines || storylines.length === 0) {
            return '<div class="empty-state">No active storylines</div>';
        }
        
        return storylines.map(s => {
            const statusColor = s.status === 'active' ? '#10b981' : '#64748b';
            const dateRange = s.first_date === s.last_date 
                ? this.formatDate(s.last_date)
                : `${this.formatDate(s.first_date)} - ${this.formatDate(s.last_date)}`;
            
            return `
                <div class="storyline-item" data-id="${s.id}" title="${this.escapeHtml(s.label)}">
                    <div class="storyline-header">
                        <div class="storyline-label">${this.escapeHtml(s.label)}</div>
                        <span class="status-badge" style="background: ${statusColor};">${s.status}</span>
                    </div>
                    <div class="storyline-meta">
                        <span class="meta-item"><strong>${s.article_count}</strong> articles</span>
                        <span class="meta-separator">•</span>
                        <span class="meta-item">Momentum: <strong>${s.momentum_score.toFixed(2)}</strong></span>
                    </div>
                    <div class="storyline-date">${dateRange}</div>
                </div>
            `;
        }).join('');
    }
    
    /**
     * Format date for display
     */
    formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr + 'T00:00:00');
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        } catch {
            return dateStr;
        }
    }
    
    /**
     * Render actors list
     */
    renderActors(actors) {
        if (!actors || actors.length === 0) {
            return '<div class="empty-state">No data</div>';
        }
        
        const typeColors = {
            'PERSON': '#3b82f6',
            'ORG': '#f59e0b',
            'GPE': '#10b981',
            'LOC': '#8b5cf6',
            'OTHER': '#64748b'
        };
        
        return actors.map(a => {
            const color = typeColors[a.type] || typeColors['OTHER'];
            return `
                <div class="actor-item" data-entity-id="${a.entity_id}" title="Click to filter articles">
                    <div>
                        <div class="actor-name">${this.escapeHtml(a.name)}</div>
                        <span class="entity-type-badge" style="background: ${color};">${a.type}</span>
                    </div>
                    <div class="actor-mentions">${a.mentions_7d}</div>
                </div>
            `;
        }).join('');
    }
    
    /**
     * Render temporal heatmap using ECharts
     */
    renderHeatmap(heatmapData) {
        const chartDom = document.getElementById('heatmap-chart');
        if (!chartDom) return;
        
        // Dispose existing chart
        if (this.charts.heatmap) {
            this.charts.heatmap.dispose();
        }
        
        this.charts.heatmap = echarts.init(chartDom);
        
        if (!heatmapData || heatmapData.length === 0) {
            chartDom.innerHTML = '<div class="empty-state">No data</div>';
            return;
        }
        
        // Prepare data for calendar heatmap
        // Convert to date-value format
        const data = heatmapData.map(d => [d.date, d.count]);
        
        // Get date range
        const dates = heatmapData.map(d => d.date);
        const minDate = dates[0];
        const maxDate = dates[dates.length - 1];
        
        // Calculate days between
        const startDate = new Date(minDate);
        const endDate = new Date(maxDate);
        const days = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
        const cellSize = Math.max(15, Math.min(25, Math.floor(chartDom.offsetWidth / 20)));
        
        const option = {
            tooltip: {
                position: 'top',
                formatter: (params) => {
                    const date = new Date(params.data[0]);
                    const formatted = date.toLocaleDateString('en-US', { 
                        weekday: 'short', 
                        month: 'short', 
                        day: 'numeric', 
                        year: 'numeric' 
                    });
                    return `<strong>${formatted}</strong><br/>${params.data[1]} article${params.data[1] !== 1 ? 's' : ''}`;
                }
            },
            visualMap: {
                min: 0,
                max: Math.max(...heatmapData.map(d => d.count)),
                calculable: true,
                orient: 'horizontal',
                left: 'center',
                bottom: 20,
                inRange: {
                    color: ['#ffffff', '#2563eb']
                }
            },
            calendar: {
                top: 60,
                left: 30,
                right: 30,
                cellSize: cellSize,
                range: [minDate, maxDate],
                itemStyle: {
                    borderWidth: 2,
                    borderColor: '#fff'
                },
                yearLabel: { show: false },
                dayLabel: {
                    firstDay: 0,
                    nameMap: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                },
                monthLabel: {
                    nameMap: 'en'
                }
            },
            series: {
                type: 'heatmap',
                coordinateSystem: 'calendar',
                data: data
            }
        };
        
        this.charts.heatmap.setOption(option);
    }
    
    /**
     * Render cluster evolution chart
     */
    renderClusterEvolution(evolutionData) {
        const chartDom = document.getElementById('evolution-chart');
        if (!chartDom) return;
        
        // Dispose existing chart
        if (this.charts.evolution) {
            this.charts.evolution.dispose();
        }
        
        this.charts.evolution = echarts.init(chartDom);
        
        if (!evolutionData || evolutionData.length === 0) {
            chartDom.innerHTML = '<div class="empty-state">No data</div>';
            return;
        }
        
        // Prepare data for stacked area chart
        // First, get all unique cluster IDs
        const clusterIds = new Set();
        evolutionData.forEach(d => {
            Object.keys(d.cluster_sizes).forEach(id => clusterIds.add(parseFloat(id)));
        });
        const sortedClusterIds = Array.from(clusterIds).sort((a, b) => a - b);
        
        // Build series data for each cluster
        const dates = evolutionData.map(d => d.date);
        const series = sortedClusterIds.map(clusterId => {
            return {
                name: `Cluster ${clusterId}`,
                type: 'line',
                stack: 'Total',
                areaStyle: {},
                emphasis: {
                    focus: 'series'
                },
                data: evolutionData.map(d => d.cluster_sizes[clusterId] || 0)
            };
        });
        
        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross',
                    label: {
                        backgroundColor: '#6a7985'
                    }
                },
                formatter: (params) => {
                    let result = `<strong>${params[0].axisValue}</strong><br/>`;
                    let total = 0;
                    params.forEach(p => {
                        if (p.value > 0) {
                            result += `${p.marker} ${p.seriesName}: ${p.value}<br/>`;
                            total += p.value;
                        }
                    });
                    result += `<br/><strong>Total: ${total} articles</strong>`;
                    return result;
                }
            },
            legend: {
                data: sortedClusterIds.map(id => `Cluster ${id}`),
                type: 'scroll',
                orient: 'horizontal',
                bottom: 0
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                top: '5%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: dates
            },
            yAxis: {
                type: 'value'
            },
            series: series
        };
        
        this.charts.evolution.setOption(option);
    }
    
    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Date range buttons
        const rangeButtons = this.container.querySelectorAll('.btn-range');
        rangeButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const days = parseInt(e.target.dataset.days);
                this.load(days);
            });
        });
        
        // Storyline click handlers
        const storylineItems = this.container.querySelectorAll('.storyline-item');
        storylineItems.forEach(item => {
            item.addEventListener('click', async (e) => {
                const storylineId = parseInt(e.currentTarget.dataset.id);
                console.log('Storyline clicked:', storylineId);
                
                try {
                    // Fetch storyline articles
                    const response = await fetch(`/api/storyline/${storylineId}/articles`);
                    if (!response.ok) throw new Error('Failed to load storyline');
                    
                    const data = await response.json();
                    
                    // Dispatch custom event to navigate to list view with storyline filter
                    document.dispatchEvent(new CustomEvent('storyline-selected', {
                        detail: {
                            storylineId: storylineId,
                            storyline: data.storyline,
                            articles: data.articles
                        }
                    }));
                } catch (error) {
                    console.error('Error loading storyline:', error);
                }
            });
        });
        
        // Actor click handlers
        const actorItems = this.container.querySelectorAll('.actor-item');
        actorItems.forEach(item => {
            item.addEventListener('click', (e) => {
                const entityId = parseInt(e.currentTarget.dataset.entityId);
                console.log('Entity clicked:', entityId);
                
                // Dispatch custom event to navigate to list view with entity filter
                document.dispatchEvent(new CustomEvent('entity-selected', {
                    detail: {
                        entityId: entityId
                    }
                }));
            });
        });
    }
    
    /**
     * Resize all charts
     */
    resize() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.resize === 'function') {
                chart.resize();
            }
        });
    }
    
    /**
     * Destroy and cleanup
     */
    destroy() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.dispose === 'function') {
                chart.dispose();
            }
        });
        this.charts = {};
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

