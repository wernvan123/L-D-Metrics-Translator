/**
 * Section Navigation System for L&D Metrics Translator
 * Handles sticky navigation, smooth scrolling, and active section highlighting
 */

class SectionNavigation {
    constructor() {
        this.sections = [];
        this.navItems = [];
        this.currentSection = 'key-numbers';
        this.isScrolling = false;
        this.adminOverlay = null;
        this.init();
    }

    init() {
        document.addEventListener('DOMContentLoaded', () => {
            this.setupElements();
            this.setupEventListeners();
            this.setupIntersectionObserver();
            this.updateActiveSection();
        });
    }

    setupElements() {
        // Get all page sections
        this.sections = Array.from(document.querySelectorAll('.page-section'));
        
        // Get all navigation items
        this.navItems = Array.from(document.querySelectorAll('.nav-section'));
        
        // Get admin overlay
        this.adminOverlay = document.getElementById('admin-overlay');
        
        console.log('Section Navigation: Found', this.sections.length, 'sections and', this.navItems.length, 'nav items');
    }

    setupEventListeners() {
        // Navigation click handlers
        this.navItems.forEach(navItem => {
            navItem.addEventListener('click', (e) => {
                e.preventDefault();
                const targetSection = navItem.getAttribute('data-section');
                this.scrollToSection(targetSection);
            });
        });

        // Admin toggle handler
        const adminToggle = document.getElementById('admin-toggle');
        if (adminToggle) {
            adminToggle.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleAdminPanel();
            });
        }

        // Admin close handler
        const adminClose = document.getElementById('admin-close');
        if (adminClose) {
            adminClose.addEventListener('click', () => {
                this.closeAdminPanel();
            });
        }

        // Close admin on overlay click
        if (this.adminOverlay) {
            this.adminOverlay.addEventListener('click', (e) => {
                if (e.target === this.adminOverlay) {
                    this.closeAdminPanel();
                }
            });
        }

        // Handle scroll events for sticky navigation
        let ticking = false;
        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    this.handleScroll();
                    ticking = false;
                });
                ticking = true;
            }
        });

        // Handle resize events
        window.addEventListener('resize', () => {
            this.updateActiveSection();
        });
    }

    setupIntersectionObserver() {
        // Create intersection observer for section detection
        const observerOptions = {
            root: null,
            rootMargin: '-20% 0px -70% 0px', // Trigger when section is 20% from top
            threshold: 0
        };

        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const sectionId = entry.target.id;
                    if (sectionId && !this.isScrolling) {
                        this.setActiveSection(sectionId);
                    }
                }
            });
        }, observerOptions);

        // Observe all sections
        this.sections.forEach(section => {
            this.observer.observe(section);
        });
    }

    handleScroll() {
        const sectionNav = document.getElementById('section-nav');
        if (!sectionNav) return;

        const scrollY = window.scrollY;
        const heroSection = document.querySelector('.hero-section');
        const heroHeight = heroSection ? heroSection.offsetHeight : 200;

        // Make navigation sticky after hero section
        if (scrollY > heroHeight - 100) {
            sectionNav.classList.add('sticky');
        } else {
            sectionNav.classList.remove('sticky');
        }
    }

    scrollToSection(sectionId) {
        const targetSection = document.getElementById(sectionId);
        if (!targetSection) return;

        this.isScrolling = true;
        this.setActiveSection(sectionId);

        // Calculate scroll position accounting for sticky nav
        const sectionNav = document.getElementById('section-nav');
        const navHeight = sectionNav ? sectionNav.offsetHeight : 80;
        const targetPosition = targetSection.offsetTop - navHeight - 20;

        // Smooth scroll to section
        window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
        });

        // Reset scrolling flag after animation
        setTimeout(() => {
            this.isScrolling = false;
        }, 1000);
    }

    setActiveSection(sectionId) {
        if (this.currentSection === sectionId) return;

        this.currentSection = sectionId;
        this.updateActiveSection();
    }

    updateActiveSection() {
        // Update navigation active states
        this.navItems.forEach(navItem => {
            const itemSection = navItem.getAttribute('data-section');
            if (itemSection === this.currentSection) {
                navItem.classList.add('active');
            } else {
                navItem.classList.remove('active');
            }
        });

        // Update page title if needed
        this.updatePageTitle();
    }

    updatePageTitle() {
        const sectionTitles = {
            'key-numbers': 'Key Numbers',
            'explore': 'Explore Metrics',
            'analyse': 'Analyse Events',
            'implement': 'Implement Solutions'
        };

        const baseTitle = 'L & D Metrics Translator';
        const sectionTitle = sectionTitles[this.currentSection];
        
        if (sectionTitle) {
            document.title = `${sectionTitle} - ${baseTitle}`;
        } else {
            document.title = baseTitle;
        }
    }

    toggleAdminPanel() {
        if (!this.adminOverlay) return;

        const isVisible = this.adminOverlay.style.display !== 'none';
        
        if (isVisible) {
            this.closeAdminPanel();
        } else {
            this.openAdminPanel();
        }
    }

    openAdminPanel() {
        if (!this.adminOverlay) return;

        this.adminOverlay.style.display = 'flex';
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
        
        // Add animation class
        setTimeout(() => {
            this.adminOverlay.classList.add('active');
        }, 10);
    }

    closeAdminPanel() {
        if (!this.adminOverlay) return;

        this.adminOverlay.classList.remove('active');
        document.body.style.overflow = ''; // Restore scrolling
        
        // Hide after animation
        setTimeout(() => {
            this.adminOverlay.style.display = 'none';
        }, 300);
    }

    // Public API methods
    goToSection(sectionId) {
        this.scrollToSection(sectionId);
    }

    getCurrentSection() {
        return this.currentSection;
    }

    // Keyboard navigation support
    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // ESC to close admin panel
            if (e.key === 'Escape' && this.adminOverlay && this.adminOverlay.style.display !== 'none') {
                this.closeAdminPanel();
                return;
            }

            // Number keys for section navigation (1-4)
            if (e.key >= '1' && e.key <= '4' && !e.ctrlKey && !e.altKey) {
                const sectionMap = {
                    '1': 'key-numbers',
                    '2': 'explore', 
                    '3': 'analyse',
                    '4': 'implement'
                };
                
                const targetSection = sectionMap[e.key];
                if (targetSection) {
                    e.preventDefault();
                    this.scrollToSection(targetSection);
                }
            }
        });
    }
}

// Initialize section navigation
const sectionNavigation = new SectionNavigation();

// Setup keyboard navigation
document.addEventListener('DOMContentLoaded', () => {
    sectionNavigation.setupKeyboardNavigation();
});

// Export for global access
window.sectionNavigation = sectionNavigation;

// Utility functions for other scripts
window.goToSection = (sectionId) => sectionNavigation.goToSection(sectionId);
window.getCurrentSection = () => sectionNavigation.getCurrentSection();

console.log('Section Navigation System: Loaded');
