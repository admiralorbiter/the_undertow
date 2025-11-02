/**
 * Timeline View - Temporal distribution of articles
 */

export class TimelineView {
    constructor(container) {
        this.container = container;
        this.chart = null;
        this.data = null;
        this.bins = null;
        this.rawDates = null; // Store raw date strings for filtering
        this.selectedBinIndex = null;
    }
    
    /**
     * Load and render timeline view
     */
    async load() {
        console.log('Loading Timeline View...');
        this.container.innerHTML = `
            <div class="chart-container">
                <div class="chart-loading" id="timeline-loading">Loading chart...</div>
                <div id="timeline-chart" style="width: 100%; height: 400px; display: none;"></div>
            </div>
        `;
        
        try {
            const response = await fetch('/api/timeline');
            if (!response.ok) {
                throw new Error(`Timeline API error: ${response.status}`);
            }
            
            const data = await response.json();
            this.data = data;
            
            // Hide loading, show chart
            const loadingEl = document.getElementById('timeline-loading');
            const chartEl = document.getElementById('timeline-chart');
            if (loadingEl) loadingEl.style.display = 'none';
            if (chartEl) chartEl.style.display = 'block';
            
            this.render(data);
        } catch (error) {
            console.error('Error loading timeline:', error);
            this.container.innerHTML = `
                <div class="error-message">
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
        
        if (bins.length === 0) {
            this.container.innerHTML = `
                <div class="empty-state">
                    <h3>No Timeline Data</h3>
                    <p>Run the pipeline to generate timeline data.</p>
                </div>
            `;
            return;
        }
        
        // Fix date formatting (e.g., "0225-10" -> "2025-10", "2024-10" -> "2024-10")
        const formatDate = (dateStr) => {
            if (!dateStr) return dateStr;
            // If date starts with 0, likely a year issue from SQLite strftime
            if (dateStr.match(/^0\d{2}-\d{2}$/)) {
                // Convert "0225-10" to "2025-10"
                return '20' + dateStr.substring(1);
            }
            // Format month display better (e.g., "2024-10" -> "Oct 2024")
            const parts = dateStr.split('-');
            if (parts.length === 2) {
                const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                const monthIdx = parseInt(parts[1]) - 1;
                if (monthIdx >= 0 && monthIdx < 12) {
                    return `${months[monthIdx]} ${parts[0]}`;
                }
            }
            return dateStr;
        };
        
        const dates = bins.map(b => formatDate(b.date));
        
        // Store raw dates and bins for click handling
        this.bins = bins;
        this.rawDates = bins.map(b => b.date);
        
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
                },
                formatter: (params) => {
                    if (!params || params.length === 0) return '';
                    const dataIndex = params[0].dataIndex;
                    const bin = bins[dataIndex];
                    
                    let tooltip = `<div style="margin-bottom: 0.5rem;"><strong>${dates[dataIndex]}</strong></div>`;
                    tooltip += `<div style="margin-bottom: 0.5rem;">Total: <strong>${bin.count}</strong> articles</div>`;
                    
                    // Show cluster breakdown
                    if (bin.by_cluster && Object.keys(bin.by_cluster).length > 0) {
                        tooltip += `<div style="font-size: 0.85em; margin-top: 0.5rem;">By cluster:</div>`;
                        Object.entries(bin.by_cluster)
                            .sort((a, b) => b[1] - a[1])
                            .forEach(([clusterId, count]) => {
                                const clusterName = clusterId === 'null' ? 'Unclustered' : `Cluster ${clusterId}`;
                                tooltip += `<div style="font-size: 0.85em; margin-left: 0.5rem;">${clusterName}: ${count}</div>`;
                            });
                    }
                    tooltip += `<div style="margin-top: 0.5rem; font-size: 0.8em; color: #64748b;">Click to filter articles</div>`;
                    return tooltip;
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
                }
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
                    restore: {},
                    brush: {
                        type: ['rect', 'clear'],
                        title: {
                            rect: 'Select date range',
                            clear: 'Clear selection'
                        }
                    }
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
        
        // Handle click events to filter articles
        this.chart.on('click', (params) => {
            if (!params || params.dataIndex === undefined) return;
            
            const binIndex = params.dataIndex;
            const bin = bins[binIndex];
            const rawDate = this.rawDates[binIndex];
            
            // Determine if cluster segment was clicked
            let clusterId = null;
            if (params.seriesName && params.seriesName !== 'Total' && params.seriesName !== 'Unclustered') {
                // Extract cluster ID from series name (e.g., "Cluster 5" -> 5)
                const match = params.seriesName.match(/Cluster (\d+)/);
                if (match) {
                    clusterId = parseInt(match[1]);
                }
            } else if (params.seriesName === 'Unclustered') {
                clusterId = 'null';
            }
            
            // Calculate date range for this bin
            // For month bins like "2025-10", create range from first to last day of month
            const dateRange = this.getDateRangeForBin(rawDate);
            
            // Store selection
            this.selectedBinIndex = binIndex;
            this.updateVisualSelection(binIndex);
            
            // Emit filter change event
            const filterEvent = new CustomEvent('timeline-filter', {
                detail: {
                    dateRange: dateRange,
                    clusterId: clusterId,
                    binIndex: binIndex,
                    count: bin.count
                }
            });
            document.dispatchEvent(filterEvent);
        });
        
        // Handle brush events for date range selection
        this.chart.on('brush', (params) => {
            if (params.areas && params.areas.length > 0) {
                const area = params.areas[0];
                const startIdx = Math.floor(area.coordRange[0]);
                const endIdx = Math.ceil(area.coordRange[1]);
                
                if (startIdx >= 0 && endIdx < bins.length && startIdx <= endIdx) {
                    const startDate = this.rawDates[startIdx];
                    const endDate = this.rawDates[endIdx];
                    
                    const dateRange = {
                        from: this.getDateRangeForBin(startDate).from,
                        to: this.getDateRangeForBin(endDate).to
                    };
                    
                    // Clear bin selection
                    this.selectedBinIndex = null;
                    this.clearVisualSelection();
                    
                    // Emit brush filter event
                    const brushEvent = new CustomEvent('timeline-brush', {
                        detail: {
                            dateRange: dateRange,
                            startIdx: startIdx,
                            endIdx: endIdx
                        }
                    });
                    document.dispatchEvent(brushEvent);
                }
            }
        });
    }
    
    /**
     * Get date range (from/to) for a date bin
     */
    getDateRangeForBin(dateStr) {
        if (!dateStr) return { from: '', to: '' };
        
        // Fix year if needed (e.g., "0225-10" -> "2025-10")
        let fixedDate = dateStr;
        if (dateStr.match(/^0\d{2}-\d{2}$/)) {
            fixedDate = '20' + dateStr.substring(1);
        }
        
        // Parse YYYY-MM format
        const parts = fixedDate.split('-');
        if (parts.length === 2) {
            const year = parseInt(parts[0]);
            const month = parseInt(parts[1]);
            
            // Calculate first and last day of month
            const from = `${year}-${String(month).padStart(2, '0')}-01`;
            const lastDay = new Date(year, month, 0).getDate(); // Get last day of month
            const to = `${year}-${String(month).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
            
            return { from, to };
        }
        
        return { from: fixedDate, to: fixedDate };
    }
    
    /**
     * Update visual selection indicator
     */
    updateVisualSelection(binIndex) {
        if (!this.chart || binIndex === null) return;
        
        // Highlight the selected bin using visualMap or markArea
        const option = this.chart.getOption();
        
        // Add markArea to highlight selected bin
        const markArea = {
            itemStyle: {
                color: 'rgba(37, 99, 235, 0.1)'
            },
            data: [[{
                xAxis: binIndex
            }, {
                xAxis: binIndex
            }]]
        };
        
        // Update series to include markArea
        option.series = option.series.map(series => ({
            ...series,
            markArea: markArea
        }));
        
        this.chart.setOption(option);
    }
    
    /**
     * Clear visual selection
     */
    clearVisualSelection() {
        if (!this.chart) return;
        this.selectedBinIndex = null;
        
        const option = this.chart.getOption();
        option.series = option.series.map(series => ({
            ...series,
            markArea: null
        }));
        this.chart.setOption(option);
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
