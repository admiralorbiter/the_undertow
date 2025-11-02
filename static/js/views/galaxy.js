/**
 * Galaxy View - UMAP scatter plot visualization
 */

export class GalaxyView {
    constructor(container) {
        this.container = container;
        this.chart = null;
        this.data = null;
        this.clusterVisibility = new Map(); // Track cluster visibility
        this.allClustersVisible = true;
    }
    
    /**
     * Load and render galaxy view
     */
    async load() {
        console.log('Loading Galaxy View...');
        this.container.innerHTML = `
            <div class="chart-container">
                <div class="chart-loading" id="galaxy-loading">Loading chart...</div>
                <div id="galaxy-chart" style="width: 100%; height: 600px; display: none;"></div>
            </div>
        `;
        
        try {
            // Fetch UMAP data with article details for tooltips
            const response = await fetch('/api/umap?include_details=true');
            if (!response.ok) {
                throw new Error(`UMAP API error: ${response.status}`);
            }
            
            const data = await response.json();
            this.data = data;
            
            // Hide loading, show chart
            const loadingEl = document.getElementById('galaxy-loading');
            const chartEl = document.getElementById('galaxy-chart');
            if (loadingEl) loadingEl.style.display = 'none';
            if (chartEl) chartEl.style.display = 'block';
            
            this.render(data);
        } catch (error) {
            console.error('Error loading galaxy view:', error);
            this.container.innerHTML = `
                <div style="text-align: center; padding: 4rem; color: #ef4444;">
                    <h3>Error Loading Galaxy View</h3>
                    <p>${error.message}</p>
                    <p style="font-size: 0.9rem; margin-top: 1rem;">
                        Make sure UMAP projection has been computed by running the pipeline.
                    </p>
                </div>
            `;
        }
    }
    
    /**
     * Render UMAP scatter plot using ECharts
     */
    render(data) {
        if (!window.echarts) {
            console.error('ECharts not loaded');
            return;
        }
        
        const chartDom = document.getElementById('galaxy-chart');
        if (!chartDom) return;
        
        // Dispose existing chart
        if (this.chart) {
            this.chart.dispose();
        }
        
        this.chart = echarts.init(chartDom);
        
        const points = data.points || [];
        
        if (points.length === 0) {
            this.container.innerHTML = `
                <div style="text-align: center; padding: 4rem; color: #64748b;">
                    <h3>No UMAP Data</h3>
                    <p>Run the pipeline to generate UMAP coordinates.</p>
                </div>
            `;
            return;
        }
        
        // Define distinct color palette for clusters (13+ colors)
        const clusterColors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
            '#c49c94', '#f7b6d3', '#dbdb8d', '#9edae5'
        ];
        
        // Group points by cluster for coloring
        const clustersMap = new Map();
        const articleMap = new Map(); // Map article IDs to full point data for tooltips
        
        points.forEach(point => {
            const clusterId = point.cluster_id !== null && point.cluster_id !== undefined 
                ? String(point.cluster_id) : 'null';
            if (!clustersMap.has(clusterId)) {
                clustersMap.set(clusterId, []);
            }
            
            // Store article data for tooltips
            articleMap.set(point.id, point);
            
            clustersMap.get(clusterId).push({
                name: `Article ${point.id}`,
                value: [point.x, point.y, point.id],
                cluster_id: point.cluster_id
            });
        });
        
        // Create series for each cluster with distinct colors
        const series = Array.from(clustersMap.entries()).map(([clusterId, clusterPoints], idx) => {
            const numericId = clusterId === 'null' ? -1 : parseInt(clusterId);
            const colorIdx = numericId >= 0 ? (numericId % clusterColors.length) : clusterColors.length - 1;
            
            return {
                name: clusterId === 'null' ? 'Unclustered' : `Cluster ${clusterId}`,
                type: 'scatter',
                data: clusterPoints,
                symbolSize: 8,
                itemStyle: {
                    color: clusterColors[colorIdx],
                    opacity: 0.7
                },
                emphasis: {
                    itemStyle: {
                        opacity: 1,
                        borderColor: '#333',
                        borderWidth: 2
                    }
                }
            };
        });
        
        const option = {
            title: {
                text: 'Article Similarity Galaxy',
                subtext: `${points.length} articles`,
                left: 'center'
            },
            tooltip: {
                trigger: 'item',
                formatter: (params) => {
                    const point = params.data.value;
                    const articleId = point[2];
                    const article = articleMap.get(articleId);
                    
                    if (article && article.title) {
                        const title = article.title.length > 60 
                            ? article.title.substring(0, 60) + '...' 
                            : article.title;
                        const summary = article.summary 
                            ? (article.summary.length > 100 
                                ? article.summary.substring(0, 100) + '...' 
                                : article.summary)
                            : 'No summary';
                        return `
                            <div style="max-width: 300px;">
                                <strong>${title}</strong><br/>
                                <span style="font-size: 0.85em; color: #64748b;">${summary}</span><br/>
                                <span style="font-size: 0.8em; color: #94a3b8;">Position: (${point[0].toFixed(2)}, ${point[1].toFixed(2)})</span>
                            </div>
                        `;
                    } else {
                        return `Article ${articleId}<br/>Position: (${point[0].toFixed(2)}, ${point[1].toFixed(2)})`;
                    }
                }
            },
            legend: {
                data: series.map(s => s.name),
                bottom: 10,
                type: 'scroll',
                orient: 'horizontal',
                left: 'center',
                itemWidth: 14,
                itemHeight: 14,
                textStyle: {
                    fontSize: 11
                },
                pageIconColor: '#2563eb',
                pageIconInactiveColor: '#94a3b8',
                pageTextStyle: {
                    color: '#64748b'
                },
                selectedMode: true, // Enable clicking to toggle
                selected: this.getLegendSelectedState()
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                top: '10%',
                containLabel: true
            },
            toolbox: {
                feature: {
                    saveAsImage: {},
                    dataZoom: {
                        yAxisIndex: 'none'
                    },
                    restore: {
                        title: 'Reset View'
                    },
                    brush: {
                        type: ['rect', 'polygon', 'clear']
                    }
                }
            },
            brush: {
                toolbox: ['rect', 'polygon', 'clear']
            },
            xAxis: {
                type: 'value',
                name: 'UMAP X',
                nameLocation: 'middle',
                nameGap: 30,
                nameTextStyle: {
                    fontSize: 12,
                    fontWeight: 500,
                    color: '#475569'
                },
                scale: true
            },
            yAxis: {
                type: 'value',
                name: 'UMAP Y',
                nameLocation: 'middle',
                nameGap: 50,
                nameTextStyle: {
                    fontSize: 12,
                    fontWeight: 500,
                    color: '#475569'
                },
                scale: true
            },
            dataZoom: [
                {
                    type: 'slider',
                    xAxisIndex: 0,
                    start: 0,
                    end: 100
                },
                {
                    type: 'slider',
                    yAxisIndex: 0,
                    start: 0,
                    end: 100
                },
                {
                    type: 'inside',
                    xAxisIndex: 0,
                    start: 0,
                    end: 100
                },
                {
                    type: 'inside',
                    yAxisIndex: 0,
                    start: 0,
                    end: 100
                }
            ],
            series: series
        };
        
        this.chart.setOption(option);
        
        // Store articleMap for tooltip access
        this.articleMap = articleMap;
        
        // Handle legend click to toggle cluster visibility
        this.chart.on('legendselectchanged', (params) => {
            const seriesName = params.name;
            const isSelected = params.selected[seriesName];
            
            // Update visibility map
            this.clusterVisibility.set(seriesName, isSelected);
            
            // Check if all clusters are visible
            this.allClustersVisible = Array.from(this.clusterVisibility.values()).every(v => v);
            
            // Update chart with new visibility
            this.updateClusterVisibility();
        });
        
        // Handle click events to select article
        this.chart.on('click', (params) => {
            if (params.data && params.data.value) {
                const articleId = params.data.value[2];
                // Emit custom event for article selection
                const event = new CustomEvent('article-selected', {
                    detail: { articleId }
                });
                document.dispatchEvent(event);
            }
        });
    }
    
    /**
     * Get initial legend selected state (all visible)
     */
    getLegendSelectedState() {
        // Return empty object - will be populated by updateClusterVisibility
        return {};
    }
    
    /**
     * Update cluster visibility based on legend selections
     */
    updateClusterVisibility() {
        if (!this.chart) return;
        
        const option = this.chart.getOption();
        const legendSelected = {};
        
        // Build selected state object
        this.clusterVisibility.forEach((visible, name) => {
            legendSelected[name] = visible;
        });
        
        // Update legend selected state
        if (!option.legend) option.legend = {};
        option.legend.selected = legendSelected;
        
        this.chart.setOption(option, { notMerge: false });
    }
    
    /**
     * Toggle all clusters visibility
     */
    toggleAllClusters(show = true) {
        if (!this.chart) return;
        
        const option = this.chart.getOption();
        const legendSelected = {};
        
        // Get all series names
        const seriesNames = option.series ? option.series.map(s => s.name) : [];
        
        seriesNames.forEach(name => {
            this.clusterVisibility.set(name, show);
            legendSelected[name] = show;
        });
        
        this.allClustersVisible = show;
        
        if (!option.legend) option.legend = {};
        option.legend.selected = legendSelected;
        
        this.chart.setOption(option, { notMerge: false });
    }
    
    /**
     * Reset view to show all points centered
     */
    resetView() {
        if (!this.chart) return;
        
        // Use dispatchAction to trigger restore
        this.chart.dispatchAction({
            type: 'restore'
        });
    }
    
    /**
     * Resize chart when container size changes
     */
    resize() {
        if (this.chart) {
            this.chart.resize();
        }
    }
    
    /**
     * Highlight specific article
     */
    highlightArticle(articleId) {
        // TODO: Implement article highlighting
        console.log('Highlight article:', articleId);
    }
}
