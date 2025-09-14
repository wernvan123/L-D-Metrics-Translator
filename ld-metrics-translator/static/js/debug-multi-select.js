// Debug script to test multi-select dropdowns
console.log('Debug script loaded');

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded - testing multi-select functionality');
    
    // Test if dropdowns exist
    const categoriesDropdown = document.getElementById('categories-dropdown');
    const outcomesDropdown = document.getElementById('outcomes-dropdown');
    
    console.log('Categories dropdown:', categoriesDropdown);
    console.log('Outcomes dropdown:', outcomesDropdown);
    
    // Test if multi-select nav is initialized
    console.log('Window multiSelectNav:', window.multiSelectNav);
    
    // Add click listeners to test dropdown opening
    const categoryButton = document.querySelector('[onclick*="categories-dropdown"]');
    if (categoryButton) {
        console.log('Category button found:', categoryButton);
        categoryButton.addEventListener('click', function(e) {
            console.log('Category button clicked');
            e.preventDefault();
            
            // Manually toggle dropdown
            if (categoriesDropdown) {
                const isVisible = categoriesDropdown.style.display === 'block';
                categoriesDropdown.style.display = isVisible ? 'none' : 'block';
                console.log('Dropdown toggled to:', categoriesDropdown.style.display);
            }
        });
    }
    
    // Test checkbox functionality
    setTimeout(() => {
        const checkboxes = document.querySelectorAll('#categories-dropdown input[type="checkbox"]');
        console.log('Found checkboxes:', checkboxes.length);
        
        checkboxes.forEach((checkbox, index) => {
            checkbox.addEventListener('change', function() {
                console.log(`Checkbox ${index} changed:`, this.checked, this.value, this.dataset.name);
                
                // Create a simple filter tag for testing
                createTestFilterTag(this.dataset.name, this.checked);
            });
        });
    }, 1000);
});

function createTestFilterTag(name, isSelected) {
    if (!isSelected) return;
    
    let filterContainer = document.querySelector('.test-filter-tags');
    if (!filterContainer) {
        filterContainer = document.createElement('div');
        filterContainer.className = 'test-filter-tags';
        filterContainer.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: white;
            padding: 10px;
            border: 2px solid #667eea;
            border-radius: 8px;
            z-index: 10000;
            max-width: 300px;
        `;
        
        const title = document.createElement('h4');
        title.textContent = 'Test Filter Tags:';
        title.style.margin = '0 0 10px 0';
        filterContainer.appendChild(title);
        
        document.body.appendChild(filterContainer);
    }
    
    const tag = document.createElement('span');
    tag.style.cssText = `
        display: inline-block;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        margin: 2px;
    `;
    tag.textContent = `Category: ${name}`;
    
    filterContainer.appendChild(tag);
    
    console.log('Created test filter tag for:', name);
}
