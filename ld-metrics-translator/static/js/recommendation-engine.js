/**
 * Rules-Based Recommendation Engine for L&D Metrics Translator
 * Provides intelligent metric recommendations based on user selections and context
 */

class RecommendationEngine {
    constructor() {
        this.recommendations = [];
        this.metricTemplates = this.initializeMetricTemplates();
        this.combinationRules = this.initializeCombinationRules();
        this.outcomeContexts = this.initializeOutcomeContexts();
        this.fallbackRecommendations = this.initializeFallbackRecommendations();
        this.panel = null;
        this.recommendationContent = null;
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initializeAfterDOMReady();
            });
        } else {
            this.initializeAfterDOMReady();
        }
    }

    initializeAfterDOMReady() {
        console.log('RecommendationEngine: Initializing after DOM ready');
        
        // Initialize recommendation display area
        this.createRecommendationPanel();
        
        // Listen for selection changes
        this.bindSelectionEvents();
        
        // Generate initial recommendations
        this.generateInitialRecommendations();
        
        console.log('RecommendationEngine: Initialization complete');
    }

    createRecommendationPanel() {
        try {
            console.log('RecommendationEngine: Looking for smart recommendations container');
            
            // Use the existing smart recommendations container from HTML
            this.recommendationContent = document.getElementById('smart-recommendations-container');
            
            if (!this.recommendationContent) {
                console.error('RecommendationEngine: smart-recommendations-container not found in DOM');
                return;
            }
            
            console.log('RecommendationEngine: Found smart recommendations container');
            return;
            
            // Find the metrics container and its parent
            const metricsContainer = document.getElementById('metrics-container');
            const exploreSection = document.getElementById('explore');
            
            // Remove panel from its current position if it exists
            if (panel.parentNode) {
                panel.parentNode.removeChild(panel);
            }
            
            // Insert the panel in the correct position - right after the metrics container
            if (metricsContainer && metricsContainer.parentNode) {
                // Insert after metrics container within the Explore section
                metricsContainer.parentNode.insertBefore(panel, metricsContainer.nextSibling);
                console.log('RecommendationEngine: Panel positioned after metrics container');
            } else if (exploreSection) {
                // Fallback: Append to end of Explore section
                exploreSection.appendChild(panel);
                console.log('RecommendationEngine: Panel appended to Explore section');
            } else {
                // Last resort: Append to body
                document.body.appendChild(panel);
                console.warn('RecommendationEngine: Could not find Explore section, appending to body');
            }
            
            // Remove the hidden class and add visible class after a short delay to allow for CSS transitions
            setTimeout(() => {
                panel.classList.remove('hidden');
                panel.classList.add('visible');
            }, 50);
            
            console.log('RecommendationEngine: Panel created/positioned successfully');
            return true;
        } catch (error) {
            console.error('RecommendationEngine: Error creating/positioning panel:', error);
            return false;
        }
    }

    togglePanel() {
        if (!this.panel) return;
        
        if (this.panel.classList.contains('hidden')) {
            // Show the panel with smooth transition
            this.panel.classList.remove('hidden');
            // Force reflow to ensure the transition plays
            void this.panel.offsetHeight;
            this.panel.classList.add('visible');
        } else {
            // Hide the panel with smooth transition
            this.panel.classList.remove('visible');
            // Wait for the transition to complete before hiding
            this.panel.addEventListener('transitionend', () => {
                if (!this.panel.classList.contains('visible')) {
                    this.panel.classList.add('hidden');
                }
            }, { once: true });
        }
    }

    bindSelectionEvents() {
        // Listen to multi-select navigation changes
        if (window.multiSelectNav) {
            const originalApplyFiltering = window.multiSelectNav.applyFiltering;
            window.multiSelectNav.applyFiltering = () => {
                originalApplyFiltering.call(window.multiSelectNav);
                this.generateRecommendations();
            };
        }

        // Listen to dropdown changes
        document.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox' && e.target.closest('.dropdown-content')) {
                setTimeout(() => this.generateRecommendations(), 100);
            }
        });
    }

    generateInitialRecommendations() {
        console.log('RecommendationEngine: Generating initial recommendations');
        this.recommendations = [
            {
                title: 'Start by selecting metrics',
                description: 'Choose metrics from the Explore section to get personalized recommendations',
                priority: 'low'
            }
        ];
        this.displayRecommendations({
            title: 'Getting Started',
            items: this.recommendations
        });
    }

    generateRecommendations() {
        console.log('RecommendationEngine: Generating recommendations');
        // Simulate API call with timeout
        setTimeout(() => {
            this.recommendations = [
                {
                    title: 'Sample Recommendation 1',
                    description: 'This is a sample recommendation based on your selections',
                    priority: 'high'
                },
                {
                    title: 'Sample Recommendation 2',
                    description: 'This is another sample recommendation',
                    priority: 'medium'
                }
            ];
            this.displayRecommendations({
                title: 'Your Recommendations',
                items: this.recommendations
            });
        }, 500);
    }

    displayRecommendations(recommendations) {
        console.log('RecommendationEngine: Displaying recommendations:', recommendations);
        
        if (!this.recommendationContent) {
            console.error('RecommendationEngine: Recommendation content element not found');
            return;
        }
        
        let html = `
            <div class="recommendation-list">
                <h4>${recommendations.title || 'Recommendations'}</h4>
        `;
        
        if (recommendations.items && recommendations.items.length > 0) {
            recommendations.items.forEach(item => {
                const priorityClass = item.priority || 'medium';
                html += `
                    <div class="recommendation-item ${priorityClass}">
                        <h5>${item.title}</h5>
                        <p>${item.description}</p>
                    </div>
                `;
            });
        } else {
            html += '<p>No recommendations available. Try selecting different metrics.</p>';
        }
        
        html += '</div>';
        this.recommendationContent.innerHTML = html;
    }

    // Stub methods - these would be implemented with actual logic
    initializeMetricTemplates() { return {}; }
    initializeCombinationRules() { return []; }
    initializeOutcomeContexts() { return {}; }
    initializeFallbackRecommendations() { return {}; }
}

// Initialize recommendation engine with error handling
let recommendationEngine;

function initializeRecommendationEngine() {
    try {
        console.log('RecommendationEngine: Initializing recommendation engine');
        recommendationEngine = new RecommendationEngine();
        window.recommendationEngine = recommendationEngine;
        return true;
    } catch (error) {
        console.error('RecommendationEngine: Error initializing recommendation engine:', error);
        return false;
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('RecommendationEngine: DOM loaded, creating instance');
        initializeRecommendationEngine();
    });
} else {
    console.log('RecommendationEngine: DOM already ready, creating instance');
    initializeRecommendationEngine();
}

// Export for debugging
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { RecommendationEngine };
}
