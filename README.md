# 🤖 AI Lead Generation Agent

Một AI Agent chuyên nghiệp cho việc tìm kiếm khách hàng tiềm năng và tự động hóa quy trình outreach.

## ✨ Tính năng

- 🔍 **Tìm kiếm doanh nghiệp** từ Google Maps theo ngành nghề và vị trí
- 📊 **Phân tích và chấm điểm** lead (0-100) dựa trên digital maturity
- 📧 **Tạo email cá nhân hóa 100%** bằng AI (OpenAI/Claude)
- 🔔 **Thông báo real-time** qua Telegram/Discord
- 📈 **Web Dashboard** theo dõi trực quan
- ⏰ **Built-in Scheduler** - KHÔNG cần n8n!
- 🐳 **Docker support** cho dễ deploy

---

## 🚀 Quick Start

### Cách 1: Chạy Local (Đơn giản nhất)

```bash
# 1. Clone và cài đặt
git clone <repo-url>
cd n8n-outreach-AI
pip install -r requirements.txt

# 2. Cấu hình
cp .env.example .env
# Sửa .env với API keys của bạn

# 3. Khởi tạo
python main.py init

# 4. Chạy demo
python main.py demo

# 5. Chạy scheduler tự động (thay thế n8n!)
python run_scheduler.py --with-dashboard
```

### Cách 2: Docker (Recommended cho Production)

```bash
cd docker
cp .env.example .env
# Sửa .env với API keys

docker-compose up -d
```

**Truy cập:**
- Dashboard: http://localhost:8080
- API: http://localhost:8000
- n8n (optional): http://localhost:5678

---

## 📋 Các chế độ chạy

### 1️⃣ CLI Mode - Chạy thủ công

```bash
# Tìm kiếm leads
python main.py search --keyword "spa" --location "TP.HCM"

# Tạo email campaign
python main.py generate --keyword "nha khoa" --location "Quận 1"

# Xem thống kê
python main.py stats

# Export leads
python main.py export --format json
```

### 2️⃣ Scheduler Mode - Tự động 24/7 (THAY THẾ n8n!)

```bash
# Chạy scheduler + dashboard
python run_scheduler.py --with-dashboard

# Chỉ scheduler (không dashboard)
python run_scheduler.py

# Chỉ dashboard
python run_scheduler.py --dashboard-only

# Custom keywords và locations
python run_scheduler.py --keywords "spa,gym" --locations "Đà Nẵng,Huế"
```

### 3️⃣ API Mode - Tích hợp với app khác

```bash
uvicorn api_server:app --port 8000
```

---

## 🔔 Cấu hình Notifications

### Telegram (Khuyên dùng!)

1. Tạo bot qua [@BotFather](https://t.me/BotFather) trên Telegram
2. Gửi `/newbot` và làm theo hướng dẫn
3. Lưu lại **bot token**
4. Gửi tin nhắn cho bot của bạn
5. Truy cập URL này để lấy **chat_id**:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
6. Cập nhật `.env`:
   ```env
   TELEGRAM_ENABLED=true
   TELEGRAM_BOT_TOKEN=123456789:ABC-DEF...
   TELEGRAM_CHAT_ID=987654321
   ```

### Discord

1. Vào Server Settings → Integrations → Webhooks
2. Create Webhook → Copy URL
3. Cập nhật `.env`:
   ```env
   DISCORD_ENABLED=true
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/xxx
   ```

### Test Notification

```bash
python run_scheduler.py test-notify
```

---

## 🐳 Self-Host n8n (Miễn phí!)

Nếu vẫn muốn dùng n8n, bạn có thể self-host miễn phí:

### Cách 1: Chỉ n8n
```bash
cd docker
docker-compose -f docker-compose.n8n-only.yml up -d
```

### Cách 2: Full stack (n8n + Agent)
```bash
cd docker
docker-compose up -d
```

**Truy cập n8n:** http://localhost:5678
- Username: admin
- Password: admin123 (đổi trong .env!)

### Import Workflows vào n8n

1. Mở n8n → Workflows → Import from File
2. Import các file trong `n8n_workflows/`:
   - `lead_capture_workflow.json` - Nhận leads mới
   - `email_sequence_workflow.json` - Gửi follow-up tự động

---

## 📁 Cấu trúc Project

```
n8n-outreach-AI/
├── main.py              # CLI interface
├── run_scheduler.py     # ⭐ Standalone scheduler (thay n8n)
├── api_server.py        # REST API server
│
├── src/
│   ├── scraper/         # Google Maps & Web scraping
│   ├── analyzer/        # Lead scoring & analysis
│   ├── email_generator/ # AI email personalization
│   ├── database/        # SQLite CRM
│   ├── scheduler/       # ⭐ Built-in scheduler
│   ├── notifications/   # ⭐ Telegram/Discord alerts
│   ├── dashboard/       # ⭐ Web dashboard
│   └── agent/           # Main orchestrator
│
├── docker/              # Docker configs
│   ├── docker-compose.yml          # Full stack
│   └── docker-compose.n8n-only.yml # n8n only
│
└── n8n_workflows/       # n8n workflow templates
```

---

## 📊 Lead Scoring System

| Score | Quality | Action |
|-------|---------|--------|
| 75-100 | 🔥 Hot | Contact ngay! |
| 50-74 | 🌡️ Warm | Nurture |
| 30-49 | ❄️ Cold | Long-term |
| <30 | ⛔ Unqualified | Skip |

**Tiêu chí chấm điểm:**
- Có email/phone: +20
- Không có website: +15 (cơ hội!)
- Không có social: +10
- Rating cao: +10
- Ít reviews: +10 (cần visibility)

---

## ⚙️ Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_MAPS_API_KEY` | Google Maps API key | ✅ Yes |
| `OPENAI_API_KEY` | OpenAI for AI emails | Optional |
| `SCHEDULE_KEYWORDS` | Ngành nghề (spa,cafe) | Optional |
| `SCHEDULE_LOCATIONS` | Địa điểm | Optional |
| `TELEGRAM_BOT_TOKEN` | Telegram bot | Optional |
| `TELEGRAM_CHAT_ID` | Telegram chat | Optional |

Xem đầy đủ trong `.env.example`

---

## 🔧 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/search` | Tìm kiếm leads |
| POST | `/api/generate` | Full pipeline |
| GET | `/api/leads` | Danh sách leads |
| POST | `/api/generate-email` | Tạo email |
| POST | `/api/analyze` | Phân tích business |
| GET | `/api/stats` | Thống kê |

---

## 📱 Preview

### Telegram Alert
```
🔥 HOT LEAD ALERT!

Spa Hoa Sen
📍 123 Nguyễn Huệ, Q1, TP.HCM
📧 contact@hoasenspa.vn
📊 Lead Score: 85/100

💡 Recommended: Tặng 1 tháng quảng cáo miễn phí

Follow up ngay!
```

### Web Dashboard
```
┌─────────────────────────────────────────┐
│  🤖 AI Lead Agent Dashboard             │
├─────────────────────────────────────────┤
│  Total: 156    Sent: 89    Reply: 12%   │
├─────────────────────────────────────────┤
│  🔥 Hot Leads                           │
│  ├─ Spa Hoa Sen - 85/100                │
│  ├─ Nha Khoa ABC - 78/100               │
│  └─ Café XYZ - 72/100                   │
└─────────────────────────────────────────┘
```

---

## ❓ FAQ

**Q: Cần những API key nào?**
- Bắt buộc: Google Maps API key
- Optional: OpenAI (cho AI email) - có thể dùng templates sẵn

**Q: Có mất phí không?**
- Google Maps: Free tier $200/tháng (~28,500 requests)
- OpenAI: ~$0.01/email (optional)
- Self-host: Miễn phí 100%

**Q: Scheduler vs n8n?**
- **Scheduler**: Đơn giản, không cần setup thêm, nhẹ
- **n8n**: UI kéo thả, flexible hơn, nhiều integrations

**Q: Làm sao lấy Google Maps API key?**
1. Vào [Google Cloud Console](https://console.cloud.google.com/)
2. Tạo project mới
3. Enable "Places API" và "Maps JavaScript API"
4. Tạo API key trong Credentials

---

## 📄 License

MIT License

---

Made with ❤️ for Vietnamese SMBs
