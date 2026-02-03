"""
Base Scraper - Abstract base class for all scrapers
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import hashlib


class BusinessStatus(Enum):
    """Status of the scraped business"""
    NEW = "new"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    NOT_INTERESTED = "not_interested"
    CONVERTED = "converted"


@dataclass
class ScrapedBusiness:
    """Data model for a scraped business"""
    # Basic Info
    name: str
    address: str
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

    # Location
    city: Optional[str] = None
    district: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Business Details
    industry: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    services: List[str] = field(default_factory=list)
    products: List[str] = field(default_factory=list)

    # Online Presence
    google_maps_url: Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    zalo_url: Optional[str] = None

    # Reviews & Ratings
    rating: Optional[float] = None
    review_count: Optional[int] = None
    reviews: List[Dict[str, Any]] = field(default_factory=list)

    # Business Hours
    opening_hours: Optional[Dict[str, str]] = None
    is_open_now: Optional[bool] = None

    # Photos
    photo_urls: List[str] = field(default_factory=list)

    # Metadata
    source: str = "unknown"
    scraped_at: datetime = field(default_factory=datetime.now)
    status: BusinessStatus = BusinessStatus.NEW

    # Contact tracking
    contact_attempts: int = 0
    last_contacted: Optional[datetime] = None
    notes: List[str] = field(default_factory=list)

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on name and address"""
        raw = f"{self.name}_{self.address}".lower().strip()
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    @property
    def has_website(self) -> bool:
        return bool(self.website)

    @property
    def has_social_media(self) -> bool:
        return any([self.facebook_url, self.instagram_url, self.zalo_url])

    @property
    def has_contact_info(self) -> bool:
        return bool(self.phone or self.email)

    @property
    def digital_maturity_score(self) -> int:
        """
        Score from 0-100 indicating digital presence maturity
        Higher score = more digitally mature
        """
        score = 0

        # Website presence (max 30 points)
        if self.website:
            score += 30

        # Social media presence (max 30 points)
        if self.facebook_url:
            score += 15
        if self.instagram_url:
            score += 10
        if self.zalo_url:
            score += 5

        # Reviews indicate online engagement (max 20 points)
        if self.review_count:
            if self.review_count > 100:
                score += 20
            elif self.review_count > 50:
                score += 15
            elif self.review_count > 10:
                score += 10
            else:
                score += 5

        # High rating indicates quality (max 10 points)
        if self.rating:
            if self.rating >= 4.5:
                score += 10
            elif self.rating >= 4.0:
                score += 7
            elif self.rating >= 3.5:
                score += 5

        # Has photos (max 10 points)
        if self.photo_urls:
            score += min(10, len(self.photo_urls) * 2)

        return min(100, score)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "unique_id": self.unique_id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "city": self.city,
            "district": self.district,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "industry": self.industry,
            "category": self.category,
            "description": self.description,
            "services": self.services,
            "products": self.products,
            "google_maps_url": self.google_maps_url,
            "facebook_url": self.facebook_url,
            "instagram_url": self.instagram_url,
            "zalo_url": self.zalo_url,
            "rating": self.rating,
            "review_count": self.review_count,
            "reviews": self.reviews,
            "opening_hours": self.opening_hours,
            "photo_urls": self.photo_urls,
            "source": self.source,
            "scraped_at": self.scraped_at.isoformat(),
            "status": self.status.value,
            "contact_attempts": self.contact_attempts,
            "last_contacted": self.last_contacted.isoformat() if self.last_contacted else None,
            "digital_maturity_score": self.digital_maturity_score,
            "notes": self.notes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScrapedBusiness":
        """Create instance from dictionary"""
        # Handle datetime conversion
        if isinstance(data.get("scraped_at"), str):
            data["scraped_at"] = datetime.fromisoformat(data["scraped_at"])
        if data.get("last_contacted") and isinstance(data["last_contacted"], str):
            data["last_contacted"] = datetime.fromisoformat(data["last_contacted"])
        if data.get("status") and isinstance(data["status"], str):
            data["status"] = BusinessStatus(data["status"])

        # Remove computed fields
        data.pop("unique_id", None)
        data.pop("digital_maturity_score", None)

        return cls(**data)


class BaseScraper(ABC):
    """Abstract base class for all scrapers"""

    def __init__(self, delay_seconds: int = 2):
        self.delay_seconds = delay_seconds
        self.scraped_count = 0

    @abstractmethod
    async def search(
        self,
        keyword: str,
        location: str,
        max_results: int = 50
    ) -> List[ScrapedBusiness]:
        """
        Search for businesses matching keyword and location

        Args:
            keyword: Business type/industry keyword (e.g., "spa", "cafe")
            location: Geographic location (e.g., "TP.HCM", "Quận 1")
            max_results: Maximum number of results to return

        Returns:
            List of ScrapedBusiness objects
        """
        pass

    @abstractmethod
    async def get_business_details(
        self,
        business: ScrapedBusiness
    ) -> ScrapedBusiness:
        """
        Get detailed information for a specific business

        Args:
            business: Basic business info

        Returns:
            Business with enriched details
        """
        pass

    def normalize_phone(self, phone: Optional[str]) -> Optional[str]:
        """Normalize Vietnamese phone number"""
        if not phone:
            return None

        # Remove all non-digits
        digits = "".join(c for c in phone if c.isdigit())

        # Handle different formats
        if digits.startswith("84"):
            digits = "0" + digits[2:]
        elif digits.startswith("+84"):
            digits = "0" + digits[3:]

        # Validate length
        if len(digits) < 9 or len(digits) > 11:
            return None

        return digits

    def extract_district(self, address: str) -> Optional[str]:
        """Extract district from Vietnamese address"""
        import re

        # Common patterns for districts
        patterns = [
            r"Quận\s*(\d+)",
            r"Q\.?\s*(\d+)",
            r"Quận\s+([A-Za-zÀ-ỹ\s]+)",
            r"Huyện\s+([A-Za-zÀ-ỹ\s]+)",
            r"Thành phố\s+([A-Za-zÀ-ỹ\s]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def extract_city(self, address: str) -> Optional[str]:
        """Extract city from Vietnamese address"""
        # Common city names
        cities = [
            "Hồ Chí Minh", "HCM", "TP.HCM", "Sài Gòn",
            "Hà Nội", "Đà Nẵng", "Cần Thơ", "Hải Phòng",
            "Biên Hòa", "Nha Trang", "Huế", "Đà Lạt",
            "Vũng Tàu", "Quy Nhơn", "Buôn Ma Thuột"
        ]

        address_lower = address.lower()
        for city in cities:
            if city.lower() in address_lower:
                # Normalize common variations
                if city in ["HCM", "TP.HCM", "Sài Gòn"]:
                    return "Hồ Chí Minh"
                return city

        return None
