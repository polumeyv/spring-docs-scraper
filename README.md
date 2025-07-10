# Spring Documentation Scraper

Scrapes documentation from all Spring projects.

## Setup
```bash
pip install -r requirements.txt
```

## Usage
```bash
python spring_docs_scraper.py
```

## What it does
- Gets all Spring projects from spring.io/projects
- Finds available versions for each project
- Downloads current documentation (reference + API)
- Saves to `spring-docs/` directory

## Output Structure
```
spring-docs/
├── metadata.json
├── summary.txt
└── {project-name}/
    └── {version}/
        ├── reference/
        └── api/
```