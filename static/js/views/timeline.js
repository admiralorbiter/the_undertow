/**
 * Timeline View - Temporal distribution of articles
 */

export class TimelineView {
    constructor(container) {
        this.container = container;
        this.chart = null;
        this.data = null;
    }
    
    /**
     * Load and render timeline view
     */
    async load() {
        console.log('Loading Timeline View...');
        this.container.innerHTML = '<div id="timeline-chart" style="width: 100%; height: 400px;"></div>';
        
        try {
            const response = await fetch('/api/timeline');
            if (!response.ok) {
                throw new Error(`Timeline API error: ${response.status}`);
            }
            
            const data = await response.json();
            this.data = data;
            this.render(data);
        } catch (error) {
            console.error('Error loading timeline:', error);
            this.container.innerHTML = `
                <div style="text-align: center; padding: 4rem; color: #ef4444;">
                    <h3>Error Loading Timeline</h3>
                    <p>${error.message}</p>
                </div>
            `;
        }
    }
    
    /**
     * Render timeline chart using ECharts
     */
    render(data) {
        if (!window.echarts) {
            console.error('ECharts not loaded');
            return;
        }
        
        const chartDom = document.getElementById('timeline-chart');
        if (!chartDom) return;
        
        // Dispose existing chart
        if (this.chart) {
            this.chart.dispose();
        }
        
        this.chart = echarts.init(chartDom);
        
        // Prepare data
        const bins = data.bins || [];
        const dates = bins.map(b => b.date);
        
        // Get unique cluster IDs from all bins
        const clusterIds = new Set();
        bins.forEach(bin => {
            Object.keys(bin.by_cluster || {}).forEach(clusterId => {
                if (clusterId !== 'null') {
                    clusterIds.add(clusterId);
                }
            });
        });
        clusterIds.add('null'); // Always include unclustered
        
        // Create series for each cluster
        const series = Array.from(clusterIds).map(clusterId => {
            const values = bins.map(bin => bin.by_cluster?.[clusterId] || 0);
            return {
                name: clusterId === 'null' ? 'Unclustered' : `Cluster ${clusterId}`,
                type: 'line',
                stack: 'Total',
                areaStyle: {},
                emphasis: {
                    focus: 'series'
                },
                data: values
            };
        });
        
        // Add total line
        series.push({
            name: 'Total',
            type: 'line',
            lineStyle: {
                width: 2,
                type: 'dashed'
            },
            data: bins.map(b => b.count)
        });
        
        const option = {
            title: {
                text: 'Articles Over Time',
                left: 'center'
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross'
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
                containLabel: true
            },
            toolbox: {
                feature: {
                    saveAsImage: {},
                    dataZoom: {
                        yAxisIndex: 'none'
                    },
                    restore: {}
                }
            },
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: dates
            },
            yAxis: {
                type: 'value',
                name: 'Article Count'
            },
            dataZoom: [
                {
                    type: 'inside',
                    start: 0,
                    end: 100
                },
                {
                    start: 0,
                    end: 100
                }
            ],
            series: series
        };
        
        this.chart.setOption(option);
        
        // Handle brush events for filtering other views
        this.chart.on('brush', (params) => {
            if (params.areas && params.areas.length > 0) {
                const area = params.areas[0];
                const startIdx = area.coordRange[0];
                const endIdx = area.coordRange[1];
                const selectedDates = dates.slice(startIdx, endIdx + 1);
                // TODO: Emit event for other views to filter
                console.log('Timeline brush:', selectedDates);
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
     * Update chart with filtered data
     */
    updateWithFilter(clusterId) {
        // Reload with cluster filter
        if (clusterId) {
            fetch(`/api/timeline?cluster_id=${clusterId}`)
                .then(r => r.json())
                .then(data => this.render(data))
                .catch(err => console.error('Error updating timeline:', err));
        } else {
            this.load();
        }
    }
}
