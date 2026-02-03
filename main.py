#!/usr/bin/env python3
"""
AI Lead Generation Agent - Main Entry Point

Usage:
    python main.py search --keyword "spa" --location "TP.HCM"
    python main.py generate --keyword "cafe" --location "Quận 1"
    python main.py demo
    python main.py stats
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from dotenv import load_dotenv
from loguru import logger

from src.agent import LeadGenerationAgent
from src.agent.lead_agent import AgentConfig, AgentMode

# Load environment variables
load_dotenv()

# Setup
app = typer.Typer(
    name="lead-agent",
    help="AI Lead Generation Agent - Tìm kiếm và tiếp cận khách hàng tiềm năng"
)
console = Console()

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO"
)
logger.add(
    "logs/agent_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG"
)


def get_config() -> AgentConfig:
    """Get agent configuration from environment"""
    return AgentConfig(
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        sender_name=os.getenv("SENDER_NAME", "AI Agent"),
        company_name=os.getenv("COMPANY_NAME", "Your Company"),
        company_phone=os.getenv("COMPANY_PHONE", ""),
        company_website=os.getenv("COMPANY_WEBSITE", ""),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/leads.db"),
        max_leads_per_search=int(os.getenv("MAX_LEADS_PER_SEARCH", "50")),
        daily_email_limit=int(os.getenv("EMAIL_DAILY_LIMIT", "100")),
        use_ai_for_emails=os.getenv("USE_AI_FOR_EMAILS", "true").lower() == "true"
    )


@app.command()
def search(
    keyword: str = typer.Option(..., "--keyword", "-k", help="Từ khóa ngành nghề (vd: spa, cafe, nha khoa)"),
    location: str = typer.Option(..., "--location", "-l", help="Địa điểm (vd: TP.HCM, Quận 1)"),
    max_results: int = typer.Option(50, "--max", "-m", help="Số lượng kết quả tối đa"),
):
    """
    Tìm kiếm doanh nghiệp tiềm năng
    """
    console.print(Panel.fit(
        f"🔍 Tìm kiếm: [bold cyan]{keyword}[/] tại [bold green]{location}[/]",
        title="Lead Search"
    ))

    async def run():
        config = get_config()
        agent = LeadGenerationAgent(config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Đang tìm kiếm...", total=None)

            result = await agent.run(
                keyword=keyword,
                location=location,
                mode=AgentMode.SEARCH,
                max_leads=max_results
            )

            progress.update(task, description="Hoàn thành!")

        # Display results
        console.print(f"\n✅ Tìm thấy [bold green]{result.leads_found}[/] doanh nghiệp")
        console.print(f"📥 Đã lưu [bold cyan]{result.leads_added}[/] leads mới")

        if result.leads:
            table = Table(title="Danh sách Leads")
            table.add_column("Tên", style="cyan")
            table.add_column("Địa chỉ", style="white")
            table.add_column("Rating", justify="center")
            table.add_column("Email", style="green")

            for lead in result.leads[:10]:
                table.add_row(
                    lead.get("name", "N/A")[:30],
                    lead.get("address", "N/A")[:40],
                    str(lead.get("rating", "N/A")),
                    lead.get("email", "❌")
                )

            console.print(table)

    asyncio.run(run())


@app.command()
def generate(
    keyword: str = typer.Option(..., "--keyword", "-k", help="Từ khóa ngành nghề"),
    location: str = typer.Option(..., "--location", "-l", help="Địa điểm"),
    offer: str = typer.Option(None, "--offer", "-o", help="Offer tùy chỉnh"),
    campaign: str = typer.Option(None, "--campaign", "-c", help="Tên campaign"),
    max_results: int = typer.Option(20, "--max", "-m", help="Số lượng leads tối đa"),
):
    """
    Tìm kiếm, phân tích và tạo email cá nhân hóa
    """
    console.print(Panel.fit(
        f"🚀 Lead Generation Pipeline\n"
        f"Ngành: [bold cyan]{keyword}[/] | Vị trí: [bold green]{location}[/]",
        title="Generate Mode"
    ))

    async def run():
        config = get_config()
        agent = LeadGenerationAgent(config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Đang xử lý...", total=None)

            result = await agent.run(
                keyword=keyword,
                location=location,
                mode=AgentMode.GENERATE,
                campaign_name=campaign,
                offer=offer,
                max_leads=max_results
            )

            progress.update(task, description="Hoàn thành!")

        # Summary
        console.print("\n" + "="*50)
        console.print("[bold]📊 KẾT QUẢ[/]")
        console.print("="*50)
        console.print(f"🔍 Tìm thấy: [cyan]{result.leads_found}[/] doanh nghiệp")
        console.print(f"📥 Đã lưu: [green]{result.leads_added}[/] leads")
        console.print(f"📧 Email đã tạo: [yellow]{result.emails_generated}[/]")

        # Show sample emails
        if result.emails:
            console.print("\n[bold]📬 MẪU EMAIL ĐÃ TẠO:[/]\n")
            for i, email in enumerate(result.emails[:3], 1):
                console.print(Panel(
                    f"[bold]Subject:[/] {email.get('subject', 'N/A')}\n\n"
                    f"{email.get('body', 'N/A')[:500]}...\n\n"
                    f"[dim]Personalization Score: {email.get('personalization_score', 0)}/100[/]",
                    title=f"Email #{i} - {email.get('business_name', 'Unknown')}",
                    border_style="green"
                ))

    asyncio.run(run())


@app.command()
def outreach(
    keyword: str = typer.Option(..., "--keyword", "-k", help="Từ khóa ngành nghề"),
    location: str = typer.Option(..., "--location", "-l", help="Địa điểm"),
    campaign: str = typer.Option(..., "--campaign", "-c", help="Tên campaign"),
    limit: int = typer.Option(10, "--limit", help="Số email gửi tối đa"),
    dry_run: bool = typer.Option(True, "--dry-run/--send", help="Chỉ tạo, không gửi email"),
):
    """
    Pipeline đầy đủ: tìm kiếm, phân tích, tạo email và gửi
    """
    mode = AgentMode.GENERATE if dry_run else AgentMode.OUTREACH

    console.print(Panel.fit(
        f"📧 Outreach Campaign: [bold]{campaign}[/]\n"
        f"Mode: [yellow]{'DRY RUN (không gửi)' if dry_run else 'GỬI THẬT'}[/]",
        title="Outreach Mode"
    ))

    if not dry_run:
        confirm = typer.confirm("⚠️ Bạn có chắc muốn gửi email thật?")
        if not confirm:
            console.print("[yellow]Đã hủy.[/]")
            return

    async def run():
        config = get_config()
        config.daily_email_limit = limit
        agent = LeadGenerationAgent(config)

        result = await agent.run(
            keyword=keyword,
            location=location,
            mode=mode,
            campaign_name=campaign,
            max_leads=limit
        )

        console.print(f"\n✅ Emails generated: {result.emails_generated}")
        if not dry_run:
            console.print(f"📤 Emails sent: {result.emails_sent}")

    asyncio.run(run())


@app.command()
def follow_up():
    """
    Gửi email follow-up cho leads đã liên hệ
    """
    console.print(Panel.fit(
        "📨 Checking for pending follow-ups...",
        title="Follow-up Mode"
    ))

    async def run():
        config = get_config()
        agent = LeadGenerationAgent(config)

        result = await agent.run(
            keyword="",
            location="",
            mode=AgentMode.FOLLOW_UP
        )

        console.print(f"\n📧 Follow-up emails generated: {result.emails_generated}")

    asyncio.run(run())


@app.command()
def stats():
    """
    Hiển thị thống kê leads và emails
    """
    config = get_config()
    agent = LeadGenerationAgent(config)
    stats = agent.get_stats()

    # Lead stats table
    lead_table = Table(title="📊 Lead Statistics")
    lead_table.add_column("Metric", style="cyan")
    lead_table.add_column("Value", style="green")

    lead_stats = stats.get("leads", {})
    lead_table.add_row("Total Leads", str(lead_stats.get("total_leads", 0)))
    lead_table.add_row("Average Score", str(lead_stats.get("average_score", 0)))

    # By status
    by_status = lead_stats.get("by_status", {})
    for status, count in by_status.items():
        lead_table.add_row(f"  └ {status}", str(count))

    console.print(lead_table)

    # Email stats table
    email_table = Table(title="📧 Email Statistics")
    email_table.add_column("Metric", style="cyan")
    email_table.add_column("Value", style="green")

    email_stats = stats.get("emails", {})
    email_table.add_row("Total Sent", str(email_stats.get("total_sent", 0)))
    email_table.add_row("Opened", str(email_stats.get("opened", 0)))
    email_table.add_row("Replied", str(email_stats.get("replied", 0)))
    email_table.add_row("Open Rate", f"{email_stats.get('open_rate', 0)}%")
    email_table.add_row("Reply Rate", f"{email_stats.get('reply_rate', 0)}%")

    console.print(email_table)


@app.command()
def demo():
    """
    Chạy demo với dữ liệu mẫu
    """
    console.print(Panel.fit(
        "🎮 Running Demo Mode\nSử dụng dữ liệu mẫu để demo pipeline",
        title="Demo"
    ))

    async def run():
        config = get_config()
        agent = LeadGenerationAgent(config)

        result = await agent.run_demo(
            keyword="spa",
            location="Quận 1 TP.HCM"
        )

        # Display business info
        console.print("\n[bold]📋 THÔNG TIN DOANH NGHIỆP:[/]")
        business = result.get("business", {})
        console.print(f"  Tên: [cyan]{business.get('name')}[/]")
        console.print(f"  Địa chỉ: {business.get('address')}")
        console.print(f"  Rating: ⭐ {business.get('rating')}")
        console.print(f"  Email: {business.get('email')}")

        # Display analysis
        console.print("\n[bold]🔍 PHÂN TÍCH:[/]")
        analysis = result.get("analysis", {})
        console.print(f"  Lead Score: [green]{analysis.get('lead_score')}/100[/]")
        console.print(f"  Digital Maturity: {analysis.get('digital_maturity')}")
        console.print(f"  Pain Points:")
        for pp in analysis.get("pain_points", []):
            console.print(f"    • {pp}")
        console.print(f"  Recommended Offer: [yellow]{analysis.get('recommended_offer')}[/]")

        # Display email
        console.print("\n[bold]📧 EMAIL ĐÃ TẠO:[/]")
        email = result.get("email", {})
        console.print(Panel(
            f"[bold]Subject:[/] {email.get('subject')}\n\n"
            f"{email.get('body')}\n\n"
            f"[dim]Personalization Score: {email.get('personalization_score')}/100[/]",
            border_style="green"
        ))

    asyncio.run(run())


@app.command()
def export(
    format: str = typer.Option("json", "--format", "-f", help="Format: json hoặc csv"),
    output: str = typer.Option("leads_export", "--output", "-o", help="Tên file output"),
):
    """
    Export leads ra file
    """
    config = get_config()
    agent = LeadGenerationAgent(config)

    data = agent.export_leads(format=format)

    ext = "json" if format == "json" else "csv"
    filename = f"{output}.{ext}"

    Path("data").mkdir(exist_ok=True)
    filepath = Path("data") / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(data)

    console.print(f"✅ Exported to [green]{filepath}[/]")


@app.command()
def init():
    """
    Khởi tạo môi trường và database
    """
    console.print("[bold]🚀 Initializing AI Lead Generation Agent...[/]\n")

    # Create directories
    dirs = ["data", "logs", "templates"]
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        console.print(f"  ✓ Created {dir_name}/")

    # Create .env if not exists
    env_file = Path(".env")
    if not env_file.exists():
        env_example = Path(".env.example")
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            console.print("  ✓ Created .env from .env.example")
        else:
            console.print("  ⚠ .env.example not found")

    # Initialize database
    from src.database import Database
    db = Database()
    console.print("  ✓ Database initialized")

    console.print("\n[green]✅ Initialization complete![/]")
    console.print("\n[dim]Next steps:[/]")
    console.print("  1. Edit .env with your API keys")
    console.print("  2. Run: python main.py demo")
    console.print("  3. Run: python main.py search --keyword spa --location 'TP.HCM'")


if __name__ == "__main__":
    app()
