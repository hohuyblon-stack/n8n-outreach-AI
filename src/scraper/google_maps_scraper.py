"""
Google Maps Scraper - Collect business data from Google Maps
Supports both API and web scraping methods
"""
import asyncio
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

import httpx
from loguru import logger

from .base_scraper import BaseScraper, ScrapedBusiness


class GoogleMapsScraper(BaseScraper):
    """
    Scraper for Google Maps business data

    Can use either:
    1. Google Places API (recommended, requires API key)
    2. Web scraping as fallback (rate limited)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        delay_seconds: int = 2,
        use_api: bool = True
    ):
        super().__init__(delay_seconds)
        self.api_key = api_key
        self.use_api = use_api and api_key is not None
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        self.client = httpx.AsyncClient(timeout=30.0)

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
        Search for businesses on Google Maps

        Args:
            keyword: Business type (e.g., "spa", "nha khoa")
            location: Location (e.g., "TP.HCM", "Quận 1 Hồ Chí Minh")
            max_results: Maximum results to return

        Returns:
            List of ScrapedBusiness objects
        """
        logger.info(f"Searching for '{keyword}' in '{location}' (max: {max_results})")

        if self.use_api:
            return await self._search_with_api(keyword, location, max_results)
        else:
            return await self._search_with_scraping(keyword, location, max_results)

    async def _search_with_api(
        self,
        keyword: str,
        location: str,
        max_results: int
    ) -> List[ScrapedBusiness]:
        """Search using Google Places API"""
        businesses = []
        query = f"{keyword} {location}"

        try:
            # Text Search API
            url = f"{self.base_url}/textsearch/json"
            params = {
                "query": query,
                "key": self.api_key,
                "language": "vi",
                "region": "vn"
            }

            next_page_token = None
            while len(businesses) < max_results:
                if next_page_token:
                    params["pagetoken"] = next_page_token
                    await asyncio.sleep(2)  # Required delay for page token

                response = await self.client.get(url, params=params)
                data = response.json()

                if data.get("status") != "OK":
                    logger.warning(f"API returned status: {data.get('status')}")
                    break

                for result in data.get("results", []):
                    if len(businesses) >= max_results:
                        break

                    business = self._parse_api_result(result)
                    business.industry = keyword
                    businesses.append(business)
                    self.scraped_count += 1

                next_page_token = data.get("next_page_token")
                if not next_page_token:
                    break

                await asyncio.sleep(self.delay_seconds)

        except Exception as e:
            logger.error(f"API search error: {e}")

        logger.info(f"Found {len(businesses)} businesses via API")
        return businesses

    def _parse_api_result(self, result: Dict[str, Any]) -> ScrapedBusiness:
        """Parse Google Places API result into ScrapedBusiness"""
        # Extract location
        geometry = result.get("geometry", {}).get("location", {})

        # Extract photos
        photos = result.get("photos", [])
        photo_urls = []
        for photo in photos[:5]:  # Limit to 5 photos
            if self.api_key and photo.get("photo_reference"):
                photo_url = (
                    f"{self.base_url}/photo?"
                    f"maxwidth=800&"
                    f"photo_reference={photo['photo_reference']}&"
                    f"key={self.api_key}"
                )
                photo_urls.append(photo_url)

        address = result.get("formatted_address", "")

        return ScrapedBusiness(
            name=result.get("name", "Unknown"),
            address=address,
            city=self.extract_city(address),
            district=self.extract_district(address),
            latitude=geometry.get("lat"),
            longitude=geometry.get("lng"),
            rating=result.get("rating"),
            review_count=result.get("user_ratings_total"),
            category=", ".join(result.get("types", [])[:3]),
            google_maps_url=f"https://www.google.com/maps/place/?q=place_id:{result.get('place_id')}",
            photo_urls=photo_urls,
            opening_hours={"status": "open" if result.get("opening_hours", {}).get("open_now") else "closed"},
            is_open_now=result.get("opening_hours", {}).get("open_now"),
            source="google_maps_api",
            scraped_at=datetime.now()
        )

    async def get_business_details(
        self,
        business: ScrapedBusiness
    ) -> ScrapedBusiness:
        """
        Get detailed information for a business using Place Details API
        """
        if not self.use_api:
            return await self._get_details_with_scraping(business)

        # Extract place_id from URL
        place_id = None
        if business.google_maps_url:
            match = re.search(r"place_id:([^&\s]+)", business.google_maps_url)
            if match:
                place_id = match.group(1)

        if not place_id:
            logger.warning(f"No place_id found for {business.name}")
            return business

        try:
            url = f"{self.base_url}/details/json"
            params = {
                "place_id": place_id,
                "key": self.api_key,
                "language": "vi",
                "fields": (
                    "name,formatted_address,formatted_phone_number,"
                    "international_phone_number,website,url,rating,"
                    "user_ratings_total,reviews,opening_hours,photos,"
                    "types,business_status"
                )
            }

            response = await self.client.get(url, params=params)
            data = response.json()

            if data.get("status") == "OK":
                result = data.get("result", {})
                business = self._enrich_from_details(business, result)

            await asyncio.sleep(self.delay_seconds)

        except Exception as e:
            logger.error(f"Error getting details for {business.name}: {e}")

        return business

    def _enrich_from_details(
        self,
        business: ScrapedBusiness,
        details: Dict[str, Any]
    ) -> ScrapedBusiness:
        """Enrich business with Place Details data"""
        # Phone number
        business.phone = self.normalize_phone(
            details.get("formatted_phone_number") or
            details.get("international_phone_number")
        )

        # Website
        business.website = details.get("website")

        # Extract social media from website
        if business.website:
            business = self._extract_social_from_website(business)

        # Reviews
        reviews = details.get("reviews", [])
        business.reviews = [
            {
                "author": r.get("author_name"),
                "rating": r.get("rating"),
                "text": r.get("text"),
                "time": r.get("relative_time_description")
            }
            for r in reviews[:5]
        ]

        # Opening hours
        if details.get("opening_hours"):
            hours = details["opening_hours"]
            business.opening_hours = {
                "weekday_text": hours.get("weekday_text", []),
                "open_now": hours.get("open_now")
            }
            business.is_open_now = hours.get("open_now")

        # Update rating if available
        if details.get("rating"):
            business.rating = details["rating"]
        if details.get("user_ratings_total"):
            business.review_count = details["user_ratings_total"]

        # Google Maps URL
        if details.get("url"):
            business.google_maps_url = details["url"]

        return business

    def _extract_social_from_website(
        self,
        business: ScrapedBusiness
    ) -> ScrapedBusiness:
        """Extract social media links from website URL patterns"""
        website = business.website.lower() if business.website else ""

        # Check if website itself is a social media page
        if "facebook.com" in website:
            business.facebook_url = business.website
        elif "instagram.com" in website:
            business.instagram_url = business.website

        return business

    async def _search_with_scraping(
        self,
        keyword: str,
        location: str,
        max_results: int
    ) -> List[ScrapedBusiness]:
        """
        Fallback web scraping method when API is not available

        Note: This is a simplified implementation. In production,
        you would use Selenium or Playwright for full scraping.
        """
        logger.warning("Using web scraping fallback - limited functionality")
        businesses = []

        # This is a placeholder - actual implementation would require
        # browser automation (Selenium/Playwright) due to Google's
        # JavaScript-heavy interface

        # For demonstration, we'll create mock data structure
        # In production, replace with actual scraping logic

        query = f"{keyword} {location}"
        logger.info(f"Would scrape Google Maps for: {query}")

        return businesses

    async def _get_details_with_scraping(
        self,
        business: ScrapedBusiness
    ) -> ScrapedBusiness:
        """Fallback for getting details via scraping"""
        # Placeholder for scraping implementation
        return business

    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        keyword: str,
        radius_meters: int = 5000,
        max_results: int = 20
    ) -> List[ScrapedBusiness]:
        """
        Search for businesses near a specific location

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            keyword: Business type keyword
            radius_meters: Search radius in meters
            max_results: Maximum results

        Returns:
            List of nearby businesses
        """
        if not self.use_api:
            logger.warning("Nearby search requires API key")
            return []

        businesses = []

        try:
            url = f"{self.base_url}/nearbysearch/json"
            params = {
                "location": f"{latitude},{longitude}",
                "radius": radius_meters,
                "keyword": keyword,
                "key": self.api_key,
                "language": "vi"
            }

            response = await self.client.get(url, params=params)
            data = response.json()

            if data.get("status") == "OK":
                for result in data.get("results", [])[:max_results]:
                    business = self._parse_api_result(result)
                    business.industry = keyword
                    businesses.append(business)

        except Exception as e:
            logger.error(f"Nearby search error: {e}")

        return businesses

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
