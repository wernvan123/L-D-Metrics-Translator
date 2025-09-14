/**
 * Smart AI Recommendations Module
 * Handles display and interaction with AI-generated recommendations for L&D concepts
 */

// Immediate test to verify script loading
console.log('🔥 SMART RECOMMENDATIONS SCRIPT LOADED!');
window.smartRecommendationsLoaded = true;

class SmartRecommendations {
    constructor() {
        this.selectedMetrics = new Set();
        this.recommendations = [];
        this.isLoading = false;
        
        this.init();
    }
    
    init() {
        console.log('🚀 Smart Recommendations module starting initialization...');
        this.bindEvents();
        this.updateSelectionCounter();
        console.log('✅ Smart Recommendations module initialized successfully');
    }
    
    updateSelectionCounter() {
        const counterElement = document.getElementById('selected-metrics-count');
        const submitButton = document.getElementById('get-recommendations-btn');
        
        if (counterElement) {
            counterElement.textContent = this.selectedMetrics.size;
        }
        
        if (submitButton) {
            submitButton.disabled = this.selectedMetrics.size === 0;
            if (this.selectedMetrics.size > 0) {
                submitButton.classList.remove('disabled');
            } else {
                submitButton.classList.add('disabled');
            }
        }
    }
    
    bindEvents() {
        // Wait for metric cards to be loaded before binding events
        this.waitForMetricCards().then(() => {
            this.bindMetricCardEvents();
            this.bindSubmitButton();
        });
    }
    
    async waitForMetricCards() {
        return new Promise((resolve) => {
            const checkForCards = () => {
                const metricCards = document.querySelectorAll('.metric-card[data-id]');
                console.log(`Smart Recommendations: Found ${metricCards.length} metric cards`);
                
                if (metricCards.length > 0) {
                    resolve(metricCards);
                } else {
                    console.log('Smart Recommendations: Waiting for metric cards to load...');
                    setTimeout(checkForCards, 500);
                }
            };
            
            checkForCards();
        });
    }
    
    bindMetricCardEvents() {
        const metricCards = document.querySelectorAll('.metric-card[data-id]');
        console.log(`Smart Recommendations: Binding events to ${metricCards.length} metric cards`);
        
        metricCards.forEach(card => {
            // Add click event listener with capture to ensure it fires first
            card.addEventListener('click', this.handleMetricCardClick.bind(this), true);
            console.log(`Smart Recommendations: Bound click event to metric card ${card.dataset.id}`);
        });
    }
    
    bindSubmitButton() {
        const submitButton = document.getElementById('get-recommendations-btn');
        if (submitButton) {
            submitButton.addEventListener('click', () => {
                if (this.selectedMetrics.size > 0 && !this.isLoading) {
                    this.fetchRecommendations();
                }
            });
        }
    }
    
    handleMetricCardClick(event) {
        const metricCard = event.target.closest('.metric-card');
        if (metricCard) {
            this.toggleMetricSelection(metricCard);
        }
    }
    
    toggleMetricSelection(metricCard) {
        const metricId = metricCard.dataset.id;
        if (!metricId) {
            console.warn('Metric card missing data-id:', metricCard);
            return;
        }
        
        console.log(`Toggling selection for metric ${metricId}`);
        
        if (this.selectedMetrics.has(metricId)) {
            this.selectedMetrics.delete(metricId);
            metricCard.classList.remove('selected');
            this.removeTickMark(metricCard);
            console.log(`Deselected metric ${metricId}`);
        } else {
            this.selectedMetrics.add(metricId);
            metricCard.classList.add('selected');
            this.addTickMark(metricCard);
            console.log(`Selected metric ${metricId}`);
        }
        
        console.log('Currently selected metrics:', Array.from(this.selectedMetrics));
        
        // Update selection counter and button state
        this.updateSelectionCounter();
    }
    
    addTickMark(metricCard) {
        // Remove existing indicator
        metricCard.querySelector('.selection-indicator')?.remove();
        
        // Add tick mark indicator
        const indicator = document.createElement('div');
        indicator.className = 'selection-indicator';
        indicator.innerHTML = '<i class="fas fa-check-circle"></i>';
        
        metricCard.appendChild(indicator);
    }
    
    removeTickMark(metricCard) {
        metricCard.querySelector('.selection-indicator')?.remove();
    }
    
    async fetchRecommendations() {
        if (this.isLoading || this.selectedMetrics.size === 0) {
            return;
        }
        
        this.isLoading = true;
        this.showLoading();
        this.showRecommendationsContainer();
        
        try {
            const selectedMetricIds = Array.from(this.selectedMetrics);
            console.log('Fetching recommendations for metrics:', selectedMetricIds);
            
            const response = await fetch('/api/smart-recommendations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    selected_metrics: selectedMetricIds,
                    context: 'user_selection'
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Received recommendations:', data);
            
            if (data.success && data.recommendations) {
                this.recommendations = data.recommendations;
                this.displayRecommendations();
            } else {
                throw new Error(data.error || 'Failed to get recommendations');
            }
            
        } catch (error) {
            console.error('Error fetching recommendations:', error);
            this.showError('Failed to generate recommendations. Please try again.');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }
    
    showRecommendationsContainer() {
        const container = document.getElementById('smart-recommendations-container');
        if (container) {
            container.style.display = 'block';
        }
    }
    
    showLoading() {
        const loadingElement = document.getElementById('recommendations-loading');
        const contentElement = document.getElementById('recommendations-content');
        const errorElement = document.getElementById('recommendations-error');
        
        if (loadingElement) loadingElement.style.display = 'block';
        if (contentElement) contentElement.style.display = 'none';
        if (errorElement) errorElement.style.display = 'none';
    }
    
    hideLoading() {
        const loadingElement = document.getElementById('recommendations-loading');
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
    }
    
    showError(message) {
        const errorElement = document.getElementById('recommendations-error');
        const contentElement = document.getElementById('recommendations-content');
        
        if (errorElement) {
            errorElement.style.display = 'block';
            const errorText = errorElement.querySelector('p');
            if (errorText) {
                errorText.textContent = message;
            }
        }
        
        if (contentElement) {
            contentElement.style.display = 'none';
        }
    }
    
    displayRecommendations() {
        const contentElement = document.getElementById('recommendations-content');
        const errorElement = document.getElementById('recommendations-error');
        
        if (!contentElement) {
            console.error('Recommendations content element not found');
            return;
        }
        
        // Hide error state
        if (errorElement) {
            errorElement.style.display = 'none';
        }
        
        // Clear existing content
        contentElement.innerHTML = '';
        
        if (this.recommendations.length === 0) {
            contentElement.innerHTML = `
                <div class="no-recommendations">
                    <i class="fas fa-lightbulb"></i>
                    <p>No additional recommendations found for your current selection.</p>
                </div>
            `;
        } else {
            // Create recommendations HTML
            const recommendationsHTML = this.recommendations.map(rec => `
                <div class="recommendation-card">
                    <div class="recommendation-header">
                        <h4 class="recommendation-title">${rec.title}</h4>
                        <span class="recommendation-relevance">${rec.relevance}% relevant</span>
                    </div>
                    <p class="recommendation-description">${rec.description}</p>
                    ${rec.measurement_approach ? `
                        <div class="recommendation-measurement">
                            <strong>How to measure:</strong> ${rec.measurement_approach}
                        </div>
                    ` : ''}
                </div>
            `).join('');
            
            contentElement.innerHTML = recommendationsHTML;
        }
        
        // Show content
        contentElement.style.display = 'block';
        
        // Show action buttons
        this.showActionButtons();
    }
    
    showActionButtons() {
        const saveBtn = document.getElementById('save-recommendations');
        const shareBtn = document.getElementById('share-recommendations');
        
        if (saveBtn) saveBtn.style.display = 'inline-block';
        if (shareBtn) shareBtn.style.display = 'inline-block';
    }
}

// Global test function to check if everything is working
window.testSmartRecommendations = function() {
    console.log('🔍 Testing Smart Recommendations...');
    console.log('Script loaded:', !!window.SmartRecommendations);
    console.log('Instance exists:', !!window.smartRecommendations);
    
    const metricCards = document.querySelectorAll('.metric-card[data-id]');
    console.log(`Found ${metricCards.length} metric cards with data-id`);
    
    if (metricCards.length > 0) {
        console.log('First metric card:', metricCards[0]);
        console.log('First metric card data-id:', metricCards[0].dataset.id);
        
        // Test clicking the first card
        console.log('Testing click on first card...');
        metricCards[0].click();
    }
    
    const submitBtn = document.getElementById('get-recommendations-btn');
    console.log('Submit button found:', !!submitBtn);
    console.log('Submit button disabled:', submitBtn ? submitBtn.disabled : 'N/A');
};

// Global retry function for HTML onclick handler
window.retryRecommendations = function() {
    if (window.smartRecommendations) {
        window.smartRecommendations.fetchRecommendations();
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM Content Loaded - Initializing Smart Recommendations...');
    window.smartRecommendations = new SmartRecommendations();
});

// Also try to initialize immediately if DOM is already loaded
if (document.readyState === 'loading') {
    console.log('⏳ DOM still loading, waiting for DOMContentLoaded...');
} else {
    console.log('📄 DOM already loaded - Initializing Smart Recommendations immediately...');
    window.smartRecommendations = new SmartRecommendations();
}
