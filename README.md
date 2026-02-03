# 🤖 AI Lead Generation Agent

Một AI Agent chuyên nghiệp cho việc tìm kiếm khách hàng tiềm năng và tự động hóa quy trình outreach. Agent này có khả năng:

- 🔍 **Tìm kiếm doanh nghiệp** từ Google Maps theo ngành nghề và vị trí
- 📊 **Phân tích và chấm điểm** lead dựa trên nhiều tiêu chí
- 📧 **Tạo email cá nhân hóa 100%** bằng AI
- 🔄 **Tích hợp n8n** cho workflow automation
- 📈 **Theo dõi và báo cáo** hiệu quả chiến dịch

## 🚀 Quick Start

### 1. Cài đặt

```bash
# Clone repository
git clone <repo-url>
cd n8n-outreach-AI

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc: venv\Scripts\activate  # Windows

# Cài đặt dependencies
pip install -r requirements.txt
```

### 2. Cấu hình

```bash
# Copy file cấu hình mẫu
cp .env.example .env

# Chỉnh sửa .env với API keys của bạn
nano .env
```

**Cấu hình cần thiết:**
```env
# Google Maps API (bắt buộc cho search)
GOOGLE_MAPS_API_KEY=your-api-key

# OpenAI API (tùy chọn, cho AI email generation)
OPENAI_API_KEY=sk-...

# Thông tin công ty (cho email)
SENDER_NAME=Tên của bạn
COMPANY_NAME=Tên công ty
COMPANY_PHONE=0901234567
```

### 3. Khởi tạo

```bash
python main.py init
```

### 4. Chạy Demo

```bash
python main.py demo
```

## 📋 Hướng dẫn sử dụng

### CLI Commands

#### Tìm kiếm doanh nghiệp
```bash
python main.py search --keyword "spa" --location "TP.HCM" --max 50
```

#### Tạo email campaign (không gửi)
```bash
python main.py generate \
    --keyword "nha khoa" \
    --location "Quận 1" \
    --campaign "Nha Khoa Q1" \
    --max 20
```

#### Chạy outreach (gửi email thật)
```bash
python main.py outreach \
    --keyword "cafe" \
    --location "Đà Nẵng" \
    --campaign "Cafe DN" \
    --limit 10 \
    --send  # Thêm flag này để gửi thật
```

#### Xem thống kê
```bash
python main.py stats
```

#### Export leads
```bash
python main.py export --format json --output my_leads
```

### API Server

Chạy API server để tích hợp với n8n hoặc ứng dụng khác:

```bash
# Development
uvicorn api_server:app --reload --port 8000

# Production
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

**API Endpoints:**

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/stats` | Thống kê tổng quan |
| POST | `/api/search` | Tìm kiếm leads |
| POST | `/api/generate` | Pipeline đầy đủ |
| GET | `/api/leads` | Danh sách leads |
| GET | `/api/leads/{id}` | Chi tiết lead |
| POST | `/api/generate-email` | Tạo email cho lead |
| POST | `/api/analyze` | Phân tích business |
| POST | `/webhook/lead-capture` | Webhook nhận leads |

**Ví dụ:**
```bash
# Tìm kiếm spa ở TP.HCM
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"keyword": "spa", "location": "TP.HCM", "max_results": 20}'

# Phân tích một business
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Spa ABC",
    "address": "123 Nguyễn Huệ, Q1",
    "email": "contact@spa-abc.vn",
    "industry": "spa",
    "rating": 4.5
  }'
```

## 🔧 Tích hợp n8n

### Import Workflows

Trong thư mục `n8n_workflows/` có sẵn các workflow mẫu:

1. **lead_capture_workflow.json** - Nhận và xử lý lead mới
2. **email_sequence_workflow.json** - Tự động gửi email follow-up

**Cách import:**
1. Mở n8n
2. Vào Settings > Import from File
3. Chọn file JSON workflow

### Cấu hình Webhook

Trong n8n, cấu hình webhook URL:
```
http://your-server:8000/webhook/lead-capture
```

## 📁 Cấu trúc Project

```
n8n-outreach-AI/
├── main.py              # CLI entry point
├── api_server.py        # FastAPI server
├── requirements.txt     # Dependencies
├── .env.example         # Environment template
│
├── src/
│   ├── scraper/         # Google Maps & Web scraping
│   │   ├── google_maps_scraper.py
│   │   ├── web_scraper.py
│   │   └── base_scraper.py
│   │
│   ├── analyzer/        # Business analysis & scoring
│   │   └── business_analyzer.py
│   │
│   ├── email_generator/ # AI email generation
│   │   └── email_generator.py
│   │
│   ├── database/        # SQLite + SQLAlchemy
│   │   ├── models.py
│   │   └── database.py
│   │
│   ├── agent/           # Main orchestrator
│   │   └── lead_agent.py
│   │
│   └── utils/           # Utilities
│       ├── n8n_integration.py
│       └── email_sender.py
│
├── config/
│   └── settings.py      # Configuration management
│
├── n8n_workflows/       # n8n workflow templates
├── data/                # Database & exports
└── logs/                # Application logs
```

## 🎯 Các ngành nghề được hỗ trợ

Agent có templates và analysis rules tối ưu cho:

- 💆 **Spa & Beauty** - Đặt lịch online, marketing Instagram
- ☕ **Café & F&B** - Loyalty program, đặt hàng online
- 🦷 **Nha khoa** - Website y tế, patient education
- 🏋️ **Gym & Fitness** - Membership, PT booking
- 🏨 **Khách sạn** - Booking, reputation management
- 🏠 **Bất động sản** - Lead gen, property marketing
- 📚 **Giáo dục** - Enrollment, course marketing

## 📊 Lead Scoring

Hệ thống chấm điểm lead từ 0-100 dựa trên:

| Tiêu chí | Điểm |
|----------|------|
| Có email | +10 |
| Có số điện thoại | +10 |
| Digital maturity thấp | +20 |
| Không có website | +15 |
| Không có social media | +10 |
| Rating cao (4.0+) | +10 |
| Ít reviews (cần visibility) | +10 |

**Phân loại:**
- 🔥 **Hot** (75-100): Liên hệ ngay
- 🌡️ **Warm** (50-74): Tiềm năng cao
- ❄️ **Cold** (30-49): Cần nurture
- ⛔ **Unqualified** (<30): Không phù hợp

## 📧 Email Templates

Agent tự động chọn template phù hợp với:

1. **Ngành nghề** của business
2. **Pain points** được xác định
3. **Loại email** (first contact, follow-up 1, follow-up 2)
4. **Lead quality** (hot lead nhận offer mạnh hơn)

**Personalization hooks:**
- Tên doanh nghiệp
- Rating và reviews
- Vị trí (quận/thành phố)
- Dịch vụ cụ thể
- Pain points riêng

## ⚠️ Lưu ý quan trọng

### Rate Limiting
- Google Maps API: 100 requests/day (free tier)
- Email gửi: Mặc định 100/ngày
- Delay giữa requests: 2 giây

### Best Practices
1. **Không spam** - Tối đa 3 emails/lead
2. **Personalize** - Đảm bảo mỗi email unique
3. **Test trước** - Dùng `--dry-run` trước khi gửi thật
4. **Monitor** - Theo dõi open/reply rate

### Legal
- Tuân thủ PDPA và luật spam email
- Chỉ contact business emails (không personal)
- Cung cấp option unsubscribe

## 🤝 Contributing

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push và tạo Pull Request

## 📄 License

MIT License - Xem file LICENSE

## 🙋 Support

- Issues: GitHub Issues
- Email: support@example.com

---

Made with ❤️ by AI Agent Team
