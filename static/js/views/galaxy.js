/**
 * Galaxy View - UMAP scatter plot visualization
 */

export class GalaxyView {
    constructor(container) {
        this.container = container;
        this.chart = null;
        this.data = null;
    }
    
    /**
     * Load and render galaxy view
     */
    async load() {
        console.log('Loading Galaxy View...');
        this.container.innerHTML = '<div id="galaxy-chart" style="width: 100%; height: 600px;"></div>';
        
        try {
            const response = await fetch('/api/umap');
            if (!response.ok) {
                throw new Error(`UMAP API error: ${response.status}`);
            }
            
            const data = await response.json();
            this.data = data;
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
        
        // Group points by cluster for coloring
        const clustersMap = new Map();
        points.forEach(point => {
            const clusterId = point.cluster_id !== null && point.cluster_id !== undefined 
                ? String(point.cluster_id) : 'null';
            if (!clustersMap.has(clusterId)) {
                clustersMap.set(clusterId, []);
            }
            clustersMap.get(clusterId).push({
                name: `Article ${point.id}`,
                value: [point.x, point.y, point.id],
                cluster_id: point.cluster_id
            });
        });
        
        // Create series for each cluster
        const series = Array.from(clustersMap.entries()).map(([clusterId, clusterPoints]) => ({
            name: clusterId === 'null' ? 'Unclustered' : `Cluster ${clusterId}`,
            type: 'scatter',
            data: clusterPoints,
            symbolSize: 8,
            itemStyle: {
                opacity: 0.7
            },
            emphasis: {
                itemStyle: {
                    opacity: 1,
                    borderColor: '#333',
                    borderWidth: 2
                }
            }
        }));
        
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
                    // Try to find article title from data if available
                    return `Article ${articleId}<br/>Position: (${point[0].toFixed(2)}, ${point[1].toFixed(2)})`;
                }
            },
            legend: {
                data: series.map(s => s.name),
                bottom: 10
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
                    restore: {},
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
                scale: true
            },
            yAxis: {
                type: 'value',
                name: 'UMAP Y',
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
