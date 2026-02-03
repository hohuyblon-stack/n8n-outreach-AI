"""
Business Analyzer - Analyze business data to identify opportunities and pain points
Uses AI for intelligent analysis and lead scoring
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import json

from loguru import logger

from src.scraper.base_scraper import ScrapedBusiness


class LeadQuality(Enum):
    """Lead quality classification"""
    HOT = "hot"           # High priority, likely to convert
    WARM = "warm"         # Good potential, needs nurturing
    COLD = "cold"         # Low priority, long-term prospect
    UNQUALIFIED = "unqualified"  # Not a good fit


class DigitalMaturity(Enum):
    """Digital presence maturity level"""
    ADVANCED = "advanced"    # Strong online presence
    MODERATE = "moderate"    # Some online presence
    BASIC = "basic"          # Minimal online presence
    NONE = "none"            # No online presence


@dataclass
class BusinessAnalysis:
    """Analysis result for a business"""
    # Basic scoring
    lead_score: int  # 0-100
    lead_quality: LeadQuality
    digital_maturity: DigitalMaturity

    # Identified issues
    pain_points: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)

    # Recommendations
    recommended_services: List[str] = field(default_factory=list)
    personalization_hooks: List[str] = field(default_factory=list)

    # Contact strategy
    best_channel: str = "email"  # email, phone, facebook, etc.
    urgency_level: str = "medium"  # low, medium, high
    recommended_offer: str = ""

    # Analysis notes
    summary: str = ""
    detailed_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lead_score": self.lead_score,
            "lead_quality": self.lead_quality.value,
            "digital_maturity": self.digital_maturity.value,
            "pain_points": self.pain_points,
            "opportunities": self.opportunities,
            "recommended_services": self.recommended_services,
            "personalization_hooks": self.personalization_hooks,
            "best_channel": self.best_channel,
            "urgency_level": self.urgency_level,
            "recommended_offer": self.recommended_offer,
            "summary": self.summary,
            "detailed_notes": self.detailed_notes
        }


class BusinessAnalyzer:
    """
    Analyze businesses to determine lead quality and personalization opportunities

    Features:
    - Lead scoring based on multiple factors
    - Pain point identification by industry
    - Personalization hook generation
    - Channel recommendation
    """

    # Industry-specific analysis rules
    INDUSTRY_ANALYSIS = {
        "spa": {
            "pain_points": {
                "no_website": "Không có website chuyên nghiệp để showcase dịch vụ và đặt lịch online",
                "low_reviews": "Ít đánh giá trực tuyến, khó xây dựng uy tín",
                "no_social": "Thiếu kênh social media để tiếp cận khách hàng trẻ",
                "no_booking": "Chưa có hệ thống đặt lịch online, mất khách ngoài giờ",
                "low_visibility": "Khả năng hiển thị trên Google thấp"
            },
            "opportunities": {
                "digital_booking": "Triển khai hệ thống đặt lịch online 24/7",
                "loyalty_program": "Xây dựng chương trình khách hàng thân thiết",
                "social_marketing": "Marketing qua Instagram/TikTok với nội dung before/after",
                "google_ads": "Chạy quảng cáo Google Maps cho khách hàng tìm kiếm gần đó",
                "review_campaign": "Chiến dịch thu thập review từ khách hàng hài lòng"
            },
            "recommended_services": [
                "Thiết kế website + tích hợp đặt lịch",
                "Quản lý Google Business Profile",
                "Marketing Instagram/TikTok",
                "Chạy quảng cáo Google/Facebook"
            ],
            "offers": [
                "Miễn phí setup Google Business Profile + tối ưu SEO địa phương",
                "Tặng 1 tháng chạy quảng cáo nếu không tăng ít nhất 20% khách đặt lịch",
                "Dùng thử 14 ngày hệ thống đặt lịch online"
            ]
        },
        "cafe": {
            "pain_points": {
                "no_website": "Chưa có kênh order online/delivery",
                "low_reviews": "Review thấp ảnh hưởng đến quyết định của khách mới",
                "no_social": "Thiếu community building trên social media",
                "no_loyalty": "Không có chương trình tích điểm, khách không quay lại",
                "low_visibility": "Khó cạnh tranh với các chuỗi lớn về mặt digital"
            },
            "opportunities": {
                "delivery_integration": "Tích hợp đặt hàng online và delivery",
                "loyalty_app": "App tích điểm/voucher cho khách quen",
                "instagram_marketing": "Content marketing về không gian và đồ uống",
                "event_marketing": "Tổ chức events/workshops để tạo community",
                "local_seo": "Tối ưu Google Maps để xuất hiện khi khách tìm café gần đây"
            },
            "recommended_services": [
                "Menu digital + đặt hàng online",
                "Marketing Instagram với content chất lượng",
                "Chương trình loyalty qua Zalo OA",
                "Quảng cáo Facebook/Instagram local"
            ],
            "offers": [
                "Miễn phí thiết kế menu digital + QR code",
                "1 tuần content Instagram miễn phí để demo",
                "Setup Zalo OA + mini program miễn phí"
            ]
        },
        "nha_khoa": {
            "pain_points": {
                "no_website": "Website không chuyên nghiệp, không tạo được niềm tin",
                "low_reviews": "Thiếu social proof từ bệnh nhân cũ",
                "no_social": "Không có kênh giáo dục khách hàng về chăm sóc răng",
                "trust_issue": "Bệnh nhân lo ngại về chất lượng và chi phí",
                "appointment": "Quản lý lịch hẹn thủ công, dễ trùng hoặc quên"
            },
            "opportunities": {
                "professional_website": "Website chuyên nghiệp với giới thiệu bác sĩ và công nghệ",
                "patient_education": "Content marketing giáo dục về sức khỏe răng miệng",
                "before_after": "Showcase kết quả điều trị (with consent)",
                "easy_booking": "Đặt lịch online + nhắc nhở tự động",
                "payment_plan": "Giới thiệu gói trả góp để giảm rào cản chi phí"
            },
            "recommended_services": [
                "Thiết kế website y tế chuyên nghiệp",
                "SEO cho từ khóa nha khoa",
                "Hệ thống CRM + nhắc lịch tái khám",
                "Google Ads cho dịch vụ nha khoa"
            ],
            "offers": [
                "Audit website miễn phí + báo cáo cải thiện",
                "Setup hệ thống nhắc lịch tự động miễn phí 1 tháng",
                "Cam kết tăng 30% bệnh nhân mới hoặc hoàn tiền"
            ]
        },
        "default": {
            "pain_points": {
                "no_website": "Chưa có hoặc website chưa tối ưu cho chuyển đổi",
                "low_reviews": "Thiếu đánh giá trực tuyến từ khách hàng",
                "no_social": "Chưa tận dụng được social media marketing",
                "low_visibility": "Khó khăn trong việc tiếp cận khách hàng online",
                "no_data": "Không có dữ liệu để đo lường hiệu quả marketing"
            },
            "opportunities": {
                "digital_presence": "Xây dựng hiện diện digital chuyên nghiệp",
                "lead_generation": "Tự động hóa thu thập khách hàng tiềm năng",
                "automation": "Tự động hóa các quy trình marketing",
                "analytics": "Thiết lập hệ thống đo lường và báo cáo",
                "content_marketing": "Xây dựng nội dung thu hút khách hàng"
            },
            "recommended_services": [
                "Thiết kế website/landing page",
                "SEO & Content Marketing",
                "Quảng cáo Google/Facebook",
                "Email Marketing Automation"
            ],
            "offers": [
                "Tư vấn chiến lược digital marketing miễn phí",
                "Audit website và đề xuất cải thiện",
                "Dùng thử 7 ngày các công cụ automation"
            ]
        }
    }

    def __init__(self, llm_client=None):
        """
        Initialize analyzer

        Args:
            llm_client: Optional LLM client for AI-powered analysis
        """
        self.llm_client = llm_client

    def analyze(self, business: ScrapedBusiness) -> BusinessAnalysis:
        """
        Analyze a business and return detailed analysis

        Args:
            business: ScrapedBusiness to analyze

        Returns:
            BusinessAnalysis with scores, pain points, and recommendations
        """
        logger.info(f"Analyzing business: {business.name}")

        # Calculate scores
        lead_score = self._calculate_lead_score(business)
        lead_quality = self._determine_lead_quality(lead_score, business)
        digital_maturity = self._assess_digital_maturity(business)

        # Get industry-specific analysis
        industry_key = self._map_industry(business.industry)
        industry_data = self.INDUSTRY_ANALYSIS.get(
            industry_key,
            self.INDUSTRY_ANALYSIS["default"]
        )

        # Identify pain points
        pain_points = self._identify_pain_points(business, industry_data)

        # Identify opportunities
        opportunities = self._identify_opportunities(business, industry_data)

        # Generate personalization hooks
        hooks = self._generate_personalization_hooks(business)

        # Determine best contact channel
        best_channel = self._determine_best_channel(business)

        # Select recommended offer
        recommended_offer = self._select_offer(business, industry_data, lead_quality)

        # Determine urgency
        urgency = self._determine_urgency(lead_score, digital_maturity)

        # Generate summary
        summary = self._generate_summary(business, pain_points, opportunities)

        return BusinessAnalysis(
            lead_score=lead_score,
            lead_quality=lead_quality,
            digital_maturity=digital_maturity,
            pain_points=pain_points,
            opportunities=opportunities,
            recommended_services=industry_data.get("recommended_services", []),
            personalization_hooks=hooks,
            best_channel=best_channel,
            urgency_level=urgency,
            recommended_offer=recommended_offer,
            summary=summary
        )

    def _calculate_lead_score(self, business: ScrapedBusiness) -> int:
        """Calculate lead score from 0-100"""
        score = 50  # Base score

        # Contact info availability (+20 max)
        if business.email:
            score += 10
        if business.phone:
            score += 10

        # Digital presence indicators
        # Lower digital maturity = HIGHER score (more need for our services)
        dm_score = business.digital_maturity_score

        if dm_score < 30:
            score += 20  # Very low digital presence = high opportunity
        elif dm_score < 50:
            score += 15
        elif dm_score < 70:
            score += 5
        else:
            score -= 10  # Already digitally mature, less need

        # Business indicators
        if business.rating:
            if business.rating >= 4.0:
                score += 10  # Good business, worth investing
            elif business.rating < 3.0:
                score -= 10  # May have other problems

        if business.review_count:
            if business.review_count > 50:
                score += 5  # Established business
            elif business.review_count < 10:
                score += 10  # New business, needs help

        # Website absence is an opportunity
        if not business.website:
            score += 15

        # Social media absence is an opportunity
        if not business.has_social_media:
            score += 10

        return max(0, min(100, score))

    def _determine_lead_quality(
        self,
        score: int,
        business: ScrapedBusiness
    ) -> LeadQuality:
        """Determine lead quality based on score and other factors"""
        if not business.has_contact_info:
            return LeadQuality.UNQUALIFIED

        if score >= 75:
            return LeadQuality.HOT
        elif score >= 50:
            return LeadQuality.WARM
        elif score >= 30:
            return LeadQuality.COLD
        else:
            return LeadQuality.UNQUALIFIED

    def _assess_digital_maturity(self, business: ScrapedBusiness) -> DigitalMaturity:
        """Assess digital presence maturity"""
        score = business.digital_maturity_score

        if score >= 70:
            return DigitalMaturity.ADVANCED
        elif score >= 40:
            return DigitalMaturity.MODERATE
        elif score >= 20:
            return DigitalMaturity.BASIC
        else:
            return DigitalMaturity.NONE

    def _map_industry(self, industry: Optional[str]) -> str:
        """Map industry keyword to analysis category"""
        if not industry:
            return "default"

        industry_lower = industry.lower()

        mappings = {
            "spa": ["spa", "massage", "làm đẹp", "thẩm mỹ", "beauty"],
            "cafe": ["café", "cafe", "coffee", "cà phê", "trà sữa"],
            "nha_khoa": ["nha khoa", "dental", "răng", "phòng khám nha"]
        }

        for key, keywords in mappings.items():
            if any(kw in industry_lower for kw in keywords):
                return key

        return "default"

    def _identify_pain_points(
        self,
        business: ScrapedBusiness,
        industry_data: Dict
    ) -> List[str]:
        """Identify specific pain points for this business"""
        pain_points = []
        pain_point_templates = industry_data.get("pain_points", {})

        # Check for no website
        if not business.website and "no_website" in pain_point_templates:
            pain_points.append(pain_point_templates["no_website"])

        # Check for low reviews
        if (not business.review_count or business.review_count < 20) and "low_reviews" in pain_point_templates:
            pain_points.append(pain_point_templates["low_reviews"])

        # Check for no social media
        if not business.has_social_media and "no_social" in pain_point_templates:
            pain_points.append(pain_point_templates["no_social"])

        # Check for low visibility
        dm_score = business.digital_maturity_score
        if dm_score < 30 and "low_visibility" in pain_point_templates:
            pain_points.append(pain_point_templates["low_visibility"])

        return pain_points[:3]  # Limit to top 3 pain points

    def _identify_opportunities(
        self,
        business: ScrapedBusiness,
        industry_data: Dict
    ) -> List[str]:
        """Identify opportunities for this business"""
        opportunities = []
        opp_templates = industry_data.get("opportunities", {})

        # Website opportunity
        if not business.website:
            for key in ["digital_booking", "professional_website", "digital_presence"]:
                if key in opp_templates:
                    opportunities.append(opp_templates[key])
                    break

        # Social media opportunity
        if not business.has_social_media:
            for key in ["social_marketing", "instagram_marketing", "content_marketing"]:
                if key in opp_templates:
                    opportunities.append(opp_templates[key])
                    break

        # Review building opportunity
        if not business.review_count or business.review_count < 30:
            for key in ["review_campaign", "patient_education"]:
                if key in opp_templates:
                    opportunities.append(opp_templates[key])
                    break

        return opportunities[:3]

    def _generate_personalization_hooks(self, business: ScrapedBusiness) -> List[str]:
        """Generate personalization hooks for outreach"""
        hooks = []

        # Location-based hook
        if business.district:
            hooks.append(f"Thấy {business.name} ở {business.district}")

        # Rating-based hook
        if business.rating and business.rating >= 4.0:
            hooks.append(f"Rating {business.rating} sao trên Google Maps rất ấn tượng")

        # Review-based hook
        if business.reviews:
            # Find a positive review to reference
            for review in business.reviews:
                if review.get("rating", 0) >= 4:
                    hooks.append(f"Thấy khách hàng khen về {business.name}")
                    break

        # Service-based hook
        if business.services:
            hooks.append(f"Dịch vụ {business.services[0]} của bạn")

        # Website absence hook
        if not business.website:
            hooks.append("Mình thấy chưa có website, đây là cơ hội lớn")

        return hooks[:3]

    def _determine_best_channel(self, business: ScrapedBusiness) -> str:
        """Determine the best contact channel"""
        if business.email:
            return "email"
        elif business.facebook_url:
            return "facebook"
        elif business.phone:
            return "phone"
        elif business.zalo_url:
            return "zalo"
        elif business.instagram_url:
            return "instagram"
        else:
            return "google_maps"  # Contact via Google Maps Q&A

    def _select_offer(
        self,
        business: ScrapedBusiness,
        industry_data: Dict,
        lead_quality: LeadQuality
    ) -> str:
        """Select the most appropriate offer"""
        offers = industry_data.get("offers", [])
        if not offers:
            return "Tư vấn miễn phí về chiến lược digital marketing"

        # For hot leads, use the most compelling offer
        if lead_quality == LeadQuality.HOT:
            # Usually the guarantee/risk-reversal offer
            for offer in offers:
                if "cam kết" in offer.lower() or "hoàn tiền" in offer.lower():
                    return offer
            return offers[0]

        # For warm leads, use free trial offers
        elif lead_quality == LeadQuality.WARM:
            for offer in offers:
                if "miễn phí" in offer.lower() or "dùng thử" in offer.lower():
                    return offer
            return offers[0] if offers else ""

        # For cold leads, use low-commitment offers
        else:
            for offer in offers:
                if "audit" in offer.lower() or "tư vấn" in offer.lower():
                    return offer
            return offers[-1] if offers else ""

    def _determine_urgency(
        self,
        lead_score: int,
        digital_maturity: DigitalMaturity
    ) -> str:
        """Determine urgency level for outreach"""
        if lead_score >= 80 and digital_maturity == DigitalMaturity.NONE:
            return "high"
        elif lead_score >= 60:
            return "medium"
        else:
            return "low"

    def _generate_summary(
        self,
        business: ScrapedBusiness,
        pain_points: List[str],
        opportunities: List[str]
    ) -> str:
        """Generate analysis summary"""
        parts = []

        parts.append(f"{business.name} tại {business.district or business.city or 'Việt Nam'}")

        if pain_points:
            parts.append(f"Vấn đề chính: {pain_points[0]}")

        if opportunities:
            parts.append(f"Cơ hội: {opportunities[0]}")

        dm = business.digital_maturity_score
        if dm < 30:
            parts.append("Digital presence rất thấp - tiềm năng cao")
        elif dm < 50:
            parts.append("Digital presence trung bình - có room để cải thiện")

        return ". ".join(parts)

    def batch_analyze(
        self,
        businesses: List[ScrapedBusiness]
    ) -> List[BusinessAnalysis]:
        """Analyze multiple businesses"""
        return [self.analyze(b) for b in businesses]

    def filter_qualified_leads(
        self,
        businesses: List[ScrapedBusiness],
        min_quality: LeadQuality = LeadQuality.WARM
    ) -> List[tuple]:
        """
        Filter and return qualified leads with their analysis

        Returns:
            List of (business, analysis) tuples
        """
        results = []
        quality_order = {
            LeadQuality.HOT: 3,
            LeadQuality.WARM: 2,
            LeadQuality.COLD: 1,
            LeadQuality.UNQUALIFIED: 0
        }
        min_order = quality_order[min_quality]

        for business in businesses:
            analysis = self.analyze(business)
            if quality_order[analysis.lead_quality] >= min_order:
                results.append((business, analysis))

        # Sort by lead score descending
        results.sort(key=lambda x: x[1].lead_score, reverse=True)

        return results
