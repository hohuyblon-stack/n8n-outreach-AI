"""
Simple Web Dashboard - Monitor leads and scheduler
"""
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.database import Database
from src.scheduler import AgentScheduler


# HTML Template with embedded CSS and JS
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Lead Agent Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid #333;
            margin-bottom: 30px;
        }
        h1 {
            font-size: 24px;
            color: #fff;
        }
        h1 span {
            color: #00d9ff;
        }
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }
        .status-running {
            background: rgba(0, 255, 136, 0.2);
            color: #00ff88;
            border: 1px solid #00ff88;
        }
        .status-stopped {
            background: rgba(255, 68, 68, 0.2);
            color: #ff4444;
            border: 1px solid #ff4444;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 24px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0, 217, 255, 0.15);
        }
        .stat-card h3 {
            font-size: 14px;
            color: #888;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stat-card .value {
            font-size: 36px;
            font-weight: 700;
            color: #fff;
        }
        .stat-card .value.highlight {
            color: #00d9ff;
        }
        .stat-card .change {
            font-size: 12px;
            margin-top: 8px;
        }
        .change.positive { color: #00ff88; }
        .change.negative { color: #ff4444; }

        .section {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .section h2 {
            font-size: 18px;
            margin-bottom: 20px;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .section h2::before {
            content: '';
            width: 4px;
            height: 20px;
            background: #00d9ff;
            border-radius: 2px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        th {
            color: #888;
            font-weight: 500;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        tr:hover {
            background: rgba(255, 255, 255, 0.02);
        }
        .quality-badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }
        .quality-hot {
            background: rgba(255, 68, 68, 0.2);
            color: #ff6b6b;
        }
        .quality-warm {
            background: rgba(255, 193, 7, 0.2);
            color: #ffc107;
        }
        .quality-cold {
            background: rgba(100, 149, 237, 0.2);
            color: #6495ed;
        }

        .job-list {
            display: grid;
            gap: 12px;
        }
        .job-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 8px;
        }
        .job-info {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .job-status {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        .job-status.active { background: #00ff88; }
        .job-status.inactive { background: #666; }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #00d9ff;
            color: #1a1a2e;
        }
        .btn-primary:hover {
            background: #00b8d9;
        }
        .btn-danger {
            background: rgba(255, 68, 68, 0.2);
            color: #ff4444;
            border: 1px solid #ff4444;
        }

        .actions {
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
        }

        .refresh-info {
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 20px;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .loading {
            animation: pulse 1.5s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 AI Lead <span>Agent</span></h1>
            <div class="status-badge {{ 'status-running' if scheduler_running else 'status-stopped' }}">
                {{ '● Running' if scheduler_running else '○ Stopped' }}
            </div>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Leads</h3>
                <div class="value highlight">{{ stats.leads.total_leads }}</div>
            </div>
            <div class="stat-card">
                <h3>Emails Sent</h3>
                <div class="value">{{ stats.emails.total_sent }}</div>
            </div>
            <div class="stat-card">
                <h3>Open Rate</h3>
                <div class="value">{{ stats.emails.open_rate }}%</div>
            </div>
            <div class="stat-card">
                <h3>Reply Rate</h3>
                <div class="value">{{ stats.emails.reply_rate }}%</div>
            </div>
            <div class="stat-card">
                <h3>Hot Leads</h3>
                <div class="value highlight">{{ stats.leads.by_quality.get('hot', 0) }}</div>
            </div>
            <div class="stat-card">
                <h3>Avg Score</h3>
                <div class="value">{{ stats.leads.average_score }}</div>
            </div>
        </div>

        <div class="section">
            <h2>Scheduled Jobs</h2>
            <div class="job-list">
                {% for job in jobs %}
                <div class="job-item">
                    <div class="job-info">
                        <div class="job-status {{ 'active' if job.enabled else 'inactive' }}"></div>
                        <div>
                            <strong>{{ job.name }}</strong>
                            <div style="color: #666; font-size: 12px;">
                                Last run: {{ job.last_run or 'Never' }}
                            </div>
                        </div>
                    </div>
                    <button class="btn btn-primary" onclick="runJob('{{ job.name }}')">
                        Run Now
                    </button>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="section">
            <h2>Recent Hot Leads</h2>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Industry</th>
                        <th>Score</th>
                        <th>Quality</th>
                        <th>Email</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for lead in hot_leads %}
                    <tr>
                        <td><strong>{{ lead.name }}</strong></td>
                        <td>{{ lead.industry or 'N/A' }}</td>
                        <td>{{ lead.lead_score }}/100</td>
                        <td>
                            <span class="quality-badge quality-{{ lead.lead_quality }}">
                                {{ lead.lead_quality }}
                            </span>
                        </td>
                        <td>{{ lead.email or '—' }}</td>
                        <td>{{ lead.status }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Lead Distribution by Status</h2>
            <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));">
                {% for status, count in stats.leads.by_status.items() %}
                <div class="stat-card">
                    <h3>{{ status }}</h3>
                    <div class="value">{{ count }}</div>
                </div>
                {% endfor %}
            </div>
        </div>

        <p class="refresh-info">
            Auto-refresh every 30 seconds • Last updated: {{ current_time }}
        </p>
    </div>

    <script>
        // Auto refresh
        setTimeout(() => location.reload(), 30000);

        function runJob(jobName) {
            fetch('/api/scheduler/run-job', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({job_name: jobName})
            })
            .then(r => r.json())
            .then(data => {
                alert(data.message || 'Job triggered!');
                location.reload();
            })
            .catch(e => alert('Error: ' + e));
        }
    </script>
</body>
</html>
"""


def create_dashboard_app(
    db: Database,
    scheduler: Optional[AgentScheduler] = None
) -> FastAPI:
    """
    Create FastAPI app with dashboard

    Args:
        db: Database instance
        scheduler: Optional scheduler instance

    Returns:
        FastAPI app
    """
    app = FastAPI(title="AI Lead Agent Dashboard")

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """Render dashboard HTML"""
        # Get stats
        stats = {
            "leads": db.get_lead_stats(),
            "emails": db.get_email_stats()
        }

        # Get scheduler jobs
        jobs = []
        scheduler_running = False
        if scheduler:
            scheduler_running = scheduler.running
            jobs = [
                {
                    "name": job.name,
                    "enabled": job.enabled,
                    "last_run": job.last_run.strftime("%Y-%m-%d %H:%M") if job.last_run else None
                }
                for job in scheduler.jobs
            ]

        # Get hot leads
        hot_leads = db.search_leads(min_score=70, limit=10)
        hot_leads_data = [lead.to_dict() for lead in hot_leads]

        # Simple template rendering (no Jinja2 dependency)
        html = DASHBOARD_HTML
        html = html.replace("{{ stats.leads.total_leads }}", str(stats["leads"].get("total_leads", 0)))
        html = html.replace("{{ stats.emails.total_sent }}", str(stats["emails"].get("total_sent", 0)))
        html = html.replace("{{ stats.emails.open_rate }}", str(stats["emails"].get("open_rate", 0)))
        html = html.replace("{{ stats.emails.reply_rate }}", str(stats["emails"].get("reply_rate", 0)))
        html = html.replace("{{ stats.leads.by_quality.get('hot', 0) }}", str(stats["leads"].get("by_quality", {}).get("hot", 0)))
        html = html.replace("{{ stats.leads.average_score }}", str(stats["leads"].get("average_score", 0)))
        html = html.replace("{{ current_time }}", datetime.now().strftime("%H:%M:%S"))

        # Replace scheduler status
        if scheduler_running:
            html = html.replace("{{ 'status-running' if scheduler_running else 'status-stopped' }}", "status-running")
            html = html.replace("{{ '● Running' if scheduler_running else '○ Stopped' }}", "● Running")
        else:
            html = html.replace("{{ 'status-running' if scheduler_running else 'status-stopped' }}", "status-stopped")
            html = html.replace("{{ '● Running' if scheduler_running else '○ Stopped' }}", "○ Stopped")

        # Generate jobs HTML
        jobs_html = ""
        for job in jobs:
            job_status = "active" if job["enabled"] else "inactive"
            jobs_html += f"""
            <div class="job-item">
                <div class="job-info">
                    <div class="job-status {job_status}"></div>
                    <div>
                        <strong>{job["name"]}</strong>
                        <div style="color: #666; font-size: 12px;">
                            Last run: {job["last_run"] or "Never"}
                        </div>
                    </div>
                </div>
                <button class="btn btn-primary" onclick="runJob('{job["name"]}')">
                    Run Now
                </button>
            </div>
            """

        # Replace jobs section
        html = html.replace(
            """{% for job in jobs %}
                <div class="job-item">
                    <div class="job-info">
                        <div class="job-status {{ 'active' if job.enabled else 'inactive' }}"></div>
                        <div>
                            <strong>{{ job.name }}</strong>
                            <div style="color: #666; font-size: 12px;">
                                Last run: {{ job.last_run or 'Never' }}
                            </div>
                        </div>
                    </div>
                    <button class="btn btn-primary" onclick="runJob('{{ job.name }}')">
                        Run Now
                    </button>
                </div>
                {% endfor %}""",
            jobs_html
        )

        # Generate leads HTML
        leads_html = ""
        for lead in hot_leads_data:
            quality = lead.get("lead_quality", "cold")
            leads_html += f"""
            <tr>
                <td><strong>{lead.get("name", "N/A")}</strong></td>
                <td>{lead.get("industry") or "N/A"}</td>
                <td>{lead.get("lead_score", 0)}/100</td>
                <td>
                    <span class="quality-badge quality-{quality}">
                        {quality}
                    </span>
                </td>
                <td>{lead.get("email") or "—"}</td>
                <td>{lead.get("status", "new")}</td>
            </tr>
            """

        html = html.replace(
            """{% for lead in hot_leads %}
                    <tr>
                        <td><strong>{{ lead.name }}</strong></td>
                        <td>{{ lead.industry or 'N/A' }}</td>
                        <td>{{ lead.lead_score }}/100</td>
                        <td>
                            <span class="quality-badge quality-{{ lead.lead_quality }}">
                                {{ lead.lead_quality }}
                            </span>
                        </td>
                        <td>{{ lead.email or '—' }}</td>
                        <td>{{ lead.status }}</td>
                    </tr>
                    {% endfor %}""",
            leads_html
        )

        # Generate status distribution
        status_html = ""
        for status, count in stats["leads"].get("by_status", {}).items():
            status_html += f"""
            <div class="stat-card">
                <h3>{status}</h3>
                <div class="value">{count}</div>
            </div>
            """

        html = html.replace(
            """{% for status, count in stats.leads.by_status.items() %}
                <div class="stat-card">
                    <h3>{{ status }}</h3>
                    <div class="value">{{ count }}</div>
                </div>
                {% endfor %}""",
            status_html
        )

        return HTMLResponse(content=html)

    @app.post("/api/scheduler/run-job")
    async def run_job(request: Request):
        """Manually trigger a job"""
        data = await request.json()
        job_name = data.get("job_name")

        if scheduler and scheduler.run_job_now(job_name):
            return {"success": True, "message": f"Job '{job_name}' triggered"}
        return {"success": False, "message": "Job not found or scheduler not running"}

    return app
