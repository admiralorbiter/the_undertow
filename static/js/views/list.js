/**
 * List View - Display articles in a list format
 */

export class ListView {
    constructor(container) {
        this.container = container;
        this.articles = [];
    }
    
    /**
     * Render articles list
     */
    render(articles) {
        this.articles = articles;
        
        const listEl = this.container.querySelector('#articles-list') || 
                      document.getElementById('articles-list');
        
        if (!listEl) return;
        
        if (articles.length === 0) {
            listEl.innerHTML = '<p style="text-align: center; color: #64748b; padding: 2rem;">No articles found.</p>';
            return;
        }
        
        listEl.innerHTML = articles.map((article, idx) => `
            <div class="article-card" data-id="${article.id}" data-index="${idx}">
                <div class="article-title">${this.escapeHtml(article.title)}</div>
                <div class="article-meta">
                    ${this.escapeHtml(article.outlet || 'Unknown')} • ${this.formatDate(article.date)}
                </div>
                <div class="article-summary">
                    ${this.escapeHtml(article.summary || 'No summary available.')}
                </div>
            </div>
        `).join('');
        
        // Attach click handlers
        listEl.querySelectorAll('.article-card').forEach(card => {
            const idx = parseInt(card.dataset.index);
            card.addEventListener('click', () => {
                if (window.selectArticle) {
                    window.selectArticle(articles[idx]);
                }
            });
        });
    }
    
    /**
     * Escape HTML
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Format date
     */
    formatDate(dateStr) {
        if (!dateStr) return 'Unknown';
        try {
            const date = new Date(dateStr + 'T00:00:00');
            return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
        } catch {
            return dateStr;
        }
    }
}

