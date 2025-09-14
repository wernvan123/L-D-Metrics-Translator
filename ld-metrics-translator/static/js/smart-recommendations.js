/**
 * Smart AI Recommendations Module
 * Handles display and interaction with AI-generated recommendations for L&D concepts
 */

// Immediate test to verify script loading
console.log('🔥 SMART RECOMMENDATIONS SCRIPT LOADED!');
window.smartRecommendationsLoaded = true;

// Make class globally accessible
window.SmartRecommendations = class SmartRecommendations {
    constructor() {
        this.selectedMetrics = new Set();
        this.recommendations = [];
        this.isLoading = false;
        this.boundCards = new WeakSet();
        
        this.init();
    }
    
    init() {
        console.log('🚀 Smart Recommendations module starting initialization...');
        this.bindEvents();
        this.updateSelectionCounter();
        // Also listen to global sidebar selection changes
        document.addEventListener('selectionChanged', (e) => {
            try {
                const metrics = Array.isArray(e.detail?.metrics) ? e.detail.metrics : [];
                // IDs can be numbers; normalize to strings for Set consistency
                this.selectedMetrics = new Set(metrics.map(m => String(m.id)));
                this.updateSelectionCounter();
            } catch (err) {
                console.warn('selectionChanged handling failed:', err);
            }
        });
        console.log('✅ Smart Recommendations module initialized successfully');
    }
    
    updateSelectionCounter() {
        const counterElement = document.getElementById('plan-selected-metrics-count');
        const submitButton = document.getElementById('plan-get-recommendations-btn');
        
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
        }).catch(error => {
            console.error('Error in bindEvents:', error);
            // Fallback: try binding immediately
            setTimeout(() => {
                this.bindMetricCardEvents();
                this.bindSubmitButton();
            }, 1000);
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
            if (card.dataset.srListenerBound === '1') return; // avoid duplicate listeners
            card.addEventListener('click', this.handleMetricCardClick.bind(this), false);
            card.dataset.srListenerBound = '1';
            console.log(`Smart Recommendations: Bound click event to metric card ${card.dataset.id}`);
        });
    }
    
    bindSubmitButton() {
        const submitButton = document.getElementById('plan-get-recommendations-btn');
        if (submitButton) {
            submitButton.addEventListener('click', () => {
                if (this.selectedMetrics.size > 0 && !this.isLoading) {
                    this.fetchRecommendations();
                }
            });
        }
    }
    
    handleMetricCardClick(event) {
        // Ignore clicks on action buttons within the card
        if (event.target.closest('.metric-actions')) return;
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
            // Notify StreamlinedSidebar that a metric was deselected
            try {
                const deselectEvt = new CustomEvent('metricDeselected', { detail: Number(metricId) });
                document.dispatchEvent(deselectEvt);
            } catch (e) {
                console.warn('Failed to dispatch metricDeselected:', e);
            }
        } else {
            this.selectedMetrics.add(metricId);
            metricCard.classList.add('selected');
            this.addTickMark(metricCard);
            console.log(`Selected metric ${metricId}`);
            // Notify StreamlinedSidebar that a metric was selected
            try {
                const name = metricCard.dataset.name || metricCard.querySelector('.metric-title')?.textContent?.trim() || `Metric ${metricId}`;
                const selectEvt = new CustomEvent('metricSelected', { detail: { id: Number(metricId), name } });
                document.dispatchEvent(selectEvt);
            } catch (e) {
                console.warn('Failed to dispatch metricSelected:', e);
            }
        }
        
        console.log('Currently selected metrics:', Array.from(this.selectedMetrics));
        
        // Update selection counter and button state
        this.updateSelectionCounter();

        // Dispatch selection changed event for integration
        this.dispatchSelectionChanged();
    }

    dispatchSelectionChanged() {
        try {
            const selected = Array.from(this.selectedMetrics).map(id => {
                const el = document.querySelector(`.metric-card[data-id="${CSS.escape(id)}"]`);
                const name = el?.dataset?.name || `Metric ${id}`;
                return { id, name };
            });
            const evt = new CustomEvent('metricSelectionChanged', { detail: selected });
            document.dispatchEvent(evt);
        } catch (e) {
            console.warn('Failed to dispatch metricSelectionChanged:', e);
        }
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

            // Use existing backend endpoint
            const requestBody = {
                categories: [],
                outcomes: [],
                metrics: selectedMetricIds.map(id => Number(id)),
                context: 'user_selection'
            };
            const response = await fetch('/api/recommendations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                let errorDetail = '';
                try {
                    const ct = response.headers.get('content-type') || '';
                    if (ct.includes('application/json')) {
                        const errJson = await response.json();
                        errorDetail = errJson.error || JSON.stringify(errJson);
                    } else {
                        errorDetail = await response.text();
                    }
                } catch (parseErr) {
                    errorDetail = 'No error body available';
                }
                const httpMsg = `HTTP ${response.status} ${response.statusText || ''}`.trim();
                throw new Error(`${httpMsg} - ${errorDetail}`);
            }

            const data = await response.json();
            console.log('Received recommendations:', data);

            const recs = (data.recommendations || data.data || []);
            if (Array.isArray(recs) || Array.isArray(data?.recommendations?.primary)) {
                // Support both flat and structured recommendations
                this.recommendations = Array.isArray(recs) ? recs : (data.recommendations.primary || []);
                this.displayRecommendations();
                this.dispatchAIRecommendationsUpdated();
            } else {
                throw new Error(data.error || `Unexpected recommendations payload: ${JSON.stringify(data).slice(0, 500)}`);
            }

        } catch (error) {
            console.error('Error fetching recommendations:', error);
            // Provide additional debugging info without exposing to end-user UI
            try {
                console.debug('[SmartRecommendations] Request payload:', {
                    categories: [],
                    outcomes: [],
                    metrics: Array.from(this.selectedMetrics).map(id => Number(id)),
                    context: 'user_selection'
                });
            } catch (_) { /* noop */ }
            this.showError('Failed to generate recommendations. Please try again.');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    dispatchAIRecommendationsUpdated() {
        try {
            const evt = new CustomEvent('aiRecommendationsUpdated', { detail: this.recommendations });
            document.dispatchEvent(evt);
        } catch (e) {
            console.warn('Failed to dispatch aiRecommendationsUpdated:', e);
        }
    }
    
    showRecommendationsContainer() {
        const container = document.getElementById('plan-smart-recommendations-container');
        if (container) {
            container.style.display = 'block';
        }
    }
    
    showLoading() {
        const loadingElement = document.getElementById('plan-recommendations-loading');
        const contentElement = document.getElementById('plan-recommendations-content');
        const errorElement = document.getElementById('plan-recommendations-error');
        
        if (loadingElement) loadingElement.style.display = 'block';
        if (contentElement) contentElement.style.display = 'none';
        if (errorElement) errorElement.style.display = 'none';
    }
    
    hideLoading() {
        const loadingElement = document.getElementById('plan-recommendations-loading');
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
    }
    
    showError(message) {
        const errorElement = document.getElementById('plan-recommendations-error');
        const contentElement = document.getElementById('plan-recommendations-content');
        
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
        const contentElement = document.getElementById('plan-recommendations-content');
        const errorElement = document.getElementById('plan-recommendations-error');
        
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
                        <h4 class="recommendation-title">${rec.concept || rec.title || 'Recommendation'}</h4>
                        <span class="recommendation-relevance">${rec.relevance || rec.score || 'High'}</span>
                    </div>
                    <p class="recommendation-description">${rec.definition || rec.description || ''}</p>
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
        const saveBtn = document.getElementById('plan-save-recommendations');
        const shareBtn = document.getElementById('plan-share-recommendations');
        
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
    
    const submitBtn = document.getElementById('plan-get-recommendations-btn');
    console.log('Submit button found:', !!submitBtn);
    console.log('Submit button disabled:', submitBtn ? submitBtn.disabled : 'N/A');
};

// Global retry function for HTML onclick handler
window.retryRecommendations = function() {
    if (window.smartRecommendations) {
        window.smartRecommendations.fetchRecommendations();
    }
};

// Bootstrap (prevent double initialization)
(function bootstrapSmartRecommendations() {
    const init = () => {
        if (window.smartRecommendations) {
            console.log('♻️ SmartRecommendations already initialized, skipping re-init');
            // Ensure bindings are up to date for any late-loaded cards
            window.smartRecommendations.bindMetricCardEvents();
            return;
        }
        console.log('🚀 Initializing SmartRecommendations');
        window.smartRecommendations = new SmartRecommendations();
        // Ensure bindings after a short delay in case cards render late
        setTimeout(() => window.smartRecommendations?.bindMetricCardEvents(), 1500);
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
