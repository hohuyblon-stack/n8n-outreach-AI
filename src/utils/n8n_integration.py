"""
N8N Integration - Connect with n8n workflows for automation
"""
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

import httpx
from loguru import logger


class N8NIntegration:
    """
    Integration with n8n automation platform

    Features:
    - Trigger workflows via webhooks
    - Send lead data to n8n
    - Receive webhook callbacks
    - Sync with n8n database nodes

    Usage:
        n8n = N8NIntegration(webhook_url="http://localhost:5678/webhook/lead-agent")
        await n8n.trigger_workflow("new_lead", lead_data)
    """

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:5678"
    ):
        """
        Initialize N8N integration

        Args:
            webhook_url: URL for webhook triggers
            api_key: N8N API key for authenticated requests
            base_url: N8N instance base URL
        """
        self.webhook_url = webhook_url
        self.api_key = api_key
        self.base_url = base_url

        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=self._get_headers()
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["X-N8N-API-KEY"] = self.api_key
        return headers

    async def trigger_webhook(
        self,
        event_type: str,
        data: Dict[str, Any],
        webhook_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trigger an n8n webhook

        Args:
            event_type: Type of event (e.g., "new_lead", "email_sent")
            data: Payload data
            webhook_path: Custom webhook path (overrides default)

        Returns:
            Response from n8n
        """
        url = webhook_path or self.webhook_url

        if not url:
            logger.warning("No webhook URL configured")
            return {"success": False, "error": "No webhook URL"}

        payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()

            logger.info(f"Webhook triggered: {event_type}")
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.json() if response.text else {}
            }

        except httpx.HTTPError as e:
            logger.error(f"Webhook error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def send_new_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send new lead to n8n for processing"""
        return await self.trigger_webhook("new_lead", lead_data)

    async def send_email_event(
        self,
        event: str,
        email_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send email event to n8n

        Events: email_generated, email_sent, email_opened, email_replied
        """
        return await self.trigger_webhook(f"email_{event}", email_data)

    async def send_batch_leads(
        self,
        leads: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Send multiple leads in batch"""
        return await self.trigger_webhook("batch_leads", {"leads": leads})

    async def request_analysis(
        self,
        business_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Request AI analysis from n8n workflow"""
        return await self.trigger_webhook("request_analysis", business_data)

    async def check_workflow_status(
        self,
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Check status of a workflow execution

        Requires n8n API access
        """
        if not self.api_key:
            return {"error": "API key required"}

        url = f"{self.base_url}/api/v1/executions/{execution_id}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"API error: {e}")
            return {"error": str(e)}

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# ==================== N8N WORKFLOW TEMPLATES ====================

N8N_WORKFLOW_TEMPLATES = {
    "lead_capture": {
        "name": "Lead Capture Workflow",
        "description": "Receives new leads and stores them in database",
        "nodes": [
            {
                "type": "n8n-nodes-base.webhook",
                "name": "Webhook",
                "parameters": {
                    "httpMethod": "POST",
                    "path": "lead-capture"
                }
            },
            {
                "type": "n8n-nodes-base.set",
                "name": "Format Data",
                "parameters": {
                    "values": {
                        "string": [
                            {"name": "name", "value": "={{$json.data.name}}"},
                            {"name": "email", "value": "={{$json.data.email}}"}
                        ]
                    }
                }
            },
            {
                "type": "n8n-nodes-base.postgres",
                "name": "Save to DB",
                "parameters": {
                    "operation": "insert",
                    "table": "leads"
                }
            }
        ]
    },

    "email_sequence": {
        "name": "Email Sequence Workflow",
        "description": "Automated email follow-up sequence",
        "nodes": [
            {
                "type": "n8n-nodes-base.scheduleTrigger",
                "name": "Daily Check",
                "parameters": {
                    "rule": {"interval": [{"field": "hours", "hoursInterval": 24}]}
                }
            },
            {
                "type": "n8n-nodes-base.postgres",
                "name": "Get Pending Emails",
                "parameters": {
                    "operation": "executeQuery",
                    "query": "SELECT * FROM leads WHERE status = 'contacted' AND last_contacted < NOW() - INTERVAL '3 days'"
                }
            },
            {
                "type": "n8n-nodes-base.httpRequest",
                "name": "Generate Email",
                "parameters": {
                    "method": "POST",
                    "url": "http://localhost:8000/generate-email"
                }
            },
            {
                "type": "n8n-nodes-base.gmail",
                "name": "Send Email",
                "parameters": {
                    "sendTo": "={{$json.email}}",
                    "subject": "={{$json.subject}}",
                    "message": "={{$json.body}}"
                }
            }
        ]
    },

    "lead_scoring": {
        "name": "AI Lead Scoring Workflow",
        "description": "Score leads using AI analysis",
        "nodes": [
            {
                "type": "n8n-nodes-base.webhook",
                "name": "New Lead Webhook",
                "parameters": {
                    "httpMethod": "POST",
                    "path": "score-lead"
                }
            },
            {
                "type": "n8n-nodes-base.openAi",
                "name": "AI Analysis",
                "parameters": {
                    "operation": "complete",
                    "prompt": "Analyze this business and score from 0-100..."
                }
            },
            {
                "type": "n8n-nodes-base.postgres",
                "name": "Update Score",
                "parameters": {
                    "operation": "update",
                    "table": "leads"
                }
            }
        ]
    }
}


def get_workflow_template(workflow_name: str) -> Optional[Dict]:
    """Get a workflow template by name"""
    return N8N_WORKFLOW_TEMPLATES.get(workflow_name)


def export_workflow_json(workflow_name: str) -> str:
    """Export workflow template as JSON for import into n8n"""
    template = N8N_WORKFLOW_TEMPLATES.get(workflow_name)
    if not template:
        return "{}"
    return json.dumps(template, indent=2)
