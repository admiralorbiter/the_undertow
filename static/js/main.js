/**
 * News Relationship Explorer - Main Application Entry Point
 */

import { api } from './api.js';
import { ListView } from './views/list.js';
import { GalaxyView } from './views/galaxy.js';
import { TimelineView } from './views/timeline.js';
import { DashboardView } from './views/dashboard.js';
import { AlertsView } from './views/alerts.js';

// Application state
const appState = {
    currentView: 'list',
    filters: {
        q: '',
        from: '',
        to: '',
        outlet: '',
        cluster_id: null
    },
    currentPage: 0,
    pageSize: 20,
    selectedArticle: null,
    totalArticles: 0,
    timelineSelection: {
        dateBin: null,
        clusterId: null
    }
};

// Initialize views
let listView, galaxyView, timelineView, dashboardView, alertsView;

/**
 * Initialize the application
 */
async function init() {
    console.log('Initializing News Relationship Explorer...');
    
    // Initialize views
    listView = new ListView(document.getElementById('list-view'));
    galaxyView = new GalaxyView(document.getElementById('galaxy-view'));
    timelineView = new TimelineView(document.getElementById('timeline-view'));
    dashboardView = new DashboardView(document.getElementById('dashboard-view'));
    alertsView = new AlertsView(document.getElementById('alerts-view'));
    
    // Make alertsView globally accessible for acknowledge function
    window.alertsView = alertsView;
    
    // Setup event listeners
    setupEventListeners();
    
    // Load initial data
    try {
        await loadArticles();
        console.log('Application initialized successfully');
    } catch (error) {
        console.error('Failed to load initial articles:', error);
        const listEl = document.getElementById('articles-list');
        if (listEl) {
            listEl.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: #ef4444;">
                    <p><strong>Error loading articles</strong></p>
                    <p style="font-size: 0.9rem; margin-top: 0.5rem;">
                        Make sure the backend is running and the database is initialized.
                    </p>
                </div>
            `;
        }
    }
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // View tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            switchView(e.target.dataset.view);
        });
    });
    
    // Filter inputs
    document.getElementById('search-query').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            applyFilters();
        }
    });
    
    document.getElementById('apply-filters').addEventListener('click', applyFilters);
    document.getElementById('clear-filters').addEventListener('click', clearFilters);
    
    // Load outlets for filter dropdown
    loadOutlets();
    
    // Listen for timeline filter events
    document.addEventListener('timeline-filter', handleTimelineFilter);
    document.addEventListener('timeline-brush', handleTimelineBrush);
    
    // Listen for storyline selection from dashboard
    document.addEventListener('storyline-selected', handleStorylineSelection);
    
    // Listen for entity selection from dashboard
    document.addEventListener('entity-selected', handleEntitySelection);
}

/**
 * Switch between views
 */
function switchView(viewName) {
    appState.currentView = viewName;
    
    // Toggle layout class for dashboard
    const mainLayout = document.querySelector('.main-layout');
    mainLayout.classList.toggle('dashboard-active', viewName === 'dashboard' || viewName === 'alerts');
    
    // Update tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.view === viewName);
    });
    
    // Update view containers
    document.querySelectorAll('.view').forEach(view => {
        view.classList.toggle('active', view.id === `${viewName}-view`);
    });
    
    // Load view-specific data
    if (viewName === 'list') {
        loadArticles();
    } else if (viewName === 'galaxy') {
        galaxyView.load();
        // Resize chart after a brief delay to ensure container is visible
        setTimeout(() => galaxyView.resize(), 100);
    } else if (viewName === 'timeline') {
        timelineView.load();
        // Resize chart after a brief delay to ensure container is visible
        setTimeout(() => timelineView.resize(), 100);
    } else if (viewName === 'dashboard') {
        dashboardView.load(30);  // Default 30 days
        setTimeout(() => dashboardView.resize(), 100);
    } else if (viewName === 'alerts') {
        alertsView.load();
    }
}

// Handle article selection events from galaxy view
document.addEventListener('article-selected', (e) => {
    const articleId = e.detail.articleId;
    selectArticleById(articleId);
});

// Handle window resize for charts
window.addEventListener('resize', () => {
    // Resize charts when window resizes
    if (galaxyView && galaxyView.chart) {
        galaxyView.resize();
    }
    if (timelineView && timelineView.chart) {
        timelineView.resize();
    }
    if (dashboardView && dashboardView.charts) {
        dashboardView.resize();
    }
});

/**
 * Apply filters and reload articles
 */
async function applyFilters() {
    appState.filters = {
        q: document.getElementById('search-query').value.trim(),
        from: document.getElementById('date-from').value,
        to: document.getElementById('date-to').value,
        outlet: document.getElementById('outlet-filter').value,
        cluster_id: appState.filters.cluster_id // Preserve cluster_id from timeline
    };
    
    appState.currentPage = 0;
    await loadArticles();
}

/**
 * Clear all filters
 */
function clearFilters() {
    document.getElementById('search-query').value = '';
    document.getElementById('date-from').value = '';
    document.getElementById('date-to').value = '';
    document.getElementById('outlet-filter').value = '';
    
    appState.filters = {
        q: '',
        from: '',
        to: '',
        outlet: '',
        cluster_id: null
    };
    
    appState.timelineSelection = {
        dateBin: null,
        clusterId: null
    };
    
    // Clear timeline visual selection
    if (timelineView && timelineView.clearVisualSelection) {
        timelineView.clearVisualSelection();
    }
    
    loadArticles();
}

/**
 * Handle timeline filter event (click on bin)
 */
function handleTimelineFilter(event) {
    const { dateRange, clusterId, count } = event.detail;
    
    // Update appState filters
    appState.filters.from = dateRange.from;
    appState.filters.to = dateRange.to;
    appState.filters.cluster_id = clusterId === 'null' ? null : clusterId;
    
    // Update timeline selection
    appState.timelineSelection = {
        dateBin: event.detail.binIndex,
        clusterId: clusterId
    };
    
    // Update filter panel UI
    updateFilterPanelUI();
    
    // Switch to list view and load articles
    switchView('list');
    appState.currentPage = 0;
    loadArticles();
}

/**
 * Handle timeline brush event (drag to select range)
 */
function handleTimelineBrush(event) {
    const { dateRange } = event.detail;
    
    // Update appState filters
    appState.filters.from = dateRange.from;
    appState.filters.to = dateRange.to;
    // Don't set cluster_id for brush (selects all clusters in range)
    appState.filters.cluster_id = null;
    
    // Clear timeline bin selection
    appState.timelineSelection = {
        dateBin: null,
        clusterId: null
    };
    
    // Update filter panel UI
    updateFilterPanelUI();
    
    // Switch to list view and load articles
    switchView('list');
    appState.currentPage = 0;
    loadArticles();
}

/**
 * Update filter panel UI to reflect current filters
 */
function updateFilterPanelUI() {
    const fromInput = document.getElementById('date-from');
    const toInput = document.getElementById('date-to');
    
    if (fromInput && appState.filters.from) {
        // Convert YYYY-MM-DD to MM/DD/YYYY for date input
        const fromDate = appState.filters.from;
        if (fromDate.match(/^\d{4}-\d{2}-\d{2}$/)) {
            const parts = fromDate.split('-');
            fromInput.value = `${parts[1]}/${parts[2]}/${parts[0]}`;
        } else {
            fromInput.value = appState.filters.from;
        }
    }
    
    if (toInput && appState.filters.to) {
        const toDate = appState.filters.to;
        if (toDate.match(/^\d{4}-\d{2}-\d{2}$/)) {
            const parts = toDate.split('-');
            toInput.value = `${parts[1]}/${parts[2]}/${parts[0]}`;
        } else {
            toInput.value = appState.filters.to;
        }
    }
}

/**
 * Load articles from API
 */
async function loadArticles() {
    const listEl = document.getElementById('articles-list');
    
    // Show loading state
    if (listEl) {
        listEl.innerHTML = '<p style="text-align: center; color: #64748b; padding: 2rem;">Loading articles...</p>';
    }
    
    try {
        const params = {
            ...appState.filters,
            limit: appState.pageSize,
            offset: appState.currentPage * appState.pageSize
        };
        
        const response = await api.getArticles(params);
        
        appState.totalArticles = response.total;
        updateResultsCount();
        updatePagination();
        
        listView.render(response.items);
        
    } catch (error) {
        console.error('Error loading articles:', error);
        if (listEl) {
            listEl.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: #ef4444;">
                    <p><strong>Error loading articles</strong></p>
                    <p style="font-size: 0.9rem; margin-top: 0.5rem;">${error.message || 'Please try again.'}</p>
                </div>
            `;
        }
    }
}

/**
 * Load available outlets for filter dropdown
 */
async function loadOutlets() {
    try {
        // For now, we'll load outlets from articles
        // In future, could have a dedicated endpoint
        const response = await api.getArticles({ limit: 1000 });
        const outlets = [...new Set(response.items.map(a => a.outlet).filter(Boolean))].sort();
        
        const select = document.getElementById('outlet-filter');
        outlets.forEach(outlet => {
            const option = document.createElement('option');
            option.value = outlet;
            option.textContent = outlet;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading outlets:', error);
    }
}

/**
 * Update results count display
 */
function updateResultsCount() {
    const countEl = document.getElementById('results-count');
    if (countEl) {
        countEl.textContent = `${appState.totalArticles} article${appState.totalArticles !== 1 ? 's' : ''}`;
    }
}

/**
 * Update pagination controls
 */
function updatePagination() {
    const paginationEl = document.getElementById('pagination');
    if (!paginationEl) return;
    
    const totalPages = Math.ceil(appState.totalArticles / appState.pageSize);
    const currentPage = appState.currentPage + 1;
    
    if (totalPages <= 1) {
        paginationEl.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    html += `<button class="pagination-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="window.goToPage(${currentPage - 2})">Previous</button>`;
    
    // Page numbers (show current and a few around it)
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    if (startPage > 1) {
        html += `<button class="pagination-btn" onclick="window.goToPage(0)">1</button>`;
        if (startPage > 2) html += `<span style="padding: 0.5rem;">...</span>`;
    }
    
    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="pagination-btn" ${i === currentPage ? 'style="background: var(--primary-color); color: white;"' : ''} onclick="window.goToPage(${i - 1})">${i}</button>`;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) html += `<span style="padding: 0.5rem;">...</span>`;
        html += `<button class="pagination-btn" onclick="window.goToPage(${totalPages - 1})">${totalPages}</button>`;
    }
    
    // Next button
    html += `<button class="pagination-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="window.goToPage(${currentPage})">Next</button>`;
    
    paginationEl.innerHTML = html;
}

/**
 * Go to a specific page
 */
function goToPage(page) {
    appState.currentPage = Math.max(0, Math.min(page, Math.ceil(appState.totalArticles / appState.pageSize) - 1));
    loadArticles();
}

/**
 * Select an article and show details
 */
function selectArticle(article) {
    appState.selectedArticle = article;
    showArticleDetails(article);
    
    // Update UI
    document.querySelectorAll('.article-card').forEach(card => {
        card.classList.toggle('selected', card.dataset.id === String(article.id));
    });
}

/**
 * Show article details in right panel
 */
async function showArticleDetails(article) {
    const detailsEl = document.getElementById('article-details');
    
    // Show basic article info immediately
    let html = `
        <div class="article-detail active">
            <h3>${escapeHtml(article.title)}</h3>
            <div class="meta">
                <strong>Outlet:</strong> ${escapeHtml(article.outlet || 'Unknown')}<br>
                <strong>Date:</strong> ${formatDate(article.date)}<br>
            </div>
            <div class="summary">${escapeHtml(article.summary || 'No summary available.')}</div>
            <a href="${escapeHtml(article.url)}" target="_blank" class="url">Read full article →</a>
    `;
    
    // Load similar articles
    try {
        const similarData = await api.getSimilar(article.id, 5);
        
        if (similarData.items && similarData.items.length > 0) {
            html += `
                <div class="similar-articles">
                    <h4>Similar Articles</h4>
            `;
            
            similarData.items.forEach(item => {
                const similarity = item.cosine !== null && item.cosine !== undefined 
                    ? item.cosine : 0;
                const similarityPercent = (similarity * 100).toFixed(1);
                
                // Determine similarity badge color
                let badgeClass = 'similarity-badge-low';
                if (similarity >= 0.8) badgeClass = 'similarity-badge-high';
                else if (similarity >= 0.6) badgeClass = 'similarity-badge-medium';
                
                html += `
                    <div class="similar-item">
                        <div class="similar-item-header">
                            <h5>
                                <a href="#" onclick="window.selectArticleById(${item.id}); return false;" class="similar-item-link">
                                    ${escapeHtml(item.title)}
                                </a>
                            </h5>
                            <span class="similarity-badge ${badgeClass}" title="Cosine similarity">
                                ${similarityPercent}%
                            </span>
                        </div>
                        <div class="why-related">
                `;
                
                // Show explain-why information
                if (item.why) {
                    if (item.why.shared_terms && item.why.shared_terms.length > 0) {
                        const terms = item.why.shared_terms.slice(0, 8);
                        html += `<div class="why-section">
                            <span class="why-label">Shared terms:</span>
                            <div class="shared-terms">
                                ${terms.map(term => `<span class="term-chip">${escapeHtml(term)}</span>`).join('')}
                            </div>
                        </div>`;
                    }
                    
                    if (item.why.date_proximity_days !== null && item.why.date_proximity_days !== undefined) {
                        html += `<div class="why-section">
                            <span class="why-icon">📅</span>
                            <span class="why-text">${item.why.date_proximity_days} day${item.why.date_proximity_days !== 1 ? 's' : ''} apart</span>
                        </div>`;
                    }
                    
                    if (item.why.same_outlet) {
                        html += `<div class="why-section">
                            <span class="why-icon">📰</span>
                            <span class="why-badge">Same outlet</span>
                        </div>`;
                    }
                }
                
                html += `
                        </div>
                    </div>
                `;
            });
            
            html += `</div>`;
        }
    } catch (error) {
        console.error('Error loading similar articles:', error);
        // Don't show error to user, just skip similar articles section
    }
    
    html += `</div>`;
    detailsEl.innerHTML = html;
}

/**
 * Select article by ID (for similar articles links)
 */
async function selectArticleById(articleId) {
    try {
        const response = await api.getArticles({ limit: 1000 });
        const article = response.items.find(a => a.id === articleId);
        if (article) {
            selectArticle(article);
        } else {
            // If not in current page, fetch directly
            // For now, just log
            console.log('Article not found in current page:', articleId);
        }
    } catch (error) {
        console.error('Error selecting article:', error);
    }
}

/**
 * Utility: Escape HTML
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Utility: Format date
 */
function formatDate(dateStr) {
    if (!dateStr) return 'Unknown';
    try {
        const date = new Date(dateStr + 'T00:00:00');
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    } catch {
        return dateStr;
    }
}

/**
 * Handle storyline selection from dashboard
 */
async function handleStorylineSelection(event) {
    const { storylineId, storyline, articles } = event.detail;
    
    console.log(`Filtering by storyline: ${storyline.label}`);
    
    // Switch to list view
    switchView('list');
    
    // Clear other filters
    appState.filters = {
        q: '',
        from: '',
        to: '',
        outlet: '',
        cluster_id: null,
        storyline_id: storylineId
    };
    
    // Update filter panel to show storyline filter
    const searchQuery = document.getElementById('search-query');
    if (searchQuery) {
        searchQuery.value = `Storyline: ${storyline.label}`;
        searchQuery.disabled = true;
    }
    
    // Fetch and display articles from this storyline
    try {
        const articleIds = articles.map(a => a.id);
        const response = await api.getArticles({ limit: 1000 });
        const filteredArticles = response.items.filter(a => articleIds.includes(a.id));
        
        appState.totalArticles = filteredArticles.length;
        updateResultsCount();
        listView.render(filteredArticles);
        
        // Show info message
        const listEl = document.getElementById('articles-list');
        if (listEl && filteredArticles.length > 0) {
            listEl.insertAdjacentHTML('afterbegin', `
                <div class="filter-info" style="background: #eff6ff; border-left: 4px solid #2563eb; padding: 1rem; margin-bottom: 1rem;">
                    <strong>Filtered by storyline:</strong> ${escapeHtml(storyline.label)} (${filteredArticles.length} articles)
                    <button onclick="window.clearStorylineFilter()" style="float: right; padding: 0.25rem 0.75rem; background: #2563eb; color: white; border: none; border-radius: 4px; cursor: pointer;">Clear Filter</button>
                </div>
            `);
        }
    } catch (error) {
        console.error('Error loading storyline articles:', error);
    }
}

/**
 * Handle entity selection from dashboard
 */
async function handleEntitySelection(event) {
    const { entityId } = event.detail;
    
    console.log(`Filtering by entity: ${entityId}`);
    
    // Switch to list view
    switchView('list');
    
    try {
        // Fetch entity timeline (articles mentioning this entity)
        const response = await fetch(`/api/entities/${entityId}/timeline`);
        if (!response.ok) throw new Error('Failed to load entity');
        
        const data = await response.json();
        
        // Clear other filters
        appState.filters = {
            q: '',
            from: '',
            to: '',
            outlet: '',
            cluster_id: null,
            entity_id: entityId
        };
        
        // Update filter panel
        const searchQuery = document.getElementById('search-query');
        if (searchQuery) {
            searchQuery.value = `Entity: ${data.entity.name}`;
            searchQuery.disabled = true;
        }
        
        // Fetch full article details
        const articleIds = data.articles.map(a => a.id);
        const articlesResponse = await api.getArticles({ limit: 1000 });
        const filteredArticles = articlesResponse.items.filter(a => articleIds.includes(a.id));
        
        appState.totalArticles = filteredArticles.length;
        updateResultsCount();
        listView.render(filteredArticles);
        
        // Show info message
        const listEl = document.getElementById('articles-list');
        if (listEl && filteredArticles.length > 0) {
            listEl.insertAdjacentHTML('afterbegin', `
                <div class="filter-info" style="background: #f0fdf4; border-left: 4px solid #10b981; padding: 1rem; margin-bottom: 1rem;">
                    <strong>Filtered by entity:</strong> ${escapeHtml(data.entity.name)} (${data.entity.type}) - ${filteredArticles.length} articles
                    <button onclick="window.clearEntityFilter()" style="float: right; padding: 0.25rem 0.75rem; background: #10b981; color: white; border: none; border-radius: 4px; cursor: pointer;">Clear Filter</button>
                </div>
            `);
        }
    } catch (error) {
        console.error('Error loading entity articles:', error);
    }
}

/**
 * Clear storyline filter
 */
function clearStorylineFilter() {
    const searchQuery = document.getElementById('search-query');
    if (searchQuery) {
        searchQuery.value = '';
        searchQuery.disabled = false;
    }
    clearFilters();
}

/**
 * Clear entity filter
 */
function clearEntityFilter() {
    const searchQuery = document.getElementById('search-query');
    if (searchQuery) {
        searchQuery.value = '';
        searchQuery.disabled = false;
    }
    clearFilters();
}

// Expose functions for views and pagination
window.appState = appState;
window.selectArticle = selectArticle;
window.selectArticleById = selectArticleById;
window.goToPage = goToPage;
window.clearStorylineFilter = clearStorylineFilter;
window.clearEntityFilter = clearEntityFilter;

// Initialize on DOM load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

