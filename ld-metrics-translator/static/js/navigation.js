/**
 * Enhanced Navigation Features for L&D Metrics Translator
 * Includes keyboard shortcuts, quick navigation, and state management
 */

class NavigationManager {
    constructor() {
        this.init();
        this.setupKeyboardShortcuts();
        this.setupQuickNavigation();
        this.setupSocialSharing();
        this.setupPrintOptimization();
    }

    init() {
        // Initialize navigation state
        this.currentPage = window.location.pathname;
        this.isDetailPage = this.currentPage.includes('/metric/');
        
        // Setup lazy loading for related content
        this.setupLazyLoading();
        
        // Setup smooth scrolling
        this.setupSmoothScrolling();
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Only handle shortcuts when not typing in input fields
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            switch(e.key) {
                case 'h':
                case 'H':
                    // Go to home
                    if (!e.ctrlKey && !e.metaKey) {
                        window.location.href = '/';
                    }
                    break;
                
                case 'b':
                case 'B':
                    // Go back
                    if (!e.ctrlKey && !e.metaKey) {
                        this.goBack();
                    }
                    break;
                
                case 'ArrowLeft':
                    // Previous metric (on detail pages)
                    if (this.isDetailPage && e.altKey) {
                        this.navigateToPrevious();
                        e.preventDefault();
                    }
                    break;
                
                case 'ArrowRight':
                    // Next metric (on detail pages)
                    if (this.isDetailPage && e.altKey) {
                        this.navigateToNext();
                        e.preventDefault();
                    }
                    break;
                
                case 's':
                case 'S':
                    // Focus search (on list pages)
                    if (!this.isDetailPage && !e.ctrlKey && !e.metaKey) {
                        const searchInput = document.querySelector('#search-input');
                        if (searchInput) {
                            searchInput.focus();
                            e.preventDefault();
                        }
                    }
                    break;
                
                case 'p':
                case 'P':
                    // Print page
                    if (e.ctrlKey || e.metaKey) {
                        this.printPage();
                        e.preventDefault();
                    }
                    break;
                
                case '?':
                    // Show keyboard shortcuts help
                    this.showKeyboardHelp();
                    e.preventDefault();
                    break;
            }
        });
    }

    setupQuickNavigation() {
        // Create floating quick navigation menu
        if (this.isDetailPage) {
            this.createQuickNavMenu();
        }
        
        // Setup breadcrumb navigation
        this.enhanceBreadcrumbs();
    }

    createQuickNavMenu() {
        const quickNav = document.createElement('div');
        quickNav.className = 'quick-nav-menu';
        quickNav.innerHTML = `
            <div class="quick-nav-toggle" title="Quick Navigation (⇄)">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M6.99 11L3 15l3.99 4v-3H14v-2H6.99v-3zM21 9l-3.99-4v3H10v2h7.01v3L21 9z"/>
                </svg>
            </div>
            <div class="quick-nav-content">
                <div class="quick-nav-section">
                    <h4>Navigation</h4>
                    <button onclick="navigationManager.goBack()" class="quick-nav-item">
                        <span class="shortcut">B</span> Back to Results
                    </button>
                    <button onclick="window.location.href='/'" class="quick-nav-item">
                        <span class="shortcut">H</span> Home
                    </button>
                </div>
                <div class="quick-nav-section">
                    <h4>Actions</h4>
                    <button onclick="navigationManager.shareMetric()" class="quick-nav-item">
                        Share Metric
                    </button>
                    <button onclick="navigationManager.printPage()" class="quick-nav-item">
                        <span class="shortcut">Ctrl+P</span> Print
                    </button>
                </div>
                <div class="quick-nav-section">
                    <h4>Help</h4>
                    <button onclick="navigationManager.showKeyboardHelp()" class="quick-nav-item">
                        <span class="shortcut">?</span> Keyboard Shortcuts
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(quickNav);
        
        // Toggle menu visibility
        const toggle = quickNav.querySelector('.quick-nav-toggle');
        const content = quickNav.querySelector('.quick-nav-content');
        
        toggle.addEventListener('click', () => {
            content.classList.toggle('show');
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!quickNav.contains(e.target)) {
                content.classList.remove('show');
            }
        });
    }

    enhanceBreadcrumbs() {
        const breadcrumbs = document.querySelector('.breadcrumb-nav');
        if (breadcrumbs) {
            // Add hover effects and smooth transitions
            breadcrumbs.classList.add('enhanced-breadcrumbs');
        }
    }

    setupSocialSharing() {
        // Add social sharing functionality
        const shareButtons = document.querySelectorAll('.share-button');
        shareButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.shareMetric();
            });
        });
    }

    setupPrintOptimization() {
        // Add print-specific styles and optimizations
        const printButton = document.querySelector('.print-button');
        if (printButton) {
            printButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.printPage();
            });
        }
    }

    setupLazyLoading() {
        // Lazy load related metrics and additional content
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const element = entry.target;
                    if (element.dataset.lazyLoad) {
                        this.loadContent(element);
                        observer.unobserve(element);
                    }
                }
            });
        }, {
            rootMargin: '50px'
        });

        document.querySelectorAll('[data-lazy-load]').forEach(el => {
            observer.observe(el);
        });
    }

    setupSmoothScrolling() {
        // Smooth scroll for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    goBack() {
        // Smart back navigation
        if (document.referrer && document.referrer.includes(window.location.origin)) {
            window.history.back();
        } else {
            // Fallback to home page
            window.location.href = '/';
        }
    }

    navigateToPrevious() {
        const prevButton = document.querySelector('.nav-previous');
        if (prevButton && !prevButton.disabled) {
            window.location.href = prevButton.href;
        }
    }

    navigateToNext() {
        const nextButton = document.querySelector('.nav-next');
        if (nextButton && !nextButton.disabled) {
            window.location.href = nextButton.href;
        }
    }

    shareMetric() {
        const title = document.querySelector('h1')?.textContent || 'L&D Metric';
        const url = window.location.href;
        const text = `Check out this L&D metric: ${title}`;

        if (navigator.share) {
            // Use native sharing API if available
            navigator.share({
                title: title,
                text: text,
                url: url
            }).catch(err => console.log('Error sharing:', err));
        } else {
            // Fallback: copy to clipboard
            navigator.clipboard.writeText(url).then(() => {
                this.showNotification('Link copied to clipboard!');
            }).catch(() => {
                // Final fallback: show share modal
                this.showShareModal(title, url, text);
            });
        }
    }

    printPage() {
        // Add print-specific class for styling
        document.body.classList.add('printing');
        
        // Print the page
        window.print();
        
        // Remove print class after printing
        setTimeout(() => {
            document.body.classList.remove('printing');
        }, 1000);
    }

    showKeyboardHelp() {
        const helpModal = document.createElement('div');
        helpModal.className = 'keyboard-help-modal';
        helpModal.innerHTML = `
            <div class="modal-overlay">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Keyboard Shortcuts</h3>
                        <button class="modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="shortcut-grid">
                            <div class="shortcut-item">
                                <kbd>H</kbd>
                                <span>Go to Home</span>
                            </div>
                            <div class="shortcut-item">
                                <kbd>B</kbd>
                                <span>Go Back</span>
                            </div>
                            <div class="shortcut-item">
                                <kbd>S</kbd>
                                <span>Focus Search</span>
                            </div>
                            <div class="shortcut-item">
                                <kbd>Alt</kbd> + <kbd>←</kbd>
                                <span>Previous Metric</span>
                            </div>
                            <div class="shortcut-item">
                                <kbd>Alt</kbd> + <kbd>→</kbd>
                                <span>Next Metric</span>
                            </div>
                            <div class="shortcut-item">
                                <kbd>Ctrl</kbd> + <kbd>P</kbd>
                                <span>Print Page</span>
                            </div>
                            <div class="shortcut-item">
                                <kbd>?</kbd>
                                <span>Show this help</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(helpModal);
        
        // Close modal handlers
        const closeBtn = helpModal.querySelector('.modal-close');
        const overlay = helpModal.querySelector('.modal-overlay');
        
        const closeModal = () => {
            helpModal.remove();
        };
        
        closeBtn.addEventListener('click', closeModal);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeModal();
        });
        
        // Close with Escape key
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
    }

    showShareModal(title, url, text) {
        const shareModal = document.createElement('div');
        shareModal.className = 'share-modal';
        shareModal.innerHTML = `
            <div class="modal-overlay">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Share Metric</h3>
                        <button class="modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="share-options">
                            <button onclick="window.open('https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}', '_blank')" class="share-option twitter">
                                <svg viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M22.46,6C21.69,6.35 20.86,6.58 20,6.69C20.88,6.16 21.56,5.32 21.88,4.31C21.05,4.81 20.13,5.16 19.16,5.36C18.37,4.5 17.26,4 16,4C13.65,4 11.73,5.92 11.73,8.29C11.73,8.63 11.77,8.96 11.84,9.27C8.28,9.09 5.11,7.38 3,4.79C2.63,5.42 2.42,6.16 2.42,6.94C2.42,8.43 3.17,9.75 4.33,10.5C3.62,10.5 2.96,10.3 2.38,10C2.38,10 2.38,10 2.38,10.03C2.38,12.11 3.86,13.85 5.82,14.24C5.46,14.34 5.08,14.39 4.69,14.39C4.42,14.39 4.15,14.36 3.89,14.31C4.43,16 6,17.26 7.89,17.29C6.43,18.45 4.58,19.13 2.56,19.13C2.22,19.13 1.88,19.11 1.54,19.07C3.44,20.29 5.7,21 8.12,21C16,21 20.33,14.46 20.33,8.79C20.33,8.6 20.33,8.42 20.32,8.23C21.16,7.63 21.88,6.87 22.46,6Z"/>
                                </svg>
                                Twitter
                            </button>
                            <button onclick="window.open('https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}', '_blank')" class="share-option linkedin">
                                <svg viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M19 3A2 2 0 0 1 21 5V19A2 2 0 0 1 19 21H5A2 2 0 0 1 3 19V5A2 2 0 0 1 5 3H19M18.5 18.5V13.2A3.26 3.26 0 0 0 15.24 9.94C14.39 9.94 13.4 10.46 12.92 11.24V10.13H10.13V18.5H12.92V13.57C12.92 12.8 13.54 12.17 14.31 12.17A1.4 1.4 0 0 1 15.71 13.57V18.5H18.5M6.88 8.56A1.68 1.68 0 0 0 8.56 6.88C8.56 5.95 7.81 5.19 6.88 5.19S5.19 5.95 5.19 6.88A1.69 1.69 0 0 0 6.88 8.56M8.27 18.5V10.13H5.5V18.5H8.27Z"/>
                                </svg>
                                LinkedIn
                            </button>
                        </div>
                        <div class="share-url">
                            <label>Share URL:</label>
                            <div class="url-input-group">
                                <input type="text" value="${url}" readonly class="share-url-input">
                                <button onclick="navigator.clipboard.writeText('${url}').then(() => this.textContent = 'Copied!')" class="copy-btn">Copy</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(shareModal);
        
        // Close modal handlers
        const closeBtn = shareModal.querySelector('.modal-close');
        const overlay = shareModal.querySelector('.modal-overlay');
        
        const closeModal = () => {
            shareModal.remove();
        };
        
        closeBtn.addEventListener('click', closeModal);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeModal();
        });
    }

    showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => notification.classList.add('show'), 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    loadContent(element) {
        // Simulate loading additional content
        const loadingSpinner = element.querySelector('.loading-spinner');
        if (loadingSpinner) {
            loadingSpinner.style.display = 'block';
        }
        
        // In a real implementation, this would make an AJAX request
        setTimeout(() => {
            element.classList.add('loaded');
            if (loadingSpinner) {
                loadingSpinner.style.display = 'none';
            }
        }, 500);
    }
}

// Initialize navigation manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.navigationManager = new NavigationManager();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NavigationManager;
}
