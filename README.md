# Developer Documentation Scraper

A modern, general-purpose documentation scraper that can find and download documentation for any framework or tool. Built with Svelte 5, SvelteKit 2, Python, and Docker.

## Features

- 🔍 **Universal Search**: Search for documentation of any framework or tool
- 📁 **Organized Storage**: Create and manage folders to organize downloaded documentation
- 🚀 **Modern UI**: Clean, responsive interface built with Svelte 5
- 🐳 **Docker-based**: Easy setup and deployment with Docker Compose
- 📖 **Multiple Doc Types**: Finds official docs, API references, tutorials, and GitHub repos
- 💾 **Recent Searches**: Keeps track of your search history

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/polumeyv/spring-docs-scraper.git
cd spring-docs-scraper
```

2. Start the application:
```bash
docker compose up -d
```

3. Open your browser and navigate to:
```
http://localhost:3000
```

## How to Use

1. **Search for Documentation**:
   - Enter any framework or tool name (e.g., React, Django, FastAPI, etc.)
   - Click "Search" to find documentation links

2. **Manage Folders**:
   - Select an existing folder from the dropdown
   - Or click "📁 New Folder" to create a new one

3. **Download Documentation**:
   - Click "Download" on any documentation link
   - The documentation will be scraped and saved to your selected folder

## Architecture

### Frontend (Svelte 5 + SvelteKit 2)
- **Port**: 3000
- Modern, reactive UI with Svelte 5
- Real-time search and folder management
- Responsive design with a clean color scheme

### API Server (Flask + Python)
- **Port**: 5000
- RESTful API endpoints for:
  - `/api/search-docs` - Search for documentation links
  - `/api/folders` - List and create folders
  - `/api/scrape` - Initiate documentation scraping

### Documentation Server (Python HTTP Server)
- **Port**: 8082
- Serves scraped documentation
- Static file serving for offline access

### Scraper Service (Python + AsyncIO)
- Async documentation scraper
- Smart content extraction
- Resource downloading (CSS, JS, images)

## API Endpoints

### Search Documentation
```
GET /api/search-docs?q={framework}
```

### List Folders
```
GET /api/folders
```

### Create Folder
```
POST /api/folders
{
  "name": "folder-name"
}
```

### Scrape Documentation
```
POST /api/scrape
{
  "url": "https://docs.example.com",
  "folder": "folder-name",
  "framework": "framework-name"
}
```

## Development

### Project Structure
```
.
├── frontend/          # Svelte frontend application
├── backend/           # Python backend services
│   └── src/
│       ├── api_server.py         # Flask API server
│       ├── doc_search_service.py # Documentation search logic
│       ├── serve_docs.py         # Documentation server
│       └── spring_docs_scraper.py # Scraper implementation
├── compose.yml        # Docker Compose configuration
└── README.md
```

### Running Individual Services

```bash
# Frontend only
docker compose up frontend

# API only
docker compose up api

# All services
docker compose up
```

### Running the Scraper

The scraper runs on-demand:
```bash
docker compose run --rm scraper
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.