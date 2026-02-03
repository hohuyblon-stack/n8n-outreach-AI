"""
Configuration settings for AI Lead Generation Agent
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Project Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"

    # API Keys
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    google_maps_api_key: Optional[str] = Field(None, alias="GOOGLE_MAPS_API_KEY")

    # Email Configuration
    smtp_host: str = Field("smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(587, alias="SMTP_PORT")
    smtp_username: Optional[str] = Field(None, alias="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(None, alias="SMTP_PASSWORD")
    sender_name: str = Field("AI Agent", alias="SENDER_NAME")
    sender_email: Optional[str] = Field(None, alias="SENDER_EMAIL")

    # N8N Integration
    n8n_webhook_url: Optional[str] = Field(None, alias="N8N_WEBHOOK_URL")
    n8n_api_key: Optional[str] = Field(None, alias="N8N_API_KEY")

    # Database
    database_url: str = Field("sqlite:///./data/leads.db", alias="DATABASE_URL")

    # Agent Configuration
    default_language: str = Field("vi", alias="DEFAULT_LANGUAGE")
    max_leads_per_search: int = Field(50, alias="MAX_LEADS_PER_SEARCH")
    email_daily_limit: int = Field(100, alias="EMAIL_DAILY_LIMIT")
    delay_between_requests: int = Field(2, alias="DELAY_BETWEEN_REQUESTS")

    # Company Info
    company_name: str = Field("Your Company", alias="COMPANY_NAME")
    company_website: str = Field("https://example.com", alias="COMPANY_WEBSITE")
    company_phone: str = Field("", alias="COMPANY_PHONE")

    # LLM Settings
    llm_model: str = Field("gpt-4-turbo-preview", alias="LLM_MODEL")
    llm_temperature: float = Field(0.7, alias="LLM_TEMPERATURE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()


# Industry mappings for Vietnamese market
INDUSTRY_KEYWORDS_VI = {
    "spa": ["spa", "massage", "làm đẹp", "thẩm mỹ", "skincare", "chăm sóc da"],
    "cafe": ["café", "cafe", "quán cà phê", "coffee", "trà sữa", "quán nước"],
    "nha_khoa": ["nha khoa", "dental", "răng", "implant", "niềng răng", "phòng khám nha"],
    "gym": ["gym", "fitness", "phòng tập", "yoga", "pilates", "thể hình"],
    "nha_hang": ["nhà hàng", "restaurant", "quán ăn", "ẩm thực", "buffet"],
    "khach_san": ["khách sạn", "hotel", "resort", "homestay", "lưu trú"],
    "bat_dong_san": ["bất động sản", "real estate", "nhà đất", "căn hộ", "chung cư"],
    "giao_duc": ["giáo dục", "trung tâm", "học viện", "dạy học", "luyện thi"],
    "y_te": ["phòng khám", "bệnh viện", "clinic", "y tế", "bác sĩ"],
    "thoi_trang": ["thời trang", "fashion", "quần áo", "shop", "boutique"],
}

# Common business problems by industry
BUSINESS_PROBLEMS = {
    "spa": [
        "Khó thu hút khách hàng mới trong mùa thấp điểm",
        "Tỷ lệ khách quay lại thấp",
        "Cạnh tranh gay gắt với các spa khác",
        "Quản lý đặt lịch hẹn thủ công",
        "Khó quảng bá dịch vụ mới"
    ],
    "cafe": [
        "Lượng khách giảm vào ngày thường",
        "Khó xây dựng cộng đồng khách hàng trung thành",
        "Chi phí marketing cao nhưng hiệu quả thấp",
        "Thiếu kênh đặt hàng online",
        "Khó cạnh tranh với các chuỗi lớn"
    ],
    "nha_khoa": [
        "Bệnh nhân lo ngại về chi phí điều trị",
        "Khó xây dựng niềm tin với bệnh nhân mới",
        "Quản lý lịch hẹn phức tạp",
        "Thiếu hiện diện online chuyên nghiệp",
        "Cạnh tranh về giá với các phòng khám khác"
    ],
    "default": [
        "Khó tiếp cận khách hàng tiềm năng",
        "Chi phí marketing cao",
        "Thiếu chiến lược digital marketing",
        "Website chưa tối ưu cho chuyển đổi",
        "Khó đo lường hiệu quả quảng cáo"
    ]
}

# Email templates config
EMAIL_TEMPLATES = {
    "first_contact": "first_contact.txt",
    "follow_up_1": "follow_up_1.txt",
    "follow_up_2": "follow_up_2.txt",
    "final_attempt": "final_attempt.txt"
}
