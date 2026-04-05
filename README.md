# Umay - Open-source Financial Management System

Umay is a powerful, modern financial management system designed for personal and small business accounting. Built with React, FastAPI, PostgreSQL, and Redis, Umay provides comprehensive financial tools including budgeting, transaction tracking, investments, and detailed reporting.

## Features

- 📊 **Dashboard** - Real-time financial overview
- 💳 **Transaction Management** - Track income and expenses
- 💰 **Account Management** - Multiple accounts support
- 📈 **Investments** - Portfolio tracking and analysis
- 📋 **Budgeting** - Plan and monitor spending
- 📄 **Reports** - Detailed financial reports
- 🔒 **Security** - Ed25519 encrypted license system
- 🌐 **Multi-tenant** - Support for multiple organizations
- ☁️ **Cloud Ready** - Docker and Docker Compose support

## Quick Start

### Option 1: Automated Installation (Linux/QNAP/Docker)

```bash
curl -fsSL https://raw.githubusercontent.com/Signorali/umay/main/install.sh | bash
```

This will:
- Check system requirements (Docker, Docker Compose)
- Prompt for admin email and password
- Generate secure configuration
- Start the system automatically
- Access the application at http://localhost:1880

### Option 2: Manual Docker Compose

```bash
# Clone the repository
git clone https://github.com/Signorali/umay.git
cd umay

# Copy and customize environment
cp .env.example .env
# Edit .env with your configuration

# Start the services
docker-compose up -d

# Access at http://localhost:1880
```

## System Requirements

### Automated Installation
- Docker and Docker Compose
- 2GB RAM minimum
- 1GB disk space minimum
- Linux/QNAP/Docker-capable environment

### Manual Installation
- Python 3.9+
- Node.js 16+
- PostgreSQL 13+
- Redis 6+

## Configuration

### Environment Variables

Key configuration variables (see `.env.example` for full list):
- `APP_SECRET` - Application secret key
- `JWT_SECRET` - JWT signing secret
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `ADMIN_EMAIL` - Initial admin email
- `ADMIN_PASSWORD` - Initial admin password

## Licensing

### Free Version (v1.0.0)
- Unlimited transactions
- 2-user limit (trial)
- 30-day trial period
- Feature degradation after trial expiry

### Paid License
- Unlimited users
- Unlimited features
- Email support
- Regular updates

Get a license key at [umay.io/pricing](https://umay.io/pricing)

## Documentation

- [Installation Guide](./docs/INSTALLATION.md)
- [Configuration Guide](./docs/CONFIGURATION.md)
- [License Tiers](./docs/LICENSE_TIERS.md)
- [Troubleshooting](./docs/TROUBLESHOOTING.md)

## Architecture

- **Frontend**: React 18, TypeScript, TailwindCSS
- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL
- **Cache**: Redis
- **Deployment**: Docker Compose

## Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## License

MIT License - See [LICENSE](./LICENSE) file for details

## Support

- Issues: [GitHub Issues](https://github.com/Signorali/umay/issues)
- Email: support@umay.io
- Documentation: [docs.umay.io](https://docs.umay.io)

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

Built with ❤️ for better financial management
