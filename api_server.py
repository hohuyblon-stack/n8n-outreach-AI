#!/usr/bin/env python3
"""
FastAPI Server for AI Lead Generation Agent

Provides REST API endpoints for n8n integration and external access.

Usage:
    uvicorn api_server:app --reload --port 8000
"""
import asyncio
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from loguru import logger

# Load environment
load_dotenv()

# Import agent modules
from src.agent import LeadGenerationAgent
from src.agent.lead_agent import AgentConfig, AgentMode
from src.database import Database
from src.analyzer import BusinessAnalyzer
from src.email_generator import EmailGenerator, EmailType
from src.scraper import ScrapedBusiness

# Initialize FastAPI app
app = FastAPI(
    title="AI Lead Generation Agent API",
    description="API for automated lead generation and personalized outreach",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
db = Database(os.getenv("DATABASE_URL", "sqlite:///./data/leads.db"))
analyzer = BusinessAnalyzer()


def get_config() -> AgentConfig:
    """Get agent configuration from environment"""
    return AgentConfig(
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        sender_name=os.getenv("SENDER_NAME", "AI Agent"),
        company_name=os.getenv("COMPANY_NAME", "Your Company"),
        company_phone=os.getenv("COMPANY_PHONE", ""),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/leads.db")
    )


# ==================== REQUEST/RESPONSE MODELS ====================

class SearchRequest(BaseModel):
    keyword: str = Field(..., description="Business type keyword (e.g., 'spa', 'cafe')")
    location: str = Field(..., description="Location (e.g., 'TP.HCM', 'Quận 1')")
    max_results: int = Field(50, ge=1, le=200)
    campaign_name: Optional[str] = None


class GenerateRequest(BaseModel):
    keyword: str
    location: str
    max_results: int = 20
    campaign_name: Optional[str] = None
    custom_offer: Optional[str] = None


class EmailGenerateRequest(BaseModel):
    lead_id: int
    email_type: str = "first_contact"


class LeadUpdateRequest(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None
    lead_score: Optional[int] = None


class AnalyzeRequest(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None


# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Lead Generation Agent",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/stats")
async def get_stats():
    """Get overall statistics"""
    lead_stats = db.get_lead_stats()
    email_stats = db.get_email_stats()

    return {
        "leads": lead_stats,
        "emails": email_stats
    }


# ==================== LEAD ENDPOINTS ====================

@app.post("/api/search")
async def search_leads(request: SearchRequest, background_tasks: BackgroundTasks):
    """
    Search for leads (async operation)

    Returns immediately with job ID, results saved to database
    """
    config = get_config()
    agent = LeadGenerationAgent(config)

    # Run in background
    async def run_search():
        result = await agent.run(
            keyword=request.keyword,
            location=request.location,
            mode=AgentMode.SEARCH,
            campaign_name=request.campaign_name,
            max_leads=request.max_results
        )
        logger.info(f"Search completed: {result.leads_found} leads found")

    background_tasks.add_task(asyncio.create_task, run_search())

    return {
        "status": "started",
        "message": f"Searching for '{request.keyword}' in '{request.location}'",
        "max_results": request.max_results
    }


@app.post("/api/generate")
async def generate_leads(request: GenerateRequest):
    """
    Full pipeline: search, analyze, and generate emails
    """
    config = get_config()
    agent = LeadGenerationAgent(config)

    result = await agent.run(
        keyword=request.keyword,
        location=request.location,
        mode=AgentMode.GENERATE,
        campaign_name=request.campaign_name,
        offer=request.custom_offer,
        max_leads=request.max_results
    )

    return {
        "success": result.success,
        "leads_found": result.leads_found,
        "leads_added": result.leads_added,
        "emails_generated": result.emails_generated,
        "leads": result.leads[:20],  # Limit response size
        "emails": result.emails[:10]
    }


@app.get("/api/leads")
async def list_leads(
    industry: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
    min_score: Optional[int] = None,
    has_email: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get leads with filters"""
    leads = db.search_leads(
        industry=industry,
        city=city,
        status=status,
        min_score=min_score,
        has_email=has_email,
        limit=limit,
        offset=offset
    )

    return {
        "count": len(leads),
        "leads": [lead.to_dict() for lead in leads]
    }


@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: int):
    """Get a specific lead by ID"""
    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead.to_dict()


@app.patch("/api/leads/{lead_id}")
async def update_lead(lead_id: int, request: LeadUpdateRequest):
    """Update a lead"""
    updates = {}
    if request.status:
        updates["status"] = request.status
    if request.lead_score is not None:
        updates["lead_score"] = request.lead_score

    if request.note:
        db.update_lead_status(lead_id, request.status or "contacted", request.note)
    elif updates:
        db.update_lead(lead_id, **updates)

    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead.to_dict()


@app.post("/api/leads/{lead_id}/contact")
async def mark_contacted(lead_id: int):
    """Mark a lead as contacted"""
    lead = db.mark_lead_contacted(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True, "contact_attempts": lead.contact_attempts}


# ==================== EMAIL ENDPOINTS ====================

@app.post("/api/generate-email")
async def generate_email(request: EmailGenerateRequest):
    """Generate a personalized email for a lead"""
    lead = db.get_lead(request.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Convert lead to ScrapedBusiness
    business = ScrapedBusiness(
        name=lead.name,
        address=lead.address or "",
        phone=lead.phone,
        email=lead.email,
        website=lead.website,
        industry=lead.industry,
        rating=lead.rating,
        review_count=lead.review_count
    )

    # Analyze
    analysis = analyzer.analyze(business)

    # Determine email type
    email_type_map = {
        "first_contact": EmailType.FIRST_CONTACT,
        "follow_up_1": EmailType.FOLLOW_UP_1,
        "follow_up_2": EmailType.FOLLOW_UP_2
    }
    email_type = email_type_map.get(request.email_type, EmailType.FIRST_CONTACT)

    # Generate email
    config = get_config()
    email_gen = EmailGenerator(
        sender_name=config.sender_name,
        company_name=config.company_name,
        company_phone=config.company_phone
    )

    email = email_gen.generate(
        business=business,
        analysis=analysis,
        email_type=email_type,
        use_ai=False  # Use templates for API
    )

    return {
        "lead_id": lead.id,
        "recipient_email": lead.email,
        "subject": email.subject,
        "body": email.body,
        "email_type": request.email_type,
        "personalization_score": email.personalization_score
    }


@app.get("/api/pending-followups")
async def get_pending_followups(
    days_since_last: int = 3,
    limit: int = 50
):
    """Get leads that need follow-up emails"""
    pending = db.get_pending_follow_ups(
        days_since_last=days_since_last,
        limit=limit
    )

    return {
        "count": len(pending),
        "leads": [
            {
                "lead_id": item["lead"].id,
                "name": item["lead"].name,
                "email": item["lead"].email,
                "last_sent": item["last_sent"].isoformat() if item["last_sent"] else None,
                "email_count": item["email_count"]
            }
            for item in pending
        ]
    }


@app.get("/api/leads/{lead_id}/emails")
async def get_lead_emails(lead_id: int):
    """Get all emails sent to a lead"""
    emails = db.get_emails_for_lead(lead_id)
    return {
        "lead_id": lead_id,
        "count": len(emails),
        "emails": [email.to_dict() for email in emails]
    }


# ==================== ANALYSIS ENDPOINT ====================

@app.post("/api/analyze")
async def analyze_business(request: AnalyzeRequest):
    """
    Analyze a business and return lead score and recommendations

    Useful for n8n workflows that need AI analysis
    """
    business = ScrapedBusiness(
        name=request.name,
        address=request.address,
        phone=request.phone,
        email=request.email,
        website=request.website,
        industry=request.industry,
        rating=request.rating,
        review_count=request.review_count
    )

    analysis = analyzer.analyze(business)

    return {
        "business_name": request.name,
        "lead_score": analysis.lead_score,
        "lead_quality": analysis.lead_quality.value,
        "digital_maturity": analysis.digital_maturity.value,
        "pain_points": analysis.pain_points,
        "opportunities": analysis.opportunities,
        "recommended_services": analysis.recommended_services,
        "recommended_offer": analysis.recommended_offer,
        "best_contact_channel": analysis.best_channel,
        "urgency_level": analysis.urgency_level,
        "summary": analysis.summary
    }


# ==================== CAMPAIGN ENDPOINTS ====================

@app.get("/api/campaigns")
async def list_campaigns(status: Optional[str] = None):
    """List all campaigns"""
    campaigns = db.get_all_campaigns(status=status)
    return {
        "count": len(campaigns),
        "campaigns": [c.to_dict() for c in campaigns]
    }


@app.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: int):
    """Get campaign details"""
    campaign = db.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign.to_dict()


# ==================== WEBHOOK ENDPOINT ====================

@app.post("/webhook/lead-capture")
async def webhook_lead_capture(data: Dict[str, Any]):
    """
    Webhook endpoint for receiving leads from external sources

    Expected payload:
    {
        "name": "Business Name",
        "email": "contact@example.com",
        "phone": "0901234567",
        "industry": "spa",
        "source": "landing_page"
    }
    """
    try:
        business = ScrapedBusiness(
            name=data.get("name", "Unknown"),
            address=data.get("address", ""),
            email=data.get("email"),
            phone=data.get("phone"),
            website=data.get("website"),
            industry=data.get("industry"),
            source=data.get("source", "webhook")
        )

        # Analyze
        analysis = analyzer.analyze(business)

        # Save to database
        lead = db.add_lead(business, analysis)

        if lead:
            return {
                "success": True,
                "lead_id": lead.id,
                "lead_score": analysis.lead_score,
                "message": "Lead captured successfully"
            }
        else:
            return {
                "success": False,
                "message": "Duplicate lead"
            }

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== EXPORT ENDPOINT ====================

@app.get("/api/export")
async def export_leads(format: str = "json"):
    """Export all leads"""
    data = db.export_leads(format=format)

    return {
        "format": format,
        "data": data if format == "json" else None,
        "csv": data if format == "csv" else None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
