"""
Web Scraper - Extract additional business info from websites
Includes email extraction, social media links, and content analysis
"""
import asyncio
import re
from typing import List, Optional, Set, Dict, Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from .base_scraper import BaseScraper, ScrapedBusiness


class WebScraper(BaseScraper):
    """
    Scraper for extracting business information from websites

    Features:
    - Email extraction
    - Social media link detection
    - Contact page scraping
    - Service/product extraction
    """

    # Common contact page paths
    CONTACT_PATHS = [
        "/contact", "/lien-he", "/lien-he/", "/contact-us",
        "/about", "/gioi-thieu", "/ve-chung-toi",
        "/footer", "/thong-tin-lien-he"
    ]

    # Email regex pattern
    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )

    # Vietnamese phone patterns
    PHONE_PATTERNS = [
        re.compile(r'(?:0|\+84|84)(?:\s*\.?\-?\s*)?\d{2,3}(?:\s*\.?\-?\s*)?\d{3}(?:\s*\.?\-?\s*)?\d{3,4}'),
        re.compile(r'\d{4}[\s\.\-]?\d{3}[\s\.\-]?\d{3}'),
    ]

    # Social media patterns
    SOCIAL_PATTERNS = {
        'facebook': re.compile(r'(?:https?://)?(?:www\.)?facebook\.com/[a-zA-Z0-9.]+/?', re.IGNORECASE),
        'instagram': re.compile(r'(?:https?://)?(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+/?', re.IGNORECASE),
        'zalo': re.compile(r'(?:https?://)?(?:zalo\.me|chat\.zalo\.me)/[a-zA-Z0-9]+/?', re.IGNORECASE),
        'tiktok': re.compile(r'(?:https?://)?(?:www\.)?tiktok\.com/@[a-zA-Z0-9_.]+/?', re.IGNORECASE),
        'youtube': re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/(?:c/|channel/|@)?[a-zA-Z0-9_-]+/?', re.IGNORECASE),
    }

    def __init__(self, delay_seconds: int = 2):
        super().__init__(delay_seconds)
        self.client = httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
            }
        )
        self.visited_urls: Set[str] = set()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def search(
        self,
        keyword: str,
        location: str,
        max_results: int = 50
    ) -> List[ScrapedBusiness]:
        """
        Web scraper doesn't do primary search - use Google Maps for that
        This method is here to satisfy the abstract interface
        """
        logger.info("WebScraper is for enrichment, not primary search. Use GoogleMapsScraper.")
        return []

    async def get_business_details(
        self,
        business: ScrapedBusiness
    ) -> ScrapedBusiness:
        """
        Enrich business data by scraping their website

        Args:
            business: Business with website URL

        Returns:
            Enriched business data
        """
        if not business.website:
            logger.debug(f"No website for {business.name}, skipping web scrape")
            return business

        logger.info(f"Scraping website for: {business.name}")

        try:
            # Scrape main page
            html = await self._fetch_page(business.website)
            if html:
                business = await self._extract_info_from_html(business, html, business.website)

            # Try contact page
            for path in self.CONTACT_PATHS:
                contact_url = urljoin(business.website, path)
                if contact_url not in self.visited_urls:
                    contact_html = await self._fetch_page(contact_url)
                    if contact_html:
                        business = await self._extract_info_from_html(
                            business, contact_html, contact_url
                        )
                        break  # Stop after finding contact page

            await asyncio.sleep(self.delay_seconds)

        except Exception as e:
            logger.error(f"Error scraping {business.website}: {e}")

        return business

    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a webpage and return HTML content"""
        if url in self.visited_urls:
            return None

        self.visited_urls.add(url)

        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Got status {response.status_code} for {url}")
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")

        return None

    async def _extract_info_from_html(
        self,
        business: ScrapedBusiness,
        html: str,
        url: str
    ) -> ScrapedBusiness:
        """Extract business information from HTML"""
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style', 'noscript']):
            element.decompose()

        text_content = soup.get_text(separator=' ', strip=True)

        # Extract emails
        if not business.email:
            emails = self._extract_emails(text_content, html)
            if emails:
                business.email = emails[0]  # Take first valid email

        # Extract phones
        if not business.phone:
            phones = self._extract_phones(text_content)
            if phones:
                business.phone = self.normalize_phone(phones[0])

        # Extract social media links
        business = self._extract_social_media(business, html)

        # Extract description
        if not business.description:
            business.description = self._extract_description(soup)

        # Extract services/products
        if not business.services:
            business.services = self._extract_services(soup, text_content)

        return business

    def _extract_emails(self, text: str, html: str) -> List[str]:
        """Extract valid email addresses"""
        # Find all potential emails
        emails = set(self.EMAIL_PATTERN.findall(text))
        emails.update(self.EMAIL_PATTERN.findall(html))

        # Filter out invalid emails
        valid_emails = []
        invalid_patterns = [
            'example.com', 'domain.com', 'email.com', 'test.com',
            'yoursite.com', 'website.com', 'company.com',
            '.png', '.jpg', '.gif', '.css', '.js'
        ]

        for email in emails:
            email_lower = email.lower()
            if not any(pattern in email_lower for pattern in invalid_patterns):
                # Additional validation
                if self._is_valid_email(email):
                    valid_emails.append(email)

        return valid_emails

    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        if len(email) < 6 or len(email) > 100:
            return False

        # Check for common spam traps
        spam_indicators = ['noreply', 'no-reply', 'donotreply', 'mailer-daemon']
        if any(ind in email.lower() for ind in spam_indicators):
            return False

        return True

    def _extract_phones(self, text: str) -> List[str]:
        """Extract Vietnamese phone numbers"""
        phones = []
        for pattern in self.PHONE_PATTERNS:
            matches = pattern.findall(text)
            phones.extend(matches)

        # Clean and deduplicate
        cleaned = []
        seen = set()
        for phone in phones:
            normalized = self.normalize_phone(phone)
            if normalized and normalized not in seen:
                seen.add(normalized)
                cleaned.append(normalized)

        return cleaned

    def _extract_social_media(
        self,
        business: ScrapedBusiness,
        html: str
    ) -> ScrapedBusiness:
        """Extract social media links from HTML"""
        soup = BeautifulSoup(html, 'html.parser')

        # Find all links
        links = soup.find_all('a', href=True)

        for link in links:
            href = link.get('href', '')

            # Facebook
            if not business.facebook_url:
                match = self.SOCIAL_PATTERNS['facebook'].search(href)
                if match:
                    business.facebook_url = match.group(0)

            # Instagram
            if not business.instagram_url:
                match = self.SOCIAL_PATTERNS['instagram'].search(href)
                if match:
                    business.instagram_url = match.group(0)

            # Zalo
            if not business.zalo_url:
                match = self.SOCIAL_PATTERNS['zalo'].search(href)
                if match:
                    business.zalo_url = match.group(0)

        return business

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract business description from meta tags or content"""
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'][:500]

        # Try OG description
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            return og_desc['content'][:500]

        # Try first paragraph in main content
        for tag in ['main', 'article', 'div']:
            main = soup.find(tag, class_=re.compile(r'content|main|about', re.I))
            if main:
                para = main.find('p')
                if para and len(para.get_text(strip=True)) > 50:
                    return para.get_text(strip=True)[:500]

        return None

    def _extract_services(
        self,
        soup: BeautifulSoup,
        text: str
    ) -> List[str]:
        """Extract services/products offered"""
        services = []

        # Look for service-related sections
        service_keywords = [
            'dịch vụ', 'service', 'sản phẩm', 'product',
            'menu', 'bảng giá', 'price list'
        ]

        # Find elements with service-related classes or IDs
        for keyword in service_keywords:
            elements = soup.find_all(
                ['div', 'section', 'ul'],
                class_=re.compile(keyword, re.I)
            )
            for element in elements:
                items = element.find_all(['li', 'h3', 'h4', 'span'])
                for item in items[:10]:  # Limit items
                    text = item.get_text(strip=True)
                    if 10 < len(text) < 100:
                        services.append(text)

        # Deduplicate while preserving order
        seen = set()
        unique_services = []
        for service in services:
            if service.lower() not in seen:
                seen.add(service.lower())
                unique_services.append(service)

        return unique_services[:10]  # Limit to 10 services

    async def batch_enrich(
        self,
        businesses: List[ScrapedBusiness],
        concurrency: int = 3
    ) -> List[ScrapedBusiness]:
        """
        Enrich multiple businesses with concurrency control

        Args:
            businesses: List of businesses to enrich
            concurrency: Max concurrent requests

        Returns:
            List of enriched businesses
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def enrich_with_limit(business: ScrapedBusiness) -> ScrapedBusiness:
            async with semaphore:
                return await self.get_business_details(business)

        tasks = [enrich_with_limit(b) for b in businesses]
        enriched = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for i, result in enumerate(enriched):
            if isinstance(result, Exception):
                logger.error(f"Error enriching {businesses[i].name}: {result}")
                results.append(businesses[i])
            else:
                results.append(result)

        return results

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
