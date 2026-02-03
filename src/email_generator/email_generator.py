"""
Email Generator - Create personalized outreach emails using AI
Supports multiple email types and personalization strategies
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import json
import re

from loguru import logger

from src.scraper.base_scraper import ScrapedBusiness
from src.analyzer.business_analyzer import BusinessAnalysis, LeadQuality


class EmailType(Enum):
    """Type of email in the sequence"""
    FIRST_CONTACT = "first_contact"
    FOLLOW_UP_1 = "follow_up_1"
    FOLLOW_UP_2 = "follow_up_2"
    FINAL_ATTEMPT = "final_attempt"
    VALUE_ADD = "value_add"  # Providing value without asking


@dataclass
class GeneratedEmail:
    """Generated email ready to send"""
    subject: str
    body: str
    email_type: EmailType
    recipient_name: str
    recipient_email: str
    business_name: str

    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    personalization_score: int = 0  # 0-100
    word_count: int = 0

    # Tracking
    sent: bool = False
    sent_at: Optional[datetime] = None
    opened: bool = False
    replied: bool = False

    def __post_init__(self):
        self.word_count = len(self.body.split())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "body": self.body,
            "email_type": self.email_type.value,
            "recipient_name": self.recipient_name,
            "recipient_email": self.recipient_email,
            "business_name": self.business_name,
            "generated_at": self.generated_at.isoformat(),
            "personalization_score": self.personalization_score,
            "word_count": self.word_count,
            "sent": self.sent,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "opened": self.opened,
            "replied": self.replied
        }


class EmailGenerator:
    """
    Generate personalized sales emails using AI or templates

    Features:
    - AI-powered personalization
    - Multiple email templates per industry
    - Sequence support (first contact, follow-ups)
    - Vietnamese language optimization
    """

    # Email templates for when AI is not available
    TEMPLATES = {
        EmailType.FIRST_CONTACT: {
            "spa": {
                "subject": "Tăng 30% khách đặt lịch cho {business_name}?",
                "body": """Chào bạn,

Mình là {sender_name} từ {company_name}.

{personalization_hook}

Mình thấy {business_name} có rating rất tốt trên Google ({rating} sao). Tuy nhiên, mình nhận ra một điều: {pain_point}

Mình đã giúp nhiều spa tương tự tăng 30-50% lượng khách đặt lịch chỉ trong 30 ngày đầu tiên bằng cách:
- Tối ưu hiển thị trên Google Maps
- Hệ thống đặt lịch online 24/7
- Chiến dịch remarketing khách cũ

{offer}

Bạn có 15 phút trong tuần này để mình chia sẻ chi tiết không?

Trân trọng,
{sender_name}
{company_name}
{company_phone}"""
            },
            "cafe": {
                "subject": "Ý tưởng tăng khách cho {business_name}",
                "body": """Chào bạn,

Mình là {sender_name}.

{personalization_hook}

Mình để ý thấy {business_name} có không gian rất đẹp, nhưng {pain_point}

Mình có vài ý tưởng có thể giúp quán tăng lượng khách vào những ngày thường:
- Chương trình loyalty qua Zalo OA
- Content Instagram thu hút khách mới
- Đặt hàng online + delivery

{offer}

Nếu bạn quan tâm, mình có thể gửi case study của một quán café tương tự đã tăng 40% doanh thu.

Cảm ơn bạn,
{sender_name}
{company_phone}"""
            },
            "nha_khoa": {
                "subject": "Giúp {business_name} tăng bệnh nhân mới",
                "body": """Chào bác sĩ,

Mình là {sender_name} từ {company_name}, chuyên về marketing cho ngành y tế.

{personalization_hook}

Mình hiểu rằng trong ngành nha khoa, niềm tin là yếu tố quan trọng nhất. Tuy nhiên, {pain_point}

Mình đã giúp nhiều phòng khám nha khoa:
- Xây dựng website chuyên nghiệp tạo uy tín
- Tối ưu Google Maps để bệnh nhân dễ tìm thấy
- Hệ thống nhắc lịch tái khám tự động

{offer}

Bác sĩ có thể cho mình 10 phút để chia sẻ thêm không?

Trân trọng,
{sender_name}
{company_name}"""
            },
            "default": {
                "subject": "Ý tưởng marketing cho {business_name}",
                "body": """Chào bạn,

Mình là {sender_name} từ {company_name}.

{personalization_hook}

Mình nhận thấy {pain_point}

Đây là những gì mình có thể giúp:
- Tăng hiển thị online
- Thu hút khách hàng tiềm năng
- Tự động hóa marketing

{offer}

Bạn có muốn mình gửi thêm thông tin không?

Trân trọng,
{sender_name}"""
            }
        },
        EmailType.FOLLOW_UP_1: {
            "default": {
                "subject": "Re: {previous_subject}",
                "body": """Chào bạn,

Mình gửi email trước nhưng chưa nhận được phản hồi, nên muốn follow up nhanh.

Mình hiểu bạn rất bận. Chỉ muốn hỏi: Bạn có đang gặp khó khăn gì trong việc tìm kiếm khách hàng mới không?

Nếu có, mình rất vui được chia sẻ một vài tips miễn phí, không cam kết gì cả.

Trả lời "CÓ" nếu bạn muốn mình gửi thêm thông tin.

{sender_name}"""
            }
        },
        EmailType.FOLLOW_UP_2: {
            "default": {
                "subject": "Lần cuối mình hỏi thăm",
                "body": """Chào bạn,

Đây là lần cuối mình liên hệ về vấn đề này.

Mình có một {offer} - nếu bạn quan tâm, chỉ cần reply email này.

Nếu không phải thời điểm phù hợp, mình hoàn toàn hiểu. Chúc {business_name} kinh doanh thật tốt!

{sender_name}"""
            }
        }
    }

    def __init__(
        self,
        openai_client=None,
        anthropic_client=None,
        sender_name: str = "AI Agent",
        company_name: str = "Your Company",
        company_phone: str = "",
        company_website: str = ""
    ):
        """
        Initialize email generator

        Args:
            openai_client: OpenAI client for AI generation
            anthropic_client: Anthropic client (alternative)
            sender_name: Name to use in emails
            company_name: Company name for signature
            company_phone: Contact phone
            company_website: Company website
        """
        self.openai_client = openai_client
        self.anthropic_client = anthropic_client
        self.sender_name = sender_name
        self.company_name = company_name
        self.company_phone = company_phone
        self.company_website = company_website

    def generate(
        self,
        business: ScrapedBusiness,
        analysis: BusinessAnalysis,
        email_type: EmailType = EmailType.FIRST_CONTACT,
        use_ai: bool = True,
        previous_subject: str = ""
    ) -> GeneratedEmail:
        """
        Generate a personalized email for a business

        Args:
            business: Target business
            analysis: Business analysis results
            email_type: Type of email to generate
            use_ai: Whether to use AI for generation
            previous_subject: Subject of previous email (for follow-ups)

        Returns:
            GeneratedEmail ready to send
        """
        logger.info(f"Generating {email_type.value} email for {business.name}")

        # Extract recipient info
        recipient_name = self._extract_recipient_name(business)
        recipient_email = business.email or ""

        if use_ai and (self.openai_client or self.anthropic_client):
            email = self._generate_with_ai(
                business, analysis, email_type, recipient_name, previous_subject
            )
        else:
            email = self._generate_from_template(
                business, analysis, email_type, recipient_name, previous_subject
            )

        # Calculate personalization score
        email.personalization_score = self._calculate_personalization_score(
            email, business, analysis
        )

        return email

    def _generate_with_ai(
        self,
        business: ScrapedBusiness,
        analysis: BusinessAnalysis,
        email_type: EmailType,
        recipient_name: str,
        previous_subject: str
    ) -> GeneratedEmail:
        """Generate email using AI"""
        prompt = self._build_ai_prompt(
            business, analysis, email_type, recipient_name, previous_subject
        )

        try:
            if self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": self._get_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                content = response.choices[0].message.content

            elif self.anthropic_client:
                response = self.anthropic_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    system=self._get_system_prompt(),
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                content = response.content[0].text

            else:
                raise ValueError("No AI client available")

            # Parse AI response
            subject, body = self._parse_ai_response(content)

            return GeneratedEmail(
                subject=subject,
                body=body,
                email_type=email_type,
                recipient_name=recipient_name,
                recipient_email=business.email or "",
                business_name=business.name
            )

        except Exception as e:
            logger.error(f"AI generation failed: {e}, falling back to template")
            return self._generate_from_template(
                business, analysis, email_type, recipient_name, previous_subject
            )

    def _get_system_prompt(self) -> str:
        """System prompt for AI email generation"""
        return """Bạn là một chuyên gia sales B2B với 10 năm kinh nghiệm.
Nhiệm vụ: Viết email outreach bằng tiếng Việt, ngắn gọn, thân thiện, không spam.

Nguyên tắc:
1. Email phải dưới 150 từ
2. Mở đầu bằng điều gì đó CỤ THỂ về doanh nghiệp (không chung chung)
3. Nêu MỘT vấn đề họ có thể đang gặp phải
4. Đề xuất giải pháp với offer win-win
5. Call-to-action đơn giản, dễ thực hiện
6. Giọng văn như đang nói chuyện, không cứng nhắc
7. KHÔNG dùng từ: "kính gửi", "trân trọng kính mời", "xin phép được"
8. KHÔNG quá nhiều emoji
9. KHÔNG dùng các cụm từ quảng cáo sáo rỗng

Format output:
SUBJECT: [tiêu đề email]
BODY:
[nội dung email]"""

    def _build_ai_prompt(
        self,
        business: ScrapedBusiness,
        analysis: BusinessAnalysis,
        email_type: EmailType,
        recipient_name: str,
        previous_subject: str
    ) -> str:
        """Build prompt for AI generation"""
        context = f"""
Thông tin doanh nghiệp:
- Tên: {business.name}
- Ngành: {business.industry or 'Không rõ'}
- Địa chỉ: {business.address}
- Rating: {business.rating or 'N/A'} ({business.review_count or 0} reviews)
- Website: {business.website or 'Không có'}
- Social Media: {'Có' if business.has_social_media else 'Không có'}

Phân tích:
- Lead Score: {analysis.lead_score}/100
- Digital Maturity: {analysis.digital_maturity.value}
- Pain Points: {', '.join(analysis.pain_points[:2]) if analysis.pain_points else 'N/A'}
- Opportunities: {', '.join(analysis.opportunities[:2]) if analysis.opportunities else 'N/A'}
- Recommended Offer: {analysis.recommended_offer}
- Personalization Hooks: {', '.join(analysis.personalization_hooks[:2]) if analysis.personalization_hooks else 'N/A'}

Thông tin người gửi:
- Tên: {self.sender_name}
- Công ty: {self.company_name}
- SĐT: {self.company_phone}

Loại email: {email_type.value}
"""

        if email_type == EmailType.FIRST_CONTACT:
            context += "\nViết email tiếp cận lần đầu, tập trung vào pain point chính và offer hấp dẫn."
        elif email_type == EmailType.FOLLOW_UP_1:
            context += f"\nViết email follow-up (email trước subject: {previous_subject}). Ngắn gọn, nhắc lại giá trị."
        elif email_type == EmailType.FOLLOW_UP_2:
            context += "\nViết email follow-up cuối cùng. Tạo urgency nhẹ nhàng, không ép buộc."

        return context

    def _parse_ai_response(self, content: str) -> tuple:
        """Parse AI response to extract subject and body"""
        lines = content.strip().split('\n')

        subject = ""
        body_lines = []
        in_body = False

        for line in lines:
            if line.upper().startswith('SUBJECT:'):
                subject = line.split(':', 1)[1].strip()
            elif line.upper().startswith('BODY:'):
                in_body = True
            elif in_body:
                body_lines.append(line)

        body = '\n'.join(body_lines).strip()

        # Fallback if parsing fails
        if not subject:
            subject = "Ý tưởng hợp tác"
        if not body:
            body = content

        return subject, body

    def _generate_from_template(
        self,
        business: ScrapedBusiness,
        analysis: BusinessAnalysis,
        email_type: EmailType,
        recipient_name: str,
        previous_subject: str
    ) -> GeneratedEmail:
        """Generate email from templates when AI is not available"""
        # Get industry-specific template
        industry_key = self._map_industry(business.industry)
        templates = self.TEMPLATES.get(email_type, self.TEMPLATES[EmailType.FIRST_CONTACT])
        template = templates.get(industry_key, templates.get("default", {}))

        # Prepare personalization hook
        personalization_hook = ""
        if analysis.personalization_hooks:
            personalization_hook = analysis.personalization_hooks[0]
        elif business.rating:
            personalization_hook = f"Mình thấy {business.name} có rating {business.rating} sao trên Google Maps."
        else:
            personalization_hook = f"Mình tìm hiểu về {business.name} và thấy rất ấn tượng."

        # Prepare pain point
        pain_point = ""
        if analysis.pain_points:
            pain_point = analysis.pain_points[0].lower()
        else:
            pain_point = "có thể còn nhiều cơ hội để phát triển online"

        # Format template
        subject = template.get("subject", "Ý tưởng hợp tác").format(
            business_name=business.name,
            previous_subject=previous_subject
        )

        body = template.get("body", "").format(
            business_name=business.name,
            sender_name=self.sender_name,
            company_name=self.company_name,
            company_phone=self.company_phone,
            rating=business.rating or "tốt",
            personalization_hook=personalization_hook,
            pain_point=pain_point,
            offer=analysis.recommended_offer or "Tư vấn miễn phí",
            previous_subject=previous_subject
        )

        return GeneratedEmail(
            subject=subject,
            body=body,
            email_type=email_type,
            recipient_name=recipient_name,
            recipient_email=business.email or "",
            business_name=business.name
        )

    def _extract_recipient_name(self, business: ScrapedBusiness) -> str:
        """Extract recipient name from business info"""
        # For now, use generic "bạn" or try to extract from reviews
        if business.reviews:
            # Sometimes owner responds to reviews with their name
            pass

        return "bạn"

    def _map_industry(self, industry: Optional[str]) -> str:
        """Map industry to template category"""
        if not industry:
            return "default"

        industry_lower = industry.lower()

        if any(kw in industry_lower for kw in ["spa", "massage", "làm đẹp"]):
            return "spa"
        elif any(kw in industry_lower for kw in ["café", "cafe", "coffee"]):
            return "cafe"
        elif any(kw in industry_lower for kw in ["nha khoa", "dental"]):
            return "nha_khoa"

        return "default"

    def _calculate_personalization_score(
        self,
        email: GeneratedEmail,
        business: ScrapedBusiness,
        analysis: BusinessAnalysis
    ) -> int:
        """Calculate how personalized the email is (0-100)"""
        score = 0

        # Business name mentioned (+20)
        if business.name.lower() in email.body.lower():
            score += 20

        # Location mentioned (+15)
        if business.district and business.district.lower() in email.body.lower():
            score += 15
        elif business.city and business.city.lower() in email.body.lower():
            score += 10

        # Rating mentioned (+15)
        if business.rating and str(business.rating) in email.body:
            score += 15

        # Pain point mentioned (+20)
        for pain_point in analysis.pain_points:
            if any(word in email.body.lower() for word in pain_point.lower().split()[:3]):
                score += 20
                break

        # Specific offer included (+15)
        if analysis.recommended_offer and len(analysis.recommended_offer) > 10:
            if any(word in email.body.lower() for word in analysis.recommended_offer.lower().split()[:3]):
                score += 15

        # Industry-specific language (+15)
        industry_terms = {
            "spa": ["đặt lịch", "khách hàng", "dịch vụ", "chăm sóc"],
            "cafe": ["quán", "khách", "menu", "đồ uống"],
            "nha_khoa": ["bệnh nhân", "phòng khám", "bác sĩ", "điều trị"]
        }
        industry_key = self._map_industry(business.industry)
        if industry_key in industry_terms:
            for term in industry_terms[industry_key]:
                if term in email.body.lower():
                    score += 5
                    break

        return min(100, score)

    def generate_sequence(
        self,
        business: ScrapedBusiness,
        analysis: BusinessAnalysis,
        use_ai: bool = True
    ) -> List[GeneratedEmail]:
        """
        Generate a complete email sequence for a lead

        Args:
            business: Target business
            analysis: Business analysis
            use_ai: Whether to use AI

        Returns:
            List of emails in sequence order
        """
        sequence = []

        # First contact
        first = self.generate(
            business, analysis, EmailType.FIRST_CONTACT, use_ai
        )
        sequence.append(first)

        # Follow-up 1
        follow1 = self.generate(
            business, analysis, EmailType.FOLLOW_UP_1, use_ai,
            previous_subject=first.subject
        )
        sequence.append(follow1)

        # Follow-up 2 (final)
        follow2 = self.generate(
            business, analysis, EmailType.FOLLOW_UP_2, use_ai,
            previous_subject=first.subject
        )
        sequence.append(follow2)

        return sequence

    def batch_generate(
        self,
        leads: List[tuple],  # List of (business, analysis) tuples
        email_type: EmailType = EmailType.FIRST_CONTACT,
        use_ai: bool = True
    ) -> List[GeneratedEmail]:
        """Generate emails for multiple leads"""
        emails = []
        for business, analysis in leads:
            email = self.generate(business, analysis, email_type, use_ai)
            emails.append(email)
        return emails
