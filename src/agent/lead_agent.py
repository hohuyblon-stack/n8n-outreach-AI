"""
Lead Generation Agent - Main orchestrator for the entire lead generation process
Coordinates scraping, analysis, email generation, and outreach
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
import json

from loguru import logger

from src.scraper import GoogleMapsScraper, WebScraper, ScrapedBusiness
from src.analyzer import BusinessAnalyzer, BusinessAnalysis
from src.email_generator import EmailGenerator, GeneratedEmail, EmailType
from src.database import Database, Lead, EmailRecord, Campaign


class AgentMode(Enum):
    """Agent operation modes"""
    SEARCH = "search"           # Only search for leads
    ANALYZE = "analyze"         # Search and analyze
    GENERATE = "generate"       # Full pipeline without sending
    OUTREACH = "outreach"       # Full pipeline with email sending
    FOLLOW_UP = "follow_up"     # Send follow-up emails only


@dataclass
class AgentConfig:
    """Configuration for the Lead Generation Agent"""
    # API Keys
    google_maps_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Search settings
    max_leads_per_search: int = 50
    delay_between_requests: int = 2

    # Email settings
    sender_name: str = "AI Agent"
    company_name: str = "Your Company"
    company_phone: str = ""
    company_website: str = ""
    daily_email_limit: int = 100
    use_ai_for_emails: bool = True

    # Database
    database_url: str = "sqlite:///./data/leads.db"

    # Filtering
    min_lead_score: int = 40
    require_email: bool = True


@dataclass
class AgentResult:
    """Result of an agent operation"""
    success: bool
    mode: AgentMode
    started_at: datetime
    completed_at: datetime = field(default_factory=datetime.now)

    # Counts
    leads_found: int = 0
    leads_added: int = 0
    leads_analyzed: int = 0
    emails_generated: int = 0
    emails_sent: int = 0

    # Data
    leads: List[Dict] = field(default_factory=list)
    emails: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "mode": self.mode.value,
            "duration_seconds": (self.completed_at - self.started_at).total_seconds(),
            "leads_found": self.leads_found,
            "leads_added": self.leads_added,
            "leads_analyzed": self.leads_analyzed,
            "emails_generated": self.emails_generated,
            "emails_sent": self.emails_sent,
            "lead_count": len(self.leads),
            "email_count": len(self.emails),
            "error_count": len(self.errors)
        }


class LeadGenerationAgent:
    """
    Main AI Agent for Lead Generation and Outreach

    This agent coordinates the entire lead generation process:
    1. Search for businesses on Google Maps
    2. Enrich data from websites
    3. Analyze and score leads
    4. Generate personalized emails
    5. Send outreach emails
    6. Track and follow up

    Usage:
        agent = LeadGenerationAgent(config)
        result = await agent.run(
            keyword="spa",
            location="TP.HCM",
            mode=AgentMode.GENERATE
        )
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize the agent with configuration

        Args:
            config: AgentConfig with API keys and settings
        """
        self.config = config

        # Initialize components
        self.db = Database(config.database_url)

        self.maps_scraper = GoogleMapsScraper(
            api_key=config.google_maps_api_key,
            delay_seconds=config.delay_between_requests
        )

        self.web_scraper = WebScraper(
            delay_seconds=config.delay_between_requests
        )

        self.analyzer = BusinessAnalyzer()

        self.email_generator = EmailGenerator(
            sender_name=config.sender_name,
            company_name=config.company_name,
            company_phone=config.company_phone,
            company_website=config.company_website
        )

        # Initialize AI clients if keys provided
        self._setup_ai_clients()

        # Callbacks
        self.on_lead_found: Optional[Callable] = None
        self.on_email_generated: Optional[Callable] = None
        self.on_email_sent: Optional[Callable] = None

        logger.info("LeadGenerationAgent initialized")

    def _setup_ai_clients(self):
        """Setup AI clients for email generation"""
        if self.config.openai_api_key:
            try:
                from openai import OpenAI
                self.email_generator.openai_client = OpenAI(
                    api_key=self.config.openai_api_key
                )
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.warning("OpenAI package not installed")

        if self.config.anthropic_api_key:
            try:
                from anthropic import Anthropic
                self.email_generator.anthropic_client = Anthropic(
                    api_key=self.config.anthropic_api_key
                )
                logger.info("Anthropic client initialized")
            except ImportError:
                logger.warning("Anthropic package not installed")

    async def run(
        self,
        keyword: str,
        location: str,
        mode: AgentMode = AgentMode.GENERATE,
        campaign_name: Optional[str] = None,
        offer: Optional[str] = None,
        max_leads: Optional[int] = None
    ) -> AgentResult:
        """
        Run the lead generation agent

        Args:
            keyword: Business type to search (e.g., "spa", "cafe")
            location: Location to search (e.g., "TP.HCM", "Quận 1")
            mode: Operation mode
            campaign_name: Optional campaign name
            offer: Custom offer text
            max_leads: Override max leads setting

        Returns:
            AgentResult with operation results
        """
        started_at = datetime.now()
        logger.info(f"Starting agent in {mode.value} mode for '{keyword}' in '{location}'")

        result = AgentResult(
            success=True,
            mode=mode,
            started_at=started_at
        )

        try:
            # Create or get campaign
            campaign = None
            if campaign_name:
                campaign = self.db.create_campaign(
                    name=campaign_name,
                    industry=keyword,
                    location=location,
                    offer_template=offer
                )

            # Step 1: Search for leads
            if mode in [AgentMode.SEARCH, AgentMode.ANALYZE, AgentMode.GENERATE, AgentMode.OUTREACH]:
                businesses = await self._search_leads(
                    keyword, location,
                    max_leads or self.config.max_leads_per_search
                )
                result.leads_found = len(businesses)
                logger.info(f"Found {len(businesses)} businesses")

                # Step 2: Enrich from websites
                businesses = await self._enrich_leads(businesses)

                # Step 3: Analyze leads
                if mode in [AgentMode.ANALYZE, AgentMode.GENERATE, AgentMode.OUTREACH]:
                    qualified_leads = await self._analyze_leads(businesses)
                    result.leads_analyzed = len(qualified_leads)
                    logger.info(f"Qualified {len(qualified_leads)} leads")

                    # Step 4: Save to database
                    for business, analysis in qualified_leads:
                        lead = self.db.add_lead(
                            business, analysis,
                            campaign_id=campaign.id if campaign else None
                        )
                        if lead:
                            result.leads_added += 1
                            result.leads.append(lead.to_dict())

                            if self.on_lead_found:
                                self.on_lead_found(lead)

                    # Step 5: Generate emails
                    if mode in [AgentMode.GENERATE, AgentMode.OUTREACH]:
                        emails = await self._generate_emails(qualified_leads, offer)
                        result.emails_generated = len(emails)
                        result.emails = [e.to_dict() for e in emails]

                        for email in emails:
                            if self.on_email_generated:
                                self.on_email_generated(email)

                        # Step 6: Send emails (if outreach mode)
                        if mode == AgentMode.OUTREACH:
                            sent_count = await self._send_emails(emails)
                            result.emails_sent = sent_count
                else:
                    # Just save businesses without analysis
                    for business in businesses:
                        lead = self.db.add_lead(business, campaign_id=campaign.id if campaign else None)
                        if lead:
                            result.leads_added += 1
                            result.leads.append(lead.to_dict())

            # Follow-up mode
            elif mode == AgentMode.FOLLOW_UP:
                result = await self._run_follow_ups(result, campaign)

            # Update campaign stats
            if campaign:
                self.db.update_campaign_stats(campaign.id)

        except Exception as e:
            logger.error(f"Agent error: {e}")
            result.success = False
            result.errors.append(str(e))

        result.completed_at = datetime.now()
        logger.info(f"Agent completed in {(result.completed_at - started_at).total_seconds():.2f}s")

        return result

    async def _search_leads(
        self,
        keyword: str,
        location: str,
        max_results: int
    ) -> List[ScrapedBusiness]:
        """Search for businesses using Google Maps"""
        async with self.maps_scraper as scraper:
            businesses = await scraper.search(keyword, location, max_results)

            # Filter out duplicates already in database
            unique_businesses = []
            for business in businesses:
                if not self.db.is_duplicate(business):
                    unique_businesses.append(business)
                else:
                    logger.debug(f"Skipping duplicate: {business.name}")

            return unique_businesses

    async def _enrich_leads(
        self,
        businesses: List[ScrapedBusiness]
    ) -> List[ScrapedBusiness]:
        """Enrich leads with website data"""
        # Only enrich businesses that have websites
        to_enrich = [b for b in businesses if b.website]

        if to_enrich:
            logger.info(f"Enriching {len(to_enrich)} businesses with website data")
            async with self.web_scraper as scraper:
                enriched = await scraper.batch_enrich(to_enrich, concurrency=3)

                # Merge enriched data back
                enriched_map = {b.unique_id: b for b in enriched}
                for i, business in enumerate(businesses):
                    if business.unique_id in enriched_map:
                        businesses[i] = enriched_map[business.unique_id]

        return businesses

    async def _analyze_leads(
        self,
        businesses: List[ScrapedBusiness]
    ) -> List[tuple]:
        """Analyze leads and filter qualified ones"""
        qualified = []

        for business in businesses:
            analysis = self.analyzer.analyze(business)

            # Filter based on config
            if analysis.lead_score >= self.config.min_lead_score:
                if not self.config.require_email or business.email:
                    qualified.append((business, analysis))
                else:
                    logger.debug(f"Skipping {business.name}: no email")
            else:
                logger.debug(f"Skipping {business.name}: score {analysis.lead_score} < {self.config.min_lead_score}")

        # Sort by score
        qualified.sort(key=lambda x: x[1].lead_score, reverse=True)

        return qualified

    async def _generate_emails(
        self,
        leads: List[tuple],
        custom_offer: Optional[str] = None
    ) -> List[GeneratedEmail]:
        """Generate personalized emails for leads"""
        emails = []

        for business, analysis in leads:
            if not business.email:
                continue

            # Override offer if custom one provided
            if custom_offer:
                analysis.recommended_offer = custom_offer

            email = self.email_generator.generate(
                business=business,
                analysis=analysis,
                email_type=EmailType.FIRST_CONTACT,
                use_ai=self.config.use_ai_for_emails
            )

            emails.append(email)

            # Respect rate limits
            if len(emails) >= self.config.daily_email_limit:
                logger.warning(f"Reached daily email limit: {self.config.daily_email_limit}")
                break

        return emails

    async def _send_emails(self, emails: List[GeneratedEmail]) -> int:
        """
        Send emails (placeholder - actual implementation would use SMTP)

        Note: In production, integrate with actual email service
        (SendGrid, Mailgun, AWS SES, etc.)
        """
        sent_count = 0

        for email in emails:
            try:
                # TODO: Implement actual email sending
                # For now, just log and mark as sent
                logger.info(f"Would send email to: {email.recipient_email}")
                logger.debug(f"Subject: {email.subject}")

                # Save to database
                # Get lead ID from email recipient
                # lead = self.db.get_lead_by_email(email.recipient_email)
                # if lead:
                #     record = self.db.add_email_record(lead.id, email)
                #     self.db.mark_email_sent(record.id)
                #     self.db.mark_lead_contacted(lead.id)

                email.sent = True
                email.sent_at = datetime.now()
                sent_count += 1

                if self.on_email_sent:
                    self.on_email_sent(email)

                # Rate limiting
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Failed to send email to {email.recipient_email}: {e}")

        return sent_count

    async def _run_follow_ups(
        self,
        result: AgentResult,
        campaign: Optional[Campaign]
    ) -> AgentResult:
        """Run follow-up email sequence"""
        pending = self.db.get_pending_follow_ups(
            days_since_last=3,
            limit=self.config.daily_email_limit
        )

        logger.info(f"Found {len(pending)} leads for follow-up")

        for item in pending:
            lead = item["lead"]
            email_count = item["email_count"]

            # Determine follow-up type
            if email_count == 1:
                email_type = EmailType.FOLLOW_UP_1
            elif email_count == 2:
                email_type = EmailType.FOLLOW_UP_2
            else:
                continue  # Max follow-ups reached

            # Get previous emails for context
            previous_emails = self.db.get_emails_for_lead(lead.id)
            previous_subject = previous_emails[0].subject if previous_emails else ""

            # Convert Lead back to ScrapedBusiness for email generation
            business = self._lead_to_business(lead)

            # Create minimal analysis
            analysis = BusinessAnalysis(
                lead_score=lead.lead_score or 50,
                lead_quality=lead.lead_quality or "warm",
                digital_maturity="moderate",
                pain_points=lead.pain_points or [],
                opportunities=lead.opportunities or [],
                recommended_offer=lead.recommended_offer or ""
            )

            # Generate follow-up email
            email = self.email_generator.generate(
                business=business,
                analysis=analysis,
                email_type=email_type,
                use_ai=self.config.use_ai_for_emails,
                previous_subject=previous_subject
            )

            result.emails_generated += 1
            result.emails.append(email.to_dict())

            # TODO: Send the email
            logger.info(f"Generated follow-up {email_count + 1} for {lead.name}")

        return result

    def _lead_to_business(self, lead: Lead) -> ScrapedBusiness:
        """Convert Lead model back to ScrapedBusiness"""
        return ScrapedBusiness(
            name=lead.name,
            address=lead.address or "",
            phone=lead.phone,
            email=lead.email,
            website=lead.website,
            city=lead.city,
            district=lead.district,
            industry=lead.industry,
            rating=lead.rating,
            review_count=lead.review_count
        )

    # ==================== UTILITY METHODS ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get overall agent statistics"""
        lead_stats = self.db.get_lead_stats()
        email_stats = self.db.get_email_stats()

        return {
            "leads": lead_stats,
            "emails": email_stats
        }

    def get_leads(
        self,
        industry: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get leads from database"""
        leads = self.db.search_leads(
            industry=industry,
            status=status,
            limit=limit
        )
        return [lead.to_dict() for lead in leads]

    def export_leads(self, format: str = "json") -> str:
        """Export all leads"""
        return self.db.export_leads(format=format)

    async def run_demo(self, keyword: str = "spa", location: str = "Quận 1 TP.HCM"):
        """
        Run a demo of the agent without actual API calls

        Creates sample data to demonstrate the pipeline
        """
        logger.info("Running demo mode with sample data")

        # Create sample business
        sample_business = ScrapedBusiness(
            name="Spa Hoa Sen",
            address="123 Nguyễn Huệ, Quận 1, TP.HCM",
            phone="0901234567",
            email="contact@hoasenspa.vn",
            website="https://hoasenspa.vn",
            city="Hồ Chí Minh",
            district="Quận 1",
            industry=keyword,
            rating=4.5,
            review_count=156,
            google_maps_url="https://maps.google.com/?q=spa+hoa+sen"
        )

        # Analyze
        analysis = self.analyzer.analyze(sample_business)
        logger.info(f"Lead Score: {analysis.lead_score}")
        logger.info(f"Pain Points: {analysis.pain_points}")
        logger.info(f"Recommended Offer: {analysis.recommended_offer}")

        # Generate email
        email = self.email_generator.generate(
            sample_business,
            analysis,
            EmailType.FIRST_CONTACT,
            use_ai=False  # Use template in demo
        )

        logger.info(f"\n{'='*50}")
        logger.info(f"GENERATED EMAIL")
        logger.info(f"{'='*50}")
        logger.info(f"To: {email.recipient_email}")
        logger.info(f"Subject: {email.subject}")
        logger.info(f"\n{email.body}")
        logger.info(f"{'='*50}")
        logger.info(f"Personalization Score: {email.personalization_score}/100")

        return {
            "business": sample_business.to_dict(),
            "analysis": analysis.to_dict(),
            "email": email.to_dict()
        }
