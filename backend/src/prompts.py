#!/usr/bin/env python3
"""
Advanced AI prompts for intelligent documentation discovery
Following Google's prompt design best practices
"""

def create_product_discovery_prompt(framework: str, base_url: str, navigation_data: dict, context_analysis: dict) -> str:
    """Generate prompt for discovering products/projects with few-shot examples"""
    return f"""Task: Discover PRODUCTS/PROJECTS within the {framework} ecosystem.

Framework: {framework}
Base URL: {base_url}
Page Title: {navigation_data['title']}
Site Type: {context_analysis['site_type']}

Navigation Data: {navigation_data['navigation'][:30]}
Sections Data: {navigation_data['sections'][:20]}

Examples:

Framework: Spring
Navigation: ["Spring Boot", "Spring Data", "Spring Cloud", "Spring Security"]
Output:
[
  {{"id": "spring-boot", "name": "Spring Boot", "description": "Create stand-alone, production-grade Spring applications", "url": "https://spring.io/projects/spring-boot", "priority": 1, "subtopics": ["Auto Configuration", "Actuator", "DevTools"]}},
  {{"id": "spring-data", "name": "Spring Data", "description": "Consistent programming model for data access", "url": "https://spring.io/projects/spring-data", "priority": 2, "subtopics": ["JPA", "MongoDB", "Redis"]}}
]

Framework: Docker
Navigation: ["Docker Desktop", "Docker Engine", "Docker Compose", "Docker Hub", "Docker Scout"]
Output:
[
  {{"id": "docker-desktop", "name": "Docker Desktop", "description": "Local development environment for containerized applications", "url": "https://docs.docker.com/desktop/", "priority": 1, "subtopics": ["Installation", "Settings", "Extensions"]}},
  {{"id": "docker-engine", "name": "Docker Engine", "description": "Core containerization technology", "url": "https://docs.docker.com/engine/", "priority": 1, "subtopics": ["Install", "Storage", "Networking"]}}
]

Framework: Kubernetes
Navigation: ["Kubernetes Core", "kubectl", "Helm", "Minikube"]
Output:
[
  {{"id": "kubernetes-core", "name": "Kubernetes Core", "description": "Container orchestration platform", "url": "https://kubernetes.io/docs/concepts/", "priority": 1, "subtopics": ["Cluster Architecture", "Workloads", "Services"]}},
  {{"id": "kubectl", "name": "kubectl", "description": "Command-line tool for Kubernetes", "url": "https://kubernetes.io/docs/reference/kubectl/", "priority": 1, "subtopics": ["Commands", "Configuration", "Plugins"]}}
]

Constraints:
- Focus on installable products/libraries, NOT documentation sections
- Avoid: "Getting Started", "Tutorial", "Examples", "API Reference"
- Each topic must be a distinct product/service
- Priority 1 = most important, 5 = least important
- Maximum 10 items

Output: Return ONLY valid JSON array following the examples above."""


def create_documentation_discovery_prompt(framework: str, base_url: str, navigation_data: dict) -> str:
    """Generate prompt for discovering documentation topics with few-shot examples"""
    return f"""Task: Discover DOCUMENTATION TOPICS within {framework}.

Framework: {framework}
Base URL: {base_url}
Page Title: {navigation_data['title']}

Navigation Data: {navigation_data['navigation'][:50]}
Sections Data: {navigation_data['sections'][:30]}

Examples:

Framework: React
Navigation: ["Learn", "Reference", "Community", "Quick Start", "Tutorial"]
Output:
[
  {{"id": "learn-react", "name": "Learn React", "description": "Interactive tutorial and core concepts", "url": "https://react.dev/learn", "priority": 1, "subtopics": ["Quick Start", "Tutorial", "Thinking in React"]}},
  {{"id": "api-reference", "name": "API Reference", "description": "Complete React API documentation", "url": "https://react.dev/reference", "priority": 2, "subtopics": ["Hooks", "Components", "React DOM"]}}
]

Framework: Vue
Navigation: ["Guide", "API", "Tutorial", "Examples", "Cookbook"]
Output:
[
  {{"id": "guide", "name": "Guide", "description": "Complete Vue.js guide from basics to advanced", "url": "https://vuejs.org/guide/", "priority": 1, "subtopics": ["Essentials", "Components", "Reusability"]}},
  {{"id": "api", "name": "API", "description": "Vue.js API reference", "url": "https://vuejs.org/api/", "priority": 2, "subtopics": ["Global API", "Composition API", "Options API"]}}
]

Constraints:
- Focus on DOCUMENTATION TOPICS, not separate products
- Group related pages under broader topic areas
- Prioritize by importance for developers learning the framework
- Each topic must have clear learning value
- Priority 1 = most important for beginners, 5 = advanced topics
- Maximum 10 topics

Output: Return ONLY valid JSON array following the examples above."""


def create_grounded_prompt(framework: str, base_url: str, navigation_data: dict, context_analysis: dict) -> str:
    """Generate prompt leveraging Google Search grounding with examples"""
    return f"""Task: Discover {framework} documentation using both provided content and current web search.

Framework: {framework}
Base URL: {base_url}
Page Title: {navigation_data['title']}

Available Navigation: {navigation_data['navigation'][:20]}

Instructions:
1. Analyze the provided navigation data
2. Use Google Search to find current {framework} documentation structure
3. Combine both sources to identify key topics
4. Verify information currency and accuracy

Examples:

Framework: Next.js (with search results)
Search Results: ["App Router", "Pages Router", "API Routes", "Deployment"]
Output:
[
  {{"id": "app-router", "name": "App Router", "description": "Next.js 13+ file-based routing system", "url": "https://nextjs.org/docs/app", "priority": 1, "subtopics": ["Layout", "Loading", "Error Handling"]}},
  {{"id": "api-routes", "name": "API Routes", "description": "Build API endpoints with Next.js", "url": "https://nextjs.org/docs/api-routes", "priority": 2, "subtopics": ["Route Handlers", "Middleware", "Authentication"]}}
]

Constraints:
- Prioritize current, official documentation
- Verify URLs are accessible and current
- Focus on primary learning paths
- Use search results to validate navigation data
- Maximum 10 topics

Output: Return ONLY valid JSON array with verified, current information."""


def create_code_execution_prompt(framework: str, base_url: str, navigation_data: dict, context_analysis: dict) -> str:
    """Generate prompt using code execution for complex analysis"""
    return f"""Task: Analyze complex {framework} documentation structure using Python code.

Framework: {framework}
Base URL: {base_url}
Navigation Count: {len(navigation_data['navigation'])}
Sections Count: {len(navigation_data['sections'])}

Navigation Data: {navigation_data['navigation']}
Sections Data: {navigation_data['sections']}

Write Python code to:
1. Parse the navigation hierarchy and identify main categories
2. Validate URLs and check HTTP status codes
3. Score topics by importance (navigation depth, link count, semantic keywords)
4. Remove duplicates and consolidate similar topics
5. Generate final topic list with validation scores

Example Output Format:
[
  {{"id": "getting-started", "name": "Getting Started", "description": "Introduction and setup guide", "url": "https://example.com/start", "priority": 1, "subtopics": ["Installation", "First Steps"], "validation_score": 95}},
  {{"id": "advanced-topics", "name": "Advanced Topics", "description": "In-depth framework concepts", "url": "https://example.com/advanced", "priority": 3, "subtopics": ["Performance", "Security"], "validation_score": 87}}
]

Constraints:
- Use code to ensure accurate parsing
- Validate all URLs programmatically
- Score topics objectively based on metrics
- Maximum 10 topics
- Include validation_score (0-100) for each topic

Code Requirements:
- Handle potential HTTP errors gracefully
- Use semantic analysis for topic importance
- Remove near-duplicate topics programmatically
- Generate clean, structured JSON output"""


def create_chain_discovery_prompt(framework: str, base_url: str, navigation_data: dict, stage: str) -> str:
    """Generate chained prompts for complex discovery workflows"""
    if stage == "discovery":
        return f"""Stage 1: DISCOVERY - Identify all potential {framework} topics.

Framework: {framework}
Base URL: {base_url}
Navigation: {navigation_data['navigation'][:30]}

Task: Extract ALL potential documentation topics without filtering.
Output: Raw list of topics with basic information.
Format: [{{"name": "Topic Name", "url": "URL", "description": "Brief description"}}]

Focus on comprehensive extraction - filtering happens in next stage."""
    
    elif stage == "validation":
        return f"""Stage 2: VALIDATION - Validate and score discovered topics.

Framework: {framework}
Previously Discovered Topics: {{previous_topics}}

Task: Validate each topic and assign quality scores.
Criteria:
- Relevance to {framework} learning
- URL accessibility and validity
- Content depth and usefulness
- Uniqueness (not duplicate)

Output: [{{"name": "Topic", "url": "URL", "description": "Desc", "score": 0-100, "keep": true/false}}]"""
    
    elif stage == "enhancement":
        return f"""Stage 3: ENHANCEMENT - Enhance validated topics with rich metadata.

Framework: {framework}
Validated Topics: {{validated_topics}}

Task: Enhance each topic with:
- Proper ID generation
- Priority assignment (1-5)
- Subtopic identification
- Complete descriptions

Output: Final JSON array with full topic metadata."""
    
    return ""


# Model parameter configurations for different strategies
STRATEGY_CONFIGS = {
    "standard": {
        "temperature": 0.1,
        "top_k": 10,
        "top_p": 0.8,
        "max_output_tokens": 2048
    },
    "grounding": {
        "temperature": 0.2,
        "top_k": 15,
        "top_p": 0.9,
        "max_output_tokens": 2048
    },
    "code_execution": {
        "temperature": 0.0,  # Deterministic for code
        "top_k": 5,
        "top_p": 0.7,
        "max_output_tokens": 4096
    },
    "chain": {
        "temperature": 0.15,
        "top_k": 12,
        "top_p": 0.85,
        "max_output_tokens": 1024
    }
}


def get_strategy_config(strategy: str) -> dict:
    """Get optimized model parameters for each strategy"""
    return STRATEGY_CONFIGS.get(strategy, STRATEGY_CONFIGS["standard"])