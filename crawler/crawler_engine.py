import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import json
from typing import List, Dict, Tuple


class SmartCrawler:
    """Smart web crawler to extract links, status codes, and meta information"""

    def __init__(self, url: str, timeout: int = 10):
        self.url = url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def crawl(self) -> Dict:
        """Main crawl method that returns comprehensive page data"""
        start_time = time.time()

        try:
            response = self.session.get(self.url, timeout=self.timeout, allow_redirects=True)
            response_time = time.time() - start_time

            soup = BeautifulSoup(response.content, 'lxml')

            # Extract page info
            page_info = {
                'status_code': response.status_code,
                'title': self._extract_title(soup),
                'meta_description': self._extract_meta_description(soup),
                'content_type': response.headers.get('Content-Type', ''),
                'response_time': round(response_time, 2),
                'page_size': len(response.content),
                'html_structure': self._extract_html_structure(soup),
                'schema_markup': self._extract_schema_markup(soup),
            }

            # Extract links
            links = self._extract_links(soup)

            # Check link status codes (optional, can be resource-intensive)
            links_with_status = self._check_link_status(links)

            # Run Lighthouse-like performance audit
            lighthouse_score = self._run_lighthouse_audit(soup, response, response_time)

            return {
                'success': True,
                'page_info': {**page_info, 'lighthouse_score': lighthouse_score},
                'links': links_with_status,
                'total_links': len(links_with_status),
                'internal_links': len([l for l in links_with_status if l['link_type'] == 'internal']),
                'external_links': len([l for l in links_with_status if l['link_type'] == 'external']),
            }

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'page_info': None,
                'links': [],
                'total_links': 0,
                'internal_links': 0,
                'external_links': 0,
            }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        title_tag = soup.find('title')
        return title_tag.get_text(strip=True) if title_tag else ''

    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']
        return ''

    def _extract_html_structure(self, soup: BeautifulSoup) -> Dict:
        """Extract HTML semantic structure as a tree"""
        def build_tree(element, depth=0, max_depth=5):
            """Recursively build structure tree"""
            if depth > max_depth or not element or not hasattr(element, 'name'):
                return None

            # Only track semantic and important elements
            semantic_tags = ['html', 'head', 'body', 'header', 'footer', 'nav', 'main',
                           'section', 'article', 'aside', 'div']

            if element.name not in semantic_tags:
                return None

            # Build node info
            node = {
                'tag': element.name,
                'id': element.get('id', ''),
                'classes': element.get('class', []),
                'children': []
            }

            # Count direct children by type
            child_counts = {}
            for child in element.children:
                if hasattr(child, 'name') and child.name:
                    child_counts[child.name] = child_counts.get(child.name, 0) + 1

            node['child_counts'] = child_counts

            # Recursively process semantic children
            for child in element.children:
                if hasattr(child, 'name'):
                    child_node = build_tree(child, depth + 1, max_depth)
                    if child_node:
                        node['children'].append(child_node)

            return node

        # Start from body tag
        body = soup.find('body')
        if body:
            return build_tree(body, 0, 4)  # Limit depth to 4 levels
        return {}

    def _extract_schema_markup(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract JSON-LD schema markup from the page"""
        schemas = []

        # Find all script tags with type="application/ld+json"
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                # Parse JSON content
                schema_data = json.loads(script.string)
                schemas.append(schema_data)
            except (json.JSONDecodeError, TypeError, AttributeError):
                # Skip invalid JSON
                continue

        return schemas

    def _extract_links(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract all links from the page with parent element info"""
        links = []
        base_domain = urlparse(self.url).netloc

        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            full_url = urljoin(self.url, href)

            # Skip invalid URLs
            if not full_url.startswith(('http://', 'https://')):
                continue

            link_domain = urlparse(full_url).netloc
            link_type = 'internal' if link_domain == base_domain else 'external'

            # Find parent element (header, footer, nav, section, article, main, aside)
            parent_element = self._find_parent_element(anchor)

            links.append({
                'url': full_url,
                'link_type': link_type,
                'anchor_text': anchor.get_text(strip=True)[:500],
                'parent_element': parent_element,
            })

        return links

    def _find_parent_element(self, element) -> str:
        """Find the semantic parent element hierarchy of a link"""
        # List of semantic HTML elements to look for
        semantic_elements = ['header', 'footer', 'nav', 'main', 'section', 'article', 'aside']

        # Collect all parent semantic elements from innermost to outermost
        parents = []
        current = element.parent

        while current and current.name != 'body':
            if current.name in semantic_elements:
                # Add class or id if available for more context
                classes = current.get('class', [])
                element_id = current.get('id', '')

                if element_id:
                    parents.append(f"{current.name}#{element_id}")
                elif classes:
                    parents.append(f"{current.name}.{classes[0]}")
                else:
                    parents.append(current.name)
            current = current.parent

        # Return the full hierarchy path (outermost to innermost)
        if parents:
            return ' > '.join(reversed(parents))

        return 'body'

    def _check_link_status(self, links: List[Dict], max_checks: int = 50) -> List[Dict]:
        """Check status codes for links (limited to avoid long execution)"""
        for i, link in enumerate(links[:max_checks]):
            try:
                response = self.session.head(
                    link['url'],
                    timeout=5,
                    allow_redirects=True
                )
                link['status_code'] = response.status_code
                link['is_broken'] = response.status_code >= 400
            except requests.exceptions.RequestException:
                link['status_code'] = None
                link['is_broken'] = True

            # Small delay to avoid overwhelming servers
            time.sleep(0.1)

        # For remaining links, set status as None
        for link in links[max_checks:]:
            link['status_code'] = None
            link['is_broken'] = False

        return links

    def _run_lighthouse_audit(self, soup: BeautifulSoup, response, response_time: float) -> Dict:
        """Run Lighthouse-like performance audit"""
        try:
            # Performance metrics
            performance_score = self._calculate_performance_score(response_time, len(response.content))

            # Accessibility analysis
            accessibility_score = self._analyze_accessibility(soup)

            # Best Practices
            best_practices_score = self._analyze_best_practices(soup, response)

            # SEO analysis
            seo_score = self._analyze_seo(soup)

            # Calculate overall score (weighted average)
            overall_score = round(
                (performance_score * 0.3 +
                 accessibility_score * 0.25 +
                 best_practices_score * 0.25 +
                 seo_score * 0.2)
            )

            return {
                'overall': overall_score,
                'performance': performance_score,
                'accessibility': accessibility_score,
                'best_practices': best_practices_score,
                'seo': seo_score,
                'metrics': {
                    'response_time': round(response_time * 1000),  # Convert to ms
                    'page_size_kb': round(len(response.content) / 1024, 2),
                    'dom_size': len(soup.find_all()),
                },
                'audits': self._get_audit_details(soup, response, response_time)
            }
        except Exception as e:
            return {
                'overall': 0,
                'performance': 0,
                'accessibility': 0,
                'best_practices': 0,
                'seo': 0,
                'metrics': {},
                'audits': {'error': str(e)}
            }

    def _calculate_performance_score(self, response_time: float, page_size: int) -> int:
        """Calculate performance score based on response time and page size"""
        score = 100

        # Response time scoring (in seconds)
        if response_time > 3:
            score -= 40
        elif response_time > 2:
            score -= 30
        elif response_time > 1:
            score -= 20
        elif response_time > 0.5:
            score -= 10

        # Page size scoring (in MB)
        size_mb = page_size / (1024 * 1024)
        if size_mb > 5:
            score -= 30
        elif size_mb > 3:
            score -= 20
        elif size_mb > 1:
            score -= 10

        return max(0, score)

    def _analyze_accessibility(self, soup: BeautifulSoup) -> int:
        """Analyze accessibility features"""
        score = 100
        issues = []

        # Check for alt attributes on images
        images = soup.find_all('img')
        images_without_alt = [img for img in images if not img.get('alt')]
        if images:
            alt_ratio = 1 - (len(images_without_alt) / len(images))
            score = int(score * (0.5 + 0.5 * alt_ratio))

        # Check for proper heading hierarchy
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        h1_count = len(soup.find_all('h1'))
        if h1_count == 0:
            score -= 15
        elif h1_count > 1:
            score -= 10

        # Check for form labels
        inputs = soup.find_all('input', type=['text', 'email', 'password', 'tel'])
        for input_field in inputs:
            input_id = input_field.get('id')
            if input_id:
                label = soup.find('label', attrs={'for': input_id})
                if not label:
                    score -= 5

        # Check for ARIA attributes
        aria_elements = soup.find_all(attrs={'role': True})
        if len(aria_elements) > 0:
            score = min(100, score + 5)

        return max(0, min(100, score))

    def _analyze_best_practices(self, soup: BeautifulSoup, response) -> int:
        """Analyze best practices"""
        score = 100

        # Check HTTPS
        if not self.url.startswith('https://'):
            score -= 20

        # Check for meta viewport
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if not viewport:
            score -= 15

        # Check for doctype
        if not str(soup).strip().lower().startswith('<!doctype'):
            score -= 10

        # Check for charset
        charset = soup.find('meta', charset=True) or soup.find('meta', attrs={'http-equiv': 'Content-Type'})
        if not charset:
            score -= 10

        # Check for security headers
        security_headers = ['X-Content-Type-Options', 'X-Frame-Options', 'Strict-Transport-Security']
        for header in security_headers:
            if header not in response.headers:
                score -= 5

        # Check for external resources over HTTP
        http_resources = soup.find_all(['script', 'link', 'img'], src=lambda x: x and x.startswith('http://'))
        if http_resources:
            score -= min(20, len(http_resources) * 2)

        return max(0, score)

    def _analyze_seo(self, soup: BeautifulSoup) -> int:
        """Analyze SEO factors"""
        score = 100

        # Check for title
        title = soup.find('title')
        if not title or not title.get_text(strip=True):
            score -= 20
        elif len(title.get_text(strip=True)) < 30 or len(title.get_text(strip=True)) > 60:
            score -= 10

        # Check for meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc or not meta_desc.get('content'):
            score -= 20
        elif len(meta_desc.get('content', '')) < 120 or len(meta_desc.get('content', '')) > 160:
            score -= 10

        # Check for h1
        h1 = soup.find('h1')
        if not h1:
            score -= 15

        # Check for canonical URL
        canonical = soup.find('link', rel='canonical')
        if not canonical:
            score -= 10

        # Check for robots meta
        robots = soup.find('meta', attrs={'name': 'robots'})
        if robots and 'noindex' in robots.get('content', '').lower():
            score -= 15

        # Check for structured data
        structured_data = soup.find_all('script', type='application/ld+json')
        if structured_data:
            score = min(100, score + 10)

        return max(0, score)

    def _get_audit_details(self, soup: BeautifulSoup, response, response_time: float) -> List[Dict]:
        """Get detailed audit information"""
        audits = []

        # Performance audits
        if response_time > 1:
            audits.append({
                'category': 'performance',
                'title': 'Server Response Time',
                'description': f'Response time is {round(response_time, 2)}s. Aim for under 600ms.',
                'score': 'warning' if response_time < 3 else 'error'
            })

        # Accessibility audits
        images = soup.find_all('img')
        images_without_alt = [img for img in images if not img.get('alt')]
        if images_without_alt:
            audits.append({
                'category': 'accessibility',
                'title': 'Image Alt Attributes',
                'description': f'{len(images_without_alt)} images missing alt attributes.',
                'score': 'warning'
            })

        # SEO audits
        title = soup.find('title')
        if not title or not title.get_text(strip=True):
            audits.append({
                'category': 'seo',
                'title': 'Document Title',
                'description': 'The page is missing a title tag.',
                'score': 'error'
            })

        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc or not meta_desc.get('content'):
            audits.append({
                'category': 'seo',
                'title': 'Meta Description',
                'description': 'The page is missing a meta description.',
                'score': 'error'
            })

        # Best practices audits
        if not self.url.startswith('https://'):
            audits.append({
                'category': 'best_practices',
                'title': 'HTTPS Usage',
                'description': 'The page is not served over HTTPS.',
                'score': 'error'
            })

        return audits
