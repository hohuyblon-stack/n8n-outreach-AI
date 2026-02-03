"""
Database Manager - Handle all database operations
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json

from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from .models import Base, Lead, EmailRecord, Campaign
from src.scraper.base_scraper import ScrapedBusiness
from src.analyzer.business_analyzer import BusinessAnalysis
from src.email_generator.email_generator import GeneratedEmail


class Database:
    """
    Database manager for lead management

    Features:
    - CRUD operations for leads
    - Duplicate detection
    - Email tracking
    - Campaign management
    - Analytics queries
    """

    def __init__(self, database_url: str = "sqlite:///./data/leads.db"):
        """
        Initialize database connection

        Args:
            database_url: SQLAlchemy database URL
        """
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._create_tables()

    def _create_tables(self):
        """Create all tables if they don't exist"""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables initialized")

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    # ==================== LEAD OPERATIONS ====================

    def add_lead(
        self,
        business: ScrapedBusiness,
        analysis: Optional[BusinessAnalysis] = None,
        campaign_id: Optional[int] = None
    ) -> Optional[Lead]:
        """
        Add a new lead to the database

        Args:
            business: Scraped business data
            analysis: Optional business analysis
            campaign_id: Optional campaign to associate with

        Returns:
            Lead object if created, None if duplicate
        """
        with self.get_session() as session:
            # Check for duplicate
            existing = session.query(Lead).filter(
                Lead.unique_id == business.unique_id
            ).first()

            if existing:
                logger.debug(f"Duplicate lead found: {business.name}")
                return None

            # Create new lead
            lead = Lead(
                unique_id=business.unique_id,
                name=business.name,
                address=business.address,
                phone=business.phone,
                email=business.email,
                website=business.website,
                city=business.city,
                district=business.district,
                latitude=business.latitude,
                longitude=business.longitude,
                industry=business.industry,
                category=business.category,
                description=business.description,
                services=business.services,
                products=business.products,
                google_maps_url=business.google_maps_url,
                facebook_url=business.facebook_url,
                instagram_url=business.instagram_url,
                zalo_url=business.zalo_url,
                rating=business.rating,
                review_count=business.review_count,
                reviews=business.reviews,
                opening_hours=business.opening_hours,
                photo_urls=business.photo_urls,
                source=business.source,
                scraped_at=business.scraped_at,
                digital_maturity_score=business.digital_maturity_score,
                campaign_id=campaign_id
            )

            # Add analysis results if available
            if analysis:
                lead.lead_score = analysis.lead_score
                lead.lead_quality = analysis.lead_quality.value
                lead.pain_points = analysis.pain_points
                lead.opportunities = analysis.opportunities
                lead.recommended_offer = analysis.recommended_offer
                lead.personalization_hooks = analysis.personalization_hooks
                lead.preferred_channel = analysis.best_channel

            session.add(lead)
            session.commit()
            session.refresh(lead)

            logger.info(f"Added new lead: {lead.name} (ID: {lead.id})")
            return lead

    def add_leads_bulk(
        self,
        businesses: List[ScrapedBusiness],
        analyses: Optional[List[BusinessAnalysis]] = None,
        campaign_id: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Add multiple leads in bulk

        Returns:
            Dict with counts: {"added": X, "duplicates": Y}
        """
        added = 0
        duplicates = 0

        for i, business in enumerate(businesses):
            analysis = analyses[i] if analyses and i < len(analyses) else None
            result = self.add_lead(business, analysis, campaign_id)
            if result:
                added += 1
            else:
                duplicates += 1

        logger.info(f"Bulk add complete: {added} added, {duplicates} duplicates")
        return {"added": added, "duplicates": duplicates}

    def get_lead(self, lead_id: int) -> Optional[Lead]:
        """Get a lead by ID"""
        with self.get_session() as session:
            return session.query(Lead).filter(Lead.id == lead_id).first()

    def get_lead_by_unique_id(self, unique_id: str) -> Optional[Lead]:
        """Get a lead by unique ID"""
        with self.get_session() as session:
            return session.query(Lead).filter(Lead.unique_id == unique_id).first()

    def update_lead(self, lead_id: int, **kwargs) -> Optional[Lead]:
        """Update a lead's fields"""
        with self.get_session() as session:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                return None

            for key, value in kwargs.items():
                if hasattr(lead, key):
                    setattr(lead, key, value)

            session.commit()
            session.refresh(lead)
            return lead

    def update_lead_status(
        self,
        lead_id: int,
        status: str,
        note: Optional[str] = None
    ) -> Optional[Lead]:
        """Update lead status and optionally add a note"""
        with self.get_session() as session:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                return None

            lead.status = status
            if note:
                lead.add_note(note)

            session.commit()
            return lead

    def mark_lead_contacted(self, lead_id: int) -> Optional[Lead]:
        """Mark a lead as contacted"""
        with self.get_session() as session:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                return None

            lead.contact_attempts += 1
            lead.last_contacted = datetime.utcnow()

            if lead.status == "new":
                lead.status = "contacted"

            session.commit()
            return lead

    def search_leads(
        self,
        industry: Optional[str] = None,
        city: Optional[str] = None,
        status: Optional[str] = None,
        min_score: Optional[int] = None,
        has_email: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Lead]:
        """
        Search leads with filters

        Args:
            industry: Filter by industry
            city: Filter by city
            status: Filter by status
            min_score: Minimum lead score
            has_email: Filter for leads with/without email
            limit: Max results
            offset: Result offset

        Returns:
            List of matching leads
        """
        with self.get_session() as session:
            query = session.query(Lead)

            if industry:
                query = query.filter(Lead.industry.ilike(f"%{industry}%"))
            if city:
                query = query.filter(Lead.city.ilike(f"%{city}%"))
            if status:
                query = query.filter(Lead.status == status)
            if min_score is not None:
                query = query.filter(Lead.lead_score >= min_score)
            if has_email is not None:
                if has_email:
                    query = query.filter(Lead.email.isnot(None))
                else:
                    query = query.filter(Lead.email.is_(None))

            query = query.order_by(Lead.lead_score.desc())
            query = query.limit(limit).offset(offset)

            return query.all()

    def get_leads_for_outreach(
        self,
        campaign_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Lead]:
        """
        Get leads ready for outreach

        Criteria:
        - Has email
        - Not contacted in last 3 days
        - Status is new or contacted (not responded/converted/not_interested)
        - Sorted by lead score
        """
        with self.get_session() as session:
            three_days_ago = datetime.utcnow() - timedelta(days=3)

            query = session.query(Lead).filter(
                Lead.email.isnot(None),
                Lead.status.in_(["new", "contacted"]),
                or_(
                    Lead.last_contacted.is_(None),
                    Lead.last_contacted < three_days_ago
                )
            )

            if campaign_id:
                query = query.filter(Lead.campaign_id == campaign_id)

            query = query.order_by(Lead.lead_score.desc())
            query = query.limit(limit)

            return query.all()

    def is_duplicate(self, business: ScrapedBusiness) -> bool:
        """Check if a business already exists"""
        with self.get_session() as session:
            exists = session.query(Lead).filter(
                Lead.unique_id == business.unique_id
            ).first()
            return exists is not None

    # ==================== EMAIL OPERATIONS ====================

    def add_email_record(
        self,
        lead_id: int,
        email: GeneratedEmail,
        campaign_id: Optional[int] = None
    ) -> EmailRecord:
        """Add an email record"""
        with self.get_session() as session:
            record = EmailRecord(
                lead_id=lead_id,
                subject=email.subject,
                body=email.body,
                email_type=email.email_type.value,
                recipient_email=email.recipient_email,
                recipient_name=email.recipient_name,
                personalization_score=email.personalization_score,
                campaign_id=campaign_id
            )

            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def mark_email_sent(self, email_id: int) -> Optional[EmailRecord]:
        """Mark an email as sent"""
        with self.get_session() as session:
            record = session.query(EmailRecord).filter(
                EmailRecord.id == email_id
            ).first()
            if record:
                record.mark_sent()
                session.commit()
            return record

    def get_emails_for_lead(self, lead_id: int) -> List[EmailRecord]:
        """Get all emails sent to a lead"""
        with self.get_session() as session:
            return session.query(EmailRecord).filter(
                EmailRecord.lead_id == lead_id
            ).order_by(EmailRecord.created_at.desc()).all()

    def get_pending_follow_ups(
        self,
        days_since_last: int = 3,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get leads that need follow-up emails

        Returns:
            List of dicts with lead and last email info
        """
        with self.get_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=days_since_last)

            # Subquery for last email per lead
            subq = session.query(
                EmailRecord.lead_id,
                func.max(EmailRecord.sent_at).label("last_sent"),
                func.count(EmailRecord.id).label("email_count")
            ).filter(
                EmailRecord.status == "sent"
            ).group_by(EmailRecord.lead_id).subquery()

            # Join with leads that need follow-up
            results = session.query(Lead, subq.c.last_sent, subq.c.email_count).join(
                subq, Lead.id == subq.c.lead_id
            ).filter(
                Lead.status.in_(["contacted"]),
                Lead.email.isnot(None),
                subq.c.last_sent < cutoff,
                subq.c.email_count < 3  # Max 3 emails in sequence
            ).order_by(Lead.lead_score.desc()).limit(limit).all()

            return [
                {
                    "lead": lead,
                    "last_sent": last_sent,
                    "email_count": count
                }
                for lead, last_sent, count in results
            ]

    # ==================== CAMPAIGN OPERATIONS ====================

    def create_campaign(
        self,
        name: str,
        industry: str,
        location: str,
        **kwargs
    ) -> Campaign:
        """Create a new campaign"""
        with self.get_session() as session:
            campaign = Campaign(
                name=name,
                industry=industry,
                location=location,
                **kwargs
            )
            session.add(campaign)
            session.commit()
            session.refresh(campaign)
            logger.info(f"Created campaign: {name} (ID: {campaign.id})")
            return campaign

    def get_campaign(self, campaign_id: int) -> Optional[Campaign]:
        """Get a campaign by ID"""
        with self.get_session() as session:
            return session.query(Campaign).filter(
                Campaign.id == campaign_id
            ).first()

    def update_campaign_stats(self, campaign_id: int):
        """Update campaign statistics"""
        with self.get_session() as session:
            campaign = session.query(Campaign).filter(
                Campaign.id == campaign_id
            ).first()

            if not campaign:
                return

            # Count leads
            campaign.total_leads = session.query(Lead).filter(
                Lead.campaign_id == campaign_id
            ).count()

            # Count emails
            email_stats = session.query(
                func.count(EmailRecord.id).label("total"),
                func.sum(func.cast(EmailRecord.status == "opened", Integer)).label("opened"),
                func.sum(func.cast(EmailRecord.status == "replied", Integer)).label("replied")
            ).filter(
                EmailRecord.campaign_id == campaign_id,
                EmailRecord.status != "draft"
            ).first()

            if email_stats:
                campaign.emails_sent = email_stats.total or 0
                campaign.emails_opened = email_stats.opened or 0
                campaign.replies_received = email_stats.replied or 0

            session.commit()

    def get_all_campaigns(self, status: Optional[str] = None) -> List[Campaign]:
        """Get all campaigns"""
        with self.get_session() as session:
            query = session.query(Campaign)
            if status:
                query = query.filter(Campaign.status == status)
            return query.order_by(Campaign.created_at.desc()).all()

    # ==================== ANALYTICS ====================

    def get_lead_stats(self) -> Dict[str, Any]:
        """Get overall lead statistics"""
        with self.get_session() as session:
            total = session.query(Lead).count()

            by_status = dict(
                session.query(Lead.status, func.count(Lead.id))
                .group_by(Lead.status).all()
            )

            by_industry = dict(
                session.query(Lead.industry, func.count(Lead.id))
                .group_by(Lead.industry).all()
            )

            by_quality = dict(
                session.query(Lead.lead_quality, func.count(Lead.id))
                .group_by(Lead.lead_quality).all()
            )

            avg_score = session.query(func.avg(Lead.lead_score)).scalar() or 0

            return {
                "total_leads": total,
                "by_status": by_status,
                "by_industry": by_industry,
                "by_quality": by_quality,
                "average_score": round(avg_score, 2)
            }

    def get_email_stats(self) -> Dict[str, Any]:
        """Get email performance statistics"""
        with self.get_session() as session:
            total_sent = session.query(EmailRecord).filter(
                EmailRecord.status != "draft"
            ).count()

            opened = session.query(EmailRecord).filter(
                EmailRecord.status == "opened"
            ).count()

            replied = session.query(EmailRecord).filter(
                EmailRecord.status == "replied"
            ).count()

            avg_personalization = session.query(
                func.avg(EmailRecord.personalization_score)
            ).scalar() or 0

            return {
                "total_sent": total_sent,
                "opened": opened,
                "replied": replied,
                "open_rate": round((opened / total_sent * 100) if total_sent > 0 else 0, 2),
                "reply_rate": round((replied / total_sent * 100) if total_sent > 0 else 0, 2),
                "avg_personalization_score": round(avg_personalization, 2)
            }

    def export_leads(
        self,
        format: str = "json",
        filters: Optional[Dict] = None
    ) -> str:
        """Export leads to JSON or CSV format"""
        leads = self.search_leads(**(filters or {}))
        data = [lead.to_dict() for lead in leads]

        if format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif format == "csv":
            if not data:
                return ""
            import csv
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()

        return json.dumps(data)
