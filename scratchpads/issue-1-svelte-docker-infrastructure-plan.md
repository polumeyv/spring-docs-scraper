# Issue #1: Project Setup with Svelte 5 + SvelteKit 2 + Docker Infrastructure

[Link to Issue](https://github.com/polumeyv/docs-scraper/issues/1)

## Current State Analysis

The docs-scraper project is currently a Python-based application that:
- Scrapes Spring documentation using various libraries (requests, beautifulsoup4, scrapy, selenium, etc.)
- Serves the scraped documentation via a Python server
- Has heavy Python dependencies for web scraping
- Uses a virtual environment approach for dependency management

## Migration Strategy

### Phase 1: Create New Frontend Infrastructure
1. Initialize Svelte 5 + SvelteKit 2 project alongside existing code
2. Create Docker containers for both frontend and backend services
3. Set up development workflow with hot reload

### Phase 2: Integrate Existing Functionality
1. Migrate the documentation viewing functionality to Svelte
2. Keep Python scraper as a backend service in Docker
3. Create API endpoints for frontend-backend communication

### Phase 3: Optimize and Clean Up
1. Remove Python virtual environment setup
2. Consolidate configuration to single .env file
3. Optimize Docker images for production

## Technical Architecture

### Container Structure
```
docs-scraper/
├── docker-compose.yml          # Orchestrates all services
├── .env.example               # Single configuration file
├── frontend/                  # Svelte 5 + SvelteKit 2
│   ├── Dockerfile
│   ├── package.json
│   └── src/
├── backend/                   # Python scraper service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
└── docs/                      # Shared volume for scraped docs
```

### Service Architecture
1. **Frontend Service (Svelte/SvelteKit)**
   - Port: 3000
   - Features: Doc viewer, search, navigation
   - Hot reload enabled

2. **Backend Service (Python Scraper)**
   - Port: 8082 (API)
   - Features: Scraping, content processing
   - REST API for frontend

3. **Shared Volume**
   - Mounted to both containers
   - Stores scraped documentation

## Implementation Steps

### Step 1: Initialize SvelteKit Project
```bash
npm create svelte@latest frontend -- --template skeleton --types typescript
cd frontend
npm install
```

### Step 2: Create Docker Configuration
- Frontend Dockerfile with Node.js 20+
- Backend Dockerfile with Python 3.11+
- docker-compose.yml with both services

### Step 3: Development Workflow
- Single command: `docker-compose up`
- Automatic reload for frontend changes
- Backend API development server

### Step 4: Migrate Viewing Functionality
- Convert index.html SPA to SvelteKit routes
- Implement search and navigation in Svelte
- Create API integration for content

### Step 5: Configuration Management
- Single .env file for all settings
- No environment-specific configs
- Docker environment variables

### Step 6: Documentation
- Update README with new setup
- Create troubleshooting guide
- Document API endpoints

## Key Decisions

1. **Keep Python Scraper**: The existing scraper is complex and works well. We'll containerize it rather than rewrite it.

2. **Svelte 5 Runes**: Use the new reactivity system with $state, $derived, etc.

3. **SvelteKit 2 Features**: Leverage new routing, loading, and error handling features.

4. **Single Configuration**: One .env file to rule them all - no dev/prod split.

5. **Development First**: Optimize for developer experience with hot reload and fast startup.

## Success Metrics

- ✅ Clone to running: < 30 seconds
- ✅ Single command startup
- ✅ Hot reload working
- ✅ No virtual environment
- ✅ Latest Svelte/SvelteKit versions
- ✅ Clean documentation
- ✅ Consistent environment

## Next Actions

1. Create feature branch `feature/issue-1-svelte-docker-setup`
2. Initialize SvelteKit project in `frontend/` directory
3. Create Docker configurations
4. Set up docker-compose.yml
5. Test development workflow
6. Migrate viewing functionality
7. Update documentation
8. Create PR for review