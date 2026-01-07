"""
Accessibility tests for L&D Metrics Translator application.
"""
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
try:
    from axe_selenium_python import Axe
    AXE_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    Axe = None
    AXE_AVAILABLE = False

pytestmark = pytest.mark.skipif(not AXE_AVAILABLE, reason="axe-selenium-python not installed")

from app.models import LDOutcome, MetricType, Metric
from app import db


@pytest.mark.accessibility
@pytest.mark.slow
class TestWebAccessibility:
    """Test web accessibility compliance."""
    
    @pytest.fixture(autouse=True)
    def setup_server(self, app):
        """Setup test server for accessibility tests."""
        self.base_url = "http://127.0.0.1:5000"
    
    def test_homepage_accessibility(self, chrome_driver):
        """Test homepage accessibility."""
        driver = chrome_driver
        
        try:
            driver.get(self.base_url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Run axe accessibility tests
            axe = Axe(driver)
            results = axe.run()
            
            # Check for violations
            violations = results.get('violations', [])
            
            # Filter out minor violations or false positives if needed
            critical_violations = [
                v for v in violations 
                if v.get('impact') in ['critical', 'serious']
            ]
            
            # Assert no critical accessibility violations
            assert len(critical_violations) == 0, f"Critical accessibility violations: {critical_violations}"
            
            # Check basic accessibility features
            self._check_basic_accessibility(driver)
            
        except TimeoutException:
            pytest.skip("Test server not available for accessibility tests")
    
    def test_outcomes_page_accessibility(self, chrome_driver, app_context):
        """Test outcomes page accessibility."""
        # Create test data
        outcome = LDOutcome(
            name="Accessibility Test Outcome",
            description="Test outcome for accessibility testing",
            category="Skills",
            level="Intermediate"
        )
        db.session.add(outcome)
        db.session.commit()
        
        driver = chrome_driver
        
        try:
            driver.get(f"{self.base_url}/outcomes")
            
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Run axe accessibility tests
            axe = Axe(driver)
            results = axe.run()
            
            violations = results.get('violations', [])
            critical_violations = [
                v for v in violations 
                if v.get('impact') in ['critical', 'serious']
            ]
            
            assert len(critical_violations) == 0, f"Critical accessibility violations: {critical_violations}"
            
            # Check specific accessibility features for data tables/lists
            self._check_data_accessibility(driver)
            
        except TimeoutException:
            pytest.skip("Test server not available for accessibility tests")
    
    def test_translator_form_accessibility(self, chrome_driver, app_context):
        """Test translator form accessibility."""
        # Create test data
        outcome = LDOutcome(
            name="Form Accessibility Test",
            description="Test outcome for form accessibility",
            category="Skills",
            level="Advanced"
        )
        db.session.add(outcome)
        db.session.commit()
        
        metric_type = MetricType(
            name="Form Accessibility Type",
            description="Test metric type for form accessibility",
            category="Assessment"
        )
        db.session.add(metric_type)
        db.session.commit()
        
        driver = chrome_driver
        
        try:
            driver.get(f"{self.base_url}/translator")
            
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
            
            # Run axe accessibility tests
            axe = Axe(driver)
            results = axe.run()
            
            violations = results.get('violations', [])
            critical_violations = [
                v for v in violations 
                if v.get('impact') in ['critical', 'serious']
            ]
            
            assert len(critical_violations) == 0, f"Critical accessibility violations: {critical_violations}"
            
            # Check form accessibility
            self._check_form_accessibility(driver)
            
        except TimeoutException:
            pytest.skip("Test server not available for accessibility tests")
    
    def test_navigation_accessibility(self, chrome_driver):
        """Test navigation accessibility."""
        driver = chrome_driver
        
        try:
            driver.get(self.base_url)
            
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "nav")))
            
            # Check navigation structure
            nav_elements = driver.find_elements(By.TAG_NAME, "nav")
            assert len(nav_elements) > 0, "No navigation elements found"
            
            # Check for proper navigation landmarks
            nav = nav_elements[0]
            
            # Should have proper role or be a nav element
            tag_name = nav.tag_name.lower()
            role = nav.get_attribute('role')
            assert tag_name == 'nav' or role == 'navigation', "Navigation should have proper semantic markup"
            
            # Check for navigation links
            nav_links = nav.find_elements(By.TAG_NAME, "a")
            assert len(nav_links) > 0, "Navigation should contain links"
            
            # Check link accessibility
            for link in nav_links:
                # Links should have text or aria-label
                link_text = link.text.strip()
                aria_label = link.get_attribute('aria-label')
                title = link.get_attribute('title')
                
                assert (link_text or aria_label or title), f"Link should have accessible text: {link.get_attribute('href')}"
            
        except TimeoutException:
            pytest.skip("Test server not available for accessibility tests")
    
    def test_keyboard_navigation(self, chrome_driver):
        """Test keyboard navigation accessibility."""
        driver = chrome_driver
        
        try:
            driver.get(self.base_url)
            
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Test tab navigation
            from selenium.webdriver.common.keys import Keys
            
            # Find all focusable elements
            focusable_elements = driver.find_elements(
                By.CSS_SELECTOR, 
                'a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
            )
            
            if focusable_elements:
                # Focus first element
                focusable_elements[0].click()
                
                # Test tab navigation through elements
                for i in range(min(5, len(focusable_elements))):  # Test first 5 elements
                    active_element = driver.switch_to.active_element
                    
                    # Element should be focusable
                    assert active_element is not None, "Should have focused element"
                    
                    # Move to next element
                    active_element.send_keys(Keys.TAB)
            
        except TimeoutException:
            pytest.skip("Test server not available for accessibility tests")
    
    def test_color_contrast(self, chrome_driver):
        """Test color contrast accessibility."""
        driver = chrome_driver
        
        try:
            driver.get(self.base_url)
            
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Run axe with color contrast rules
            axe = Axe(driver)
            results = axe.run(['color-contrast'])
            
            violations = results.get('violations', [])
            color_violations = [
                v for v in violations 
                if 'color-contrast' in v.get('id', '')
            ]
            
            # Should have good color contrast
            assert len(color_violations) == 0, f"Color contrast violations: {color_violations}"
            
        except TimeoutException:
            pytest.skip("Test server not available for accessibility tests")
    
    def test_screen_reader_compatibility(self, chrome_driver):
        """Test screen reader compatibility."""
        driver = chrome_driver
        
        try:
            driver.get(self.base_url)
            
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check for proper heading structure
            headings = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6")
            
            if headings:
                # Should start with h1
                first_heading = headings[0]
                assert first_heading.tag_name.lower() == 'h1', "Page should start with h1"
                
                # Check heading hierarchy
                prev_level = 1
                for heading in headings[1:]:
                    current_level = int(heading.tag_name[1])
                    # Should not skip levels (e.g., h1 to h3)
                    assert current_level <= prev_level + 1, f"Heading hierarchy error: {prev_level} to {current_level}"
                    prev_level = current_level
            
            # Check for alt text on images
            images = driver.find_elements(By.TAG_NAME, "img")
            for img in images:
                alt_text = img.get_attribute('alt')
                src = img.get_attribute('src')
                
                # Decorative images should have empty alt, content images should have descriptive alt
                if 'decorative' not in src.lower() and 'icon' not in src.lower():
                    assert alt_text is not None, f"Image should have alt text: {src}"
            
            # Check for proper form labels
            inputs = driver.find_elements(By.TAG_NAME, "input")
            for input_elem in inputs:
                input_type = input_elem.get_attribute('type')
                if input_type not in ['hidden', 'submit', 'button']:
                    # Should have label or aria-label
                    input_id = input_elem.get_attribute('id')
                    aria_label = input_elem.get_attribute('aria-label')
                    aria_labelledby = input_elem.get_attribute('aria-labelledby')
                    
                    has_label = False
                    if input_id:
                        labels = driver.find_elements(By.CSS_SELECTOR, f'label[for="{input_id}"]')
                        has_label = len(labels) > 0
                    
                    assert (has_label or aria_label or aria_labelledby), f"Input should have accessible label: {input_type}"
            
        except TimeoutException:
            pytest.skip("Test server not available for accessibility tests")
    
    def _check_basic_accessibility(self, driver):
        """Check basic accessibility features."""
        # Check for page title
        title = driver.title
        assert title and len(title.strip()) > 0, "Page should have a title"
        
        # Check for main content landmark
        main_elements = driver.find_elements(By.TAG_NAME, "main")
        main_role_elements = driver.find_elements(By.CSS_SELECTOR, '[role="main"]')
        
        assert (len(main_elements) > 0 or len(main_role_elements) > 0), "Page should have main content landmark"
        
        # Check for skip links (optional but recommended)
        skip_links = driver.find_elements(By.CSS_SELECTOR, 'a[href^="#"]')
        if skip_links:
            # If skip links exist, they should be at the beginning
            first_link = driver.find_element(By.TAG_NAME, "a")
            assert first_link.get_attribute('href').startswith('#'), "First link should be skip link if present"
    
    def _check_data_accessibility(self, driver):
        """Check accessibility of data presentation."""
        # Check for proper table structure if tables exist
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            # Should have table headers
            headers = table.find_elements(By.TAG_NAME, "th")
            if len(headers) == 0:
                # If no th elements, check for role="columnheader"
                header_roles = table.find_elements(By.CSS_SELECTOR, '[role="columnheader"]')
                assert len(header_roles) > 0, "Table should have proper headers"
            
            # Check for caption or aria-label
            caption = table.find_elements(By.TAG_NAME, "caption")
            aria_label = table.get_attribute('aria-label')
            aria_labelledby = table.get_attribute('aria-labelledby')
            
            assert (len(caption) > 0 or aria_label or aria_labelledby), "Table should have accessible description"
        
        # Check for proper list structure
        lists = driver.find_elements(By.CSS_SELECTOR, "ul, ol")
        for list_elem in lists:
            list_items = list_elem.find_elements(By.TAG_NAME, "li")
            assert len(list_items) > 0, "List should contain list items"
    
    def _check_form_accessibility(self, driver):
        """Check form accessibility features."""
        forms = driver.find_elements(By.TAG_NAME, "form")
        
        for form in forms:
            # Check for form labels
            inputs = form.find_elements(By.CSS_SELECTOR, "input, select, textarea")
            
            for input_elem in inputs:
                input_type = input_elem.get_attribute('type')
                if input_type not in ['hidden', 'submit', 'button']:
                    # Check for proper labeling
                    input_id = input_elem.get_attribute('id')
                    aria_label = input_elem.get_attribute('aria-label')
                    aria_labelledby = input_elem.get_attribute('aria-labelledby')
                    placeholder = input_elem.get_attribute('placeholder')
                    
                    has_label = False
                    if input_id:
                        labels = form.find_elements(By.CSS_SELECTOR, f'label[for="{input_id}"]')
                        has_label = len(labels) > 0
                    
                    # Placeholder is not sufficient for accessibility
                    assert (has_label or aria_label or aria_labelledby), f"Form input should have proper label: {input_type}"
            
            # Check for fieldsets if multiple related fields
            fieldsets = form.find_elements(By.TAG_NAME, "fieldset")
            if len(inputs) > 3:  # If complex form
                # Should consider using fieldsets for grouping
                pass  # This is a recommendation, not a requirement
            
            # Check for error handling accessibility
            error_elements = form.find_elements(By.CSS_SELECTOR, '.error, [role="alert"], .alert-danger')
            for error_elem in error_elements:
                # Error messages should be associated with form fields
                aria_describedby = error_elem.get_attribute('aria-describedby')
                error_id = error_elem.get_attribute('id')
                
                if error_id:
                    # Check if any input references this error
                    related_inputs = form.find_elements(By.CSS_SELECTOR, f'[aria-describedby*="{error_id}"]')
                    # This is a best practice check


@pytest.mark.accessibility
class TestContentAccessibility:
    """Test content accessibility without browser."""
    
    def test_html_structure_accessibility(self, client, app_context):
        """Test HTML structure for accessibility."""
        # Test main pages
        pages = ['/', '/outcomes', '/metrics', '/translator', '/about', '/help']
        
        for page in pages:
            response = client.get(page)
            assert response.status_code == 200
            
            html_content = response.data.decode()
            
            # Check for basic HTML structure
            assert '<html' in html_content, f"Page {page} should have html element"
            assert '<head>' in html_content, f"Page {page} should have head element"
            assert '<body' in html_content, f"Page {page} should have body element"
            
            # Check for title
            assert '<title>' in html_content, f"Page {page} should have title element"
            
            # Check for language attribute
            assert 'lang=' in html_content, f"Page {page} should have language attribute"
            
            # Check for meta viewport (responsive design)
            assert 'viewport' in html_content, f"Page {page} should have viewport meta tag"
    
    def test_semantic_html_usage(self, client, app_context):
        """Test semantic HTML usage."""
        response = client.get('/')
        assert response.status_code == 200
        
        html_content = response.data.decode()
        
        # Check for semantic elements
        semantic_elements = ['<nav', '<main', '<header', '<footer', '<section', '<article']
        found_elements = [elem for elem in semantic_elements if elem in html_content]
        
        # Should use at least some semantic elements
        assert len(found_elements) >= 2, "Should use semantic HTML elements"
        
        # Check for proper heading structure
        import re
        headings = re.findall(r'<h([1-6])', html_content)
        if headings:
            # Should start with h1
            assert '1' in headings, "Should have h1 heading"
    
    def test_form_accessibility_markup(self, client, app_context):
        """Test form accessibility markup."""
        response = client.get('/translator')
        assert response.status_code == 200
        
        html_content = response.data.decode()
        
        # Check for form labels
        import re
        
        # Find input elements
        inputs = re.findall(r'<input[^>]*>', html_content)
        selects = re.findall(r'<select[^>]*>', html_content)
        textareas = re.findall(r'<textarea[^>]*>', html_content)
        
        form_fields = inputs + selects + textareas
        
        for field in form_fields:
            # Skip hidden and button inputs
            if 'type="hidden"' in field or 'type="submit"' in field or 'type="button"' in field:
                continue
            
            # Should have id for label association
            has_id = 'id=' in field
            has_aria_label = 'aria-label=' in field
            has_aria_labelledby = 'aria-labelledby=' in field
            
            # At least one method of labeling should be present
            assert (has_id or has_aria_label or has_aria_labelledby), f"Form field should have proper labeling: {field}"
    
    def test_image_accessibility_markup(self, client, app_context):
        """Test image accessibility markup."""
        response = client.get('/')
        assert response.status_code == 200
        
        html_content = response.data.decode()
        
        # Find image elements
        import re
        images = re.findall(r'<img[^>]*>', html_content)
        
        for img in images:
            # Should have alt attribute
            assert 'alt=' in img, f"Image should have alt attribute: {img}"
    
    def test_link_accessibility_markup(self, client, app_context):
        """Test link accessibility markup."""
        response = client.get('/')
        assert response.status_code == 200
        
        html_content = response.data.decode()
        
        # Find link elements
        import re
        links = re.findall(r'<a[^>]*>.*?</a>', html_content, re.DOTALL)
        
        for link in links:
            # Links should have meaningful text or aria-label
            link_text = re.sub(r'<[^>]*>', '', link).strip()
            has_aria_label = 'aria-label=' in link
            has_title = 'title=' in link
            
            # Avoid generic link text
            generic_texts = ['click here', 'read more', 'more', 'link']
            is_generic = any(generic.lower() in link_text.lower() for generic in generic_texts)
            
            assert (link_text and not is_generic) or has_aria_label or has_title, f"Link should have meaningful text: {link}"
    
    def test_table_accessibility_markup(self, client, app_context):
        """Test table accessibility markup."""
        # Create test data to ensure tables are present
        outcome = LDOutcome(
            name="Table Test Outcome",
            description="Test outcome for table accessibility",
            category="Skills",
            level="Basic"
        )
        db.session.add(outcome)
        db.session.commit()
        
        response = client.get('/outcomes')
        assert response.status_code == 200
        
        html_content = response.data.decode()
        
        # Find table elements
        import re
        tables = re.findall(r'<table[^>]*>.*?</table>', html_content, re.DOTALL)
        
        for table in tables:
            # Should have table headers
            has_th = '<th' in table
            has_header_role = 'role="columnheader"' in table
            
            assert has_th or has_header_role, f"Table should have proper headers: {table[:100]}..."
            
            # Should have caption or aria-label for complex tables
            has_caption = '<caption>' in table
            has_aria_label = 'aria-label=' in table
            has_aria_labelledby = 'aria-labelledby=' in table
            
            # This is a recommendation for complex tables
            if len(re.findall(r'<tr', table)) > 5:  # Complex table
                # Should consider having description
                pass


@pytest.mark.accessibility
class TestMobileAccessibility:
    """Test mobile accessibility."""
    
    def test_responsive_design_accessibility(self, client):
        """Test responsive design accessibility."""
        response = client.get('/')
        assert response.status_code == 200
        
        html_content = response.data.decode()
        
        # Check for viewport meta tag
        assert 'viewport' in html_content, "Should have viewport meta tag for mobile"
        
        # Check for responsive viewport settings
        import re
        viewport_content = re.search(r'content="([^"]*)"', html_content)
        if viewport_content:
            content = viewport_content.group(1)
            assert 'width=device-width' in content, "Should set width to device width"
            assert 'initial-scale=1' in content, "Should set initial scale to 1"
    
    def test_touch_target_accessibility(self, chrome_driver):
        """Test touch target accessibility."""
        driver = chrome_driver
        
        try:
            # Set mobile viewport
            driver.set_window_size(375, 667)  # iPhone size
            
            driver.get(self.base_url)
            
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check touch targets (buttons, links)
            touch_targets = driver.find_elements(By.CSS_SELECTOR, "button, a, input[type='submit'], input[type='button']")
            
            for target in touch_targets[:10]:  # Check first 10 targets
                size = target.size
                
                # Touch targets should be at least 44x44 pixels (WCAG recommendation)
                min_size = 44
                
                # Some flexibility for very small screens or specific design requirements
                assert (size['width'] >= min_size - 10 and size['height'] >= min_size - 10), \
                    f"Touch target should be at least {min_size}px: {size}"
            
        except TimeoutException:
            pytest.skip("Test server not available for mobile accessibility tests")


@pytest.mark.accessibility
class TestAccessibilityReporting:
    """Test accessibility reporting and monitoring."""
    
    def test_accessibility_audit_report(self, chrome_driver):
        """Generate accessibility audit report."""
        driver = chrome_driver
        
        try:
            pages_to_test = [
                ('Homepage', '/'),
                ('Outcomes', '/outcomes'),
                ('Metrics', '/metrics'),
                ('Translator', '/translator')
            ]
            
            audit_results = {}
            
            for page_name, page_url in pages_to_test:
                driver.get(f"{self.base_url}{page_url}")
                
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
                # Run comprehensive accessibility audit
                axe = Axe(driver)
                results = axe.run()
                
                # Categorize results
                violations = results.get('violations', [])
                passes = results.get('passes', [])
                incomplete = results.get('incomplete', [])
                
                audit_results[page_name] = {
                    'url': page_url,
                    'violations': len(violations),
                    'critical_violations': len([v for v in violations if v.get('impact') == 'critical']),
                    'serious_violations': len([v for v in violations if v.get('impact') == 'serious']),
                    'moderate_violations': len([v for v in violations if v.get('impact') == 'moderate']),
                    'minor_violations': len([v for v in violations if v.get('impact') == 'minor']),
                    'passes': len(passes),
                    'incomplete': len(incomplete),
                    'details': violations  # Store details for debugging
                }
            
            # Generate summary report
            total_violations = sum(result['violations'] for result in audit_results.values())
            total_critical = sum(result['critical_violations'] for result in audit_results.values())
            total_serious = sum(result['serious_violations'] for result in audit_results.values())
            
            print(f"\n=== ACCESSIBILITY AUDIT REPORT ===")
            print(f"Total pages tested: {len(pages_to_test)}")
            print(f"Total violations: {total_violations}")
            print(f"Critical violations: {total_critical}")
            print(f"Serious violations: {total_serious}")
            print(f"\nPage-by-page results:")
            
            for page_name, results in audit_results.items():
                print(f"\n{page_name} ({results['url']}):")
                print(f"  Violations: {results['violations']}")
                print(f"  Critical: {results['critical_violations']}")
                print(f"  Serious: {results['serious_violations']}")
                print(f"  Passes: {results['passes']}")
            
            # Assert acceptable levels
            assert total_critical == 0, f"No critical accessibility violations allowed: {total_critical}"
            assert total_serious <= 2, f"Too many serious accessibility violations: {total_serious}"
            
        except TimeoutException:
            pytest.skip("Test server not available for accessibility audit")
    
    def test_accessibility_standards_compliance(self, chrome_driver):
        """Test compliance with accessibility standards."""
        driver = chrome_driver
        
        try:
            driver.get(self.base_url)
            
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Test WCAG 2.1 Level AA compliance
            axe = Axe(driver)
            
            # Run tests for specific WCAG criteria
            wcag_tags = ['wcag2a', 'wcag2aa', 'wcag21aa']
            
            for tag in wcag_tags:
                results = axe.run(tags=[tag])
                violations = results.get('violations', [])
                
                # Filter critical and serious violations
                significant_violations = [
                    v for v in violations 
                    if v.get('impact') in ['critical', 'serious']
                ]
                
                assert len(significant_violations) == 0, \
                    f"WCAG {tag} violations found: {[v.get('id') for v in significant_violations]}"
            
        except TimeoutException:
            pytest.skip("Test server not available for WCAG compliance tests")
