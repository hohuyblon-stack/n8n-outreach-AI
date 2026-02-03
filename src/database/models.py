"""
Database Models - SQLAlchemy models for lead management
"""
from datetime import datetime
from typing import Optional, List
import json

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey,
    Enum as SQLEnum, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

Base = declarative_base()


class Lead(Base):
    """Lead/Business record in the database"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    unique_id = Column(String(20), unique=True, nullable=False, index=True)

    # Basic Info
    name = Column(String(255), nullable=False)
    address = Column(Text)
    phone = Column(String(20))
    email = Column(String(255), index=True)
    website = Column(String(500))

    # Location
    city = Column(String(100))
    district = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)

    # Business Details
    industry = Column(String(100), index=True)
    category = Column(String(255))
    description = Column(Text)
    services = Column(JSON)  # List of services
    products = Column(JSON)  # List of products

    # Online Presence
    google_maps_url = Column(String(500))
    facebook_url = Column(String(500))
    instagram_url = Column(String(500))
    zalo_url = Column(String(500))

    # Reviews & Ratings
    rating = Column(Float)
    review_count = Column(Integer)
    reviews = Column(JSON)  # List of review dicts

    # Business Hours
    opening_hours = Column(JSON)

    # Photos
    photo_urls = Column(JSON)

    # Metadata
    source = Column(String(50), default="google_maps")
    scraped_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Lead Status
    status = Column(String(20), default="new", index=True)
    # new, contacted, responded, qualified, not_interested, converted

    # Scoring
    lead_score = Column(Integer, default=0)
    digital_maturity_score = Column(Integer, default=0)
    lead_quality = Column(String(20))  # hot, warm, cold, unqualified

    # Contact Tracking
    contact_attempts = Column(Integer, default=0)
    last_contacted = Column(DateTime)
    next_contact_date = Column(DateTime)
    preferred_channel = Column(String(20))

    # Analysis Results
    pain_points = Column(JSON)
    opportunities = Column(JSON)
    recommended_offer = Column(Text)
    personalization_hooks = Column(JSON)

    # Notes
    notes = Column(JSON)  # List of timestamped notes

    # Campaign relationship
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    campaign = relationship("Campaign", back_populates="leads")

    # Email records
    emails = relationship("EmailRecord", back_populates="lead", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_leads_industry_city", "industry", "city"),
        Index("idx_leads_status_score", "status", "lead_score"),
    )

    @hybrid_property
    def has_contact_info(self) -> bool:
        return bool(self.phone or self.email)

    @hybrid_property
    def has_social_media(self) -> bool:
        return bool(self.facebook_url or self.instagram_url or self.zalo_url)

    def add_note(self, note: str):
        """Add a timestamped note"""
        if self.notes is None:
            self.notes = []
        self.notes.append({
            "text": note,
            "timestamp": datetime.utcnow().isoformat()
        })

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "unique_id": self.unique_id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "city": self.city,
            "district": self.district,
            "industry": self.industry,
            "rating": self.rating,
            "review_count": self.review_count,
            "status": self.status,
            "lead_score": self.lead_score,
            "lead_quality": self.lead_quality,
            "contact_attempts": self.contact_attempts,
            "last_contacted": self.last_contacted.isoformat() if self.last_contacted else None,
            "recommended_offer": self.recommended_offer,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
        }


class EmailRecord(Base):
    """Record of emails sent to leads"""
    __tablename__ = "email_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)

    # Email Content
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    email_type = Column(String(50))  # first_contact, follow_up_1, etc.

    # Recipient
    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(255))

    # Personalization
    personalization_score = Column(Integer, default=0)

    # Status
    status = Column(String(20), default="draft")
    # draft, scheduled, sent, delivered, opened, clicked, replied, bounced

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_at = Column(DateTime)
    sent_at = Column(DateTime)
    opened_at = Column(DateTime)
    replied_at = Column(DateTime)

    # Tracking
    open_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)

    # Campaign relationship
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))

    # Lead relationship
    lead = relationship("Lead", back_populates="emails")

    # Indexes
    __table_args__ = (
        Index("idx_email_status_type", "status", "email_type"),
    )

    def mark_sent(self):
        """Mark email as sent"""
        self.status = "sent"
        self.sent_at = datetime.utcnow()

    def mark_opened(self):
        """Mark email as opened"""
        if self.status in ["sent", "delivered"]:
            self.status = "opened"
        if not self.opened_at:
            self.opened_at = datetime.utcnow()
        self.open_count += 1

    def mark_replied(self):
        """Mark email as replied"""
        self.status = "replied"
        self.replied_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "subject": self.subject,
            "email_type": self.email_type,
            "recipient_email": self.recipient_email,
            "status": self.status,
            "personalization_score": self.personalization_score,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "replied_at": self.replied_at.isoformat() if self.replied_at else None,
        }


class Campaign(Base):
    """Outreach campaign"""
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Campaign Info
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Targeting
    industry = Column(String(100))
    location = Column(String(255))
    search_keywords = Column(JSON)  # List of keywords

    # Settings
    daily_email_limit = Column(Integer, default=50)
    email_sequence_enabled = Column(Boolean, default=True)
    follow_up_days = Column(JSON, default=[3, 7])  # Days between follow-ups

    # Offer
    offer_template = Column(Text)

    # Status
    status = Column(String(20), default="draft")
    # draft, active, paused, completed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Stats
    total_leads = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    replies_received = Column(Integer, default=0)
    conversions = Column(Integer, default=0)

    # Relationships
    leads = relationship("Lead", back_populates="campaign")

    @hybrid_property
    def open_rate(self) -> float:
        if self.emails_sent == 0:
            return 0.0
        return (self.emails_opened / self.emails_sent) * 100

    @hybrid_property
    def reply_rate(self) -> float:
        if self.emails_sent == 0:
            return 0.0
        return (self.replies_received / self.emails_sent) * 100

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "industry": self.industry,
            "location": self.location,
            "status": self.status,
            "total_leads": self.total_leads,
            "emails_sent": self.emails_sent,
            "emails_opened": self.emails_opened,
            "replies_received": self.replies_received,
            "open_rate": round(self.open_rate, 2),
            "reply_rate": round(self.reply_rate, 2),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
