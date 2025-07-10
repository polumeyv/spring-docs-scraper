# Spring Docs Scraper

Modern Spring documentation scraper with Svelte 5 + SvelteKit 2 frontend and Docker-based infrastructure.

## 🚀 Quick Start

```bash
# Clone and start the application
git clone <repository-url>
cd docs-scraper
docker-compose up
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8082

## 📋 Features

- **Modern Frontend**: Built with Svelte 5 and SvelteKit 2
- **Containerized Architecture**: Everything runs in Docker containers
- **Single Command Setup**: No complex environment configuration
- **Hot Reload**: Frontend changes are instantly reflected
- **Unified Configuration**: Single `.env` file for all settings

## 🏗️ Architecture

```
docs-scraper/
├── frontend/               # Svelte 5 + SvelteKit 2 application
│   ├── src/
│   ├── static/
│   └── Dockerfile
├── backend/                # Python scraper and API
│   ├── src/
│   └── Dockerfile
├── spring-docs/            # Scraped documentation (shared volume)
├── docker-compose.yml      # Service orchestration
└── .env                    # Configuration
```

## 🛠️ Development

### Available Commands

```bash
# Start development environment
npm run dev

# Build containers
npm run build

# Run documentation scraper
npm run scrape

# Stop all services
npm run stop

# Clean everything (including scraped docs)
npm run clean
```

### Local Development (without Docker)

```bash
# Frontend development
npm run dev:frontend

# Backend development
npm run dev:backend
```

## 🔧 Configuration

Copy `.env.example` to `.env` and adjust settings as needed:

```bash
cp .env.example .env
```

## 📚 Documentation Structure

The scraper organizes Spring documentation into a clean structure:

```
spring-docs/
├── index.html          # SPA interface
├── static/             # Organized assets
│   ├── css/
│   ├── js/
│   └── img/
├── content/            # JSON content files
├── templates/          # HTML templates
└── metadata.json       # Project metadata
```

## 🐳 Docker Services

1. **frontend**: Svelte/SvelteKit application (port 3000)
2. **backend**: Python API server (port 8082)
3. **scraper**: Documentation scraper (runs on demand)

## 🚀 Deployment

For production deployment, use the production Dockerfile:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run tests
4. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details