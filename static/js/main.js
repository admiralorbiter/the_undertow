/**
 * News Relationship Explorer - Main Application Entry Point
 */

import { api } from './api.js';
import { ListView } from './views/list.js';
import { GalaxyView } from './views/galaxy.js';
import { TimelineView } from './views/timeline.js';

// Application state
const appState = {
    currentView: 'list',
    filters: {
        q: '',
        from: '',
        to: '',
        outlet: ''
    },
    currentPage: 0,
    pageSize: 20,
    selectedArticle: null,
    totalArticles: 0
};

// Initialize views
let listView, galaxyView, timelineView;

/**
 * Initialize the application
 */
async function init() {
    console.log('Initializing News Relationship Explorer...');
    
    // Initialize views
    listView = new ListView(document.getElementById('list-view'));
    galaxyView = new GalaxyView(document.getElementById('galaxy-view'));
    timelineView = new TimelineView(document.getElementById('timeline-view'));
    
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
}

/**
 * Switch between views
 */
function switchView(viewName) {
    appState.currentView = viewName;
    
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
    }
}

// Handle article selection events from galaxy view
document.addEventListener('article-selected', (e) => {
    const articleId = e.detail.articleId;
    selectArticleById(articleId);
});

// Handle window resize for charts
window.addEventListener('resize', () => {
    if (appState.currentView === 'galaxy' && galaxyView) {
        galaxyView.resize();
    }
    if (appState.currentView === 'timeline' && timelineView) {
        timelineView.resize();
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
        outlet: document.getElementById('outlet-filter').value
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
        outlet: ''
    };
    
    loadArticles();
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
                <div class="similar-articles" style="margin-top: 2rem; padding-top: 2rem; border-top: 1px solid #e2e8f0;">
                    <h4 style="margin-bottom: 1rem;">Similar Articles</h4>
            `;
            
            similarData.items.forEach(item => {
                html += `
                    <div class="similar-item" style="margin-bottom: 1.5rem; padding: 1rem; background: #f8fafc; border-radius: 0.5rem;">
                        <h5 style="margin: 0 0 0.5rem 0; font-size: 1rem;">
                            <a href="#" onclick="window.selectArticleById(${item.id}); return false;" style="color: var(--primary-color); text-decoration: none;">
                                ${escapeHtml(item.title)}
                            </a>
                        </h5>
                        <div class="why-related" style="font-size: 0.875rem; color: #64748b;">
                `;
                
                // Show explain-why information
                if (item.cosine !== null && item.cosine !== undefined) {
                    html += `<div style="margin-bottom: 0.5rem;">
                        <strong>Similarity:</strong> ${(item.cosine * 100).toFixed(1)}%
                    </div>`;
                }
                
                if (item.why) {
                    if (item.why.shared_terms && item.why.shared_terms.length > 0) {
                        html += `<div style="margin-bottom: 0.5rem;">
                            <strong>Shared terms:</strong> ${escapeHtml(item.why.shared_terms.slice(0, 5).join(', '))}
                        </div>`;
                    }
                    
                    if (item.why.date_proximity_days !== null && item.why.date_proximity_days !== undefined) {
                        html += `<div style="margin-bottom: 0.5rem;">
                            <strong>Date proximity:</strong> ${item.why.date_proximity_days} day${item.why.date_proximity_days !== 1 ? 's' : ''}
                        </div>`;
                    }
                    
                    if (item.why.same_outlet) {
                        html += `<div style="margin-bottom: 0.5rem;">
                            <span style="background: #dbeafe; color: #1e40af; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem;">
                                Same outlet
                            </span>
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

// Expose functions for views and pagination
window.appState = appState;
window.selectArticle = selectArticle;
window.selectArticleById = selectArticleById;
window.goToPage = goToPage;

// Initialize on DOM load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

