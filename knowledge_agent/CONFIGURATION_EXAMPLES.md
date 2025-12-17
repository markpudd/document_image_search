# Configuration Examples

This document provides practical examples for configuring your Document Agent.

## Basic Configuration

### Anthropic with Example MCP Servers

```env
# AI Provider
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# MCP Servers (using examples)
ELASTIC_SEARCH_MCP_COMMAND=python
ELASTIC_SEARCH_MCP_ARGS=/Users/yourname/knowledge_agent/examples/elastic_search_mcp_example.py

IMAGE_ANALYSIS_MCP_COMMAND=python
IMAGE_ANALYSIS_MCP_ARGS=/Users/yourname/knowledge_agent/examples/image_analysis_mcp_example.py

# Agent Settings
MAX_TOKENS=4096
TEMPERATURE=0.7
SYSTEM_PROMPT=You are a helpful AI assistant that answers questions about documents. Use the available tools to search for documents and analyze images.
```

### OpenAI with Custom MCP Servers

```env
# AI Provider
AI_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
OPENAI_MODEL=gpt-4-turbo-preview

# MCP Servers (custom Node.js servers)
ELASTIC_SEARCH_MCP_COMMAND=node
ELASTIC_SEARCH_MCP_ARGS=/path/to/your/elastic-mcp-server/dist/index.js

IMAGE_ANALYSIS_MCP_COMMAND=node
IMAGE_ANALYSIS_MCP_ARGS=/path/to/your/image-mcp-server/dist/index.js

# Agent Settings
MAX_TOKENS=2048
TEMPERATURE=0.5
SYSTEM_PROMPT=You are a document research assistant. Be concise and cite sources.
```

## System Prompt Examples

### Technical Documentation Assistant

```env
SYSTEM_PROMPT=You are a technical documentation expert. When searching for documents, prioritize API documentation, code examples, and technical specifications. For images, focus on extracting information from diagrams, flowcharts, and architecture diagrams. Always provide code snippets when relevant.
```

### Legal Research Assistant

```env
SYSTEM_PROMPT=You are a legal research assistant specialized in document analysis. When searching documents, look for relevant case law, statutes, and legal precedents. When analyzing images, pay attention to signatures, dates, and official seals. Maintain formal language and cite all sources with document IDs.
```

### Medical Research Assistant

```env
SYSTEM_PROMPT=You are a medical research assistant. Prioritize peer-reviewed sources and clinical data. When analyzing images, focus on medical imaging, charts showing clinical trial results, and anatomical diagrams. Always note the source and date of medical information.
```

### Financial Analysis Assistant

```env
SYSTEM_PROMPT=You are a financial analysis assistant. Focus on quarterly reports, financial statements, and market analysis documents. When analyzing images, extract data from charts, graphs, and financial tables. Present numerical data clearly and note any trends.
```

### Customer Support Knowledge Base

```env
SYSTEM_PROMPT=You are a customer support assistant. Search for product documentation, troubleshooting guides, and FAQs. Keep answers clear and actionable. When images contain screenshots or UI elements, describe them in user-friendly terms.
```

## Elasticsearch Document Structure Examples

### Documents with Local Image Paths

```json
{
  "title": "Q4 Financial Report",
  "content": "Revenue increased by 15% in Q4...",
  "image_path": "/data/documents/reports/2024/q4-chart.png",
  "category": "financial",
  "date": "2024-01-15"
}
```

### Documents with Web URLs

```json
{
  "title": "Product Announcement",
  "content": "Introducing our new product line...",
  "image_url": "https://cdn.example.com/products/hero-image.jpg",
  "category": "marketing",
  "date": "2024-02-01"
}
```

### Documents with Both

```json
{
  "title": "Technical Architecture",
  "content": "System architecture overview...",
  "image_path": "/docs/diagrams/architecture.png",
  "thumbnail": "https://example.com/thumbs/arch.jpg",
  "category": "technical",
  "date": "2024-01-20"
}
```

The agent will prioritize `image_path` over `image_url` when both are present.

## Advanced Configurations

### Using Different Models for Different Tasks

Create separate environment files for different use cases:

**research.env:**
```env
AI_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-opus-4-5-20251101  # More capable model for complex research
TEMPERATURE=0.3  # Lower temperature for accuracy
SYSTEM_PROMPT=You are a research assistant focused on accuracy and thoroughness.
```

**quick-lookup.env:**
```env
AI_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929  # Faster model for quick queries
TEMPERATURE=0.7
SYSTEM_PROMPT=You are a quick-lookup assistant. Provide concise answers.
```

Then run with:
```bash
python agent.py --env research.env
# or
python agent.py --env quick-lookup.env
```

### Using MCP Servers with Environment Variables

If your MCP servers need their own configuration, create wrapper scripts:

**run_elastic_mcp.sh:**
```bash
#!/bin/bash
export ELASTICSEARCH_URL=http://localhost:9200
export ELASTICSEARCH_API_KEY=your_elastic_key
export ELASTICSEARCH_INDEX=documents

python /path/to/elastic_search_mcp_example.py
```

**run_image_mcp.sh:**
```bash
#!/bin/bash
export ANTHROPIC_API_KEY=your_anthropic_key
export IMAGE_ANALYSIS_MODEL=claude-3-5-sonnet-20241022

python /path/to/image_analysis_mcp_example.py
```

**Then in .env:**
```env
ELASTIC_SEARCH_MCP_COMMAND=bash
ELASTIC_SEARCH_MCP_ARGS=/path/to/run_elastic_mcp.sh

IMAGE_ANALYSIS_MCP_COMMAND=bash
IMAGE_ANALYSIS_MCP_ARGS=/path/to/run_image_mcp.sh
```

### Docker-based MCP Servers

```env
# Run MCP servers in Docker containers
ELASTIC_SEARCH_MCP_COMMAND=docker
ELASTIC_SEARCH_MCP_ARGS=run --rm -i -e ELASTICSEARCH_URL=http://host.docker.internal:9200 elastic-mcp

IMAGE_ANALYSIS_MCP_COMMAND=docker
IMAGE_ANALYSIS_MCP_ARGS=run --rm -i -e ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} image-mcp
```

## Environment-Specific Configurations

### Development

```env
AI_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
TEMPERATURE=0.7
MAX_TOKENS=4096

ELASTIC_SEARCH_MCP_COMMAND=python
ELASTIC_SEARCH_MCP_ARGS=/Users/dev/knowledge_agent/examples/elastic_search_mcp_example.py

IMAGE_ANALYSIS_MCP_COMMAND=python
IMAGE_ANALYSIS_MCP_ARGS=/Users/dev/knowledge_agent/examples/image_analysis_mcp_example.py

SYSTEM_PROMPT=You are a development assistant. Be verbose and explain your reasoning.
```

### Production

```env
AI_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
TEMPERATURE=0.5  # Lower temperature for consistency
MAX_TOKENS=2048  # Lower token limit for cost control

ELASTIC_SEARCH_MCP_COMMAND=node
ELASTIC_SEARCH_MCP_ARGS=/opt/mcp-servers/elastic/index.js

IMAGE_ANALYSIS_MCP_COMMAND=node
IMAGE_ANALYSIS_MCP_ARGS=/opt/mcp-servers/image/index.js

SYSTEM_PROMPT=You are a professional document assistant. Provide accurate, concise answers.
```

## Testing Configurations

### Test if MCP Servers are Working

```bash
# Test Elastic Search MCP
python examples/elastic_search_mcp_example.py
# Should start without errors and wait for input

# Test Image Analysis MCP
python examples/image_analysis_mcp_example.py
# Should start without errors and wait for input
```

### Test Different System Prompts

Create a test script:

```bash
#!/bin/bash
echo "Testing different prompts..."

# Test 1: Technical prompt
export SYSTEM_PROMPT="You are a technical expert."
python agent.py <<< "What is the architecture?"

# Test 2: Concise prompt
export SYSTEM_PROMPT="Be extremely concise."
python agent.py <<< "What is the architecture?"
```

## Tips for Effective Configuration

1. **Model Selection:**
   - Use Opus for complex reasoning tasks
   - Use Sonnet for balanced performance
   - Use Haiku for quick, simple queries (when available)

2. **Temperature Settings:**
   - 0.0-0.3: Highly deterministic (good for factual queries)
   - 0.4-0.7: Balanced creativity and accuracy
   - 0.8-1.0: More creative (good for brainstorming)

3. **System Prompts:**
   - Keep them focused and specific
   - Mention the tools available
   - Set clear expectations for output format
   - Include domain expertise when needed

4. **Token Limits:**
   - Higher limits for complex documents
   - Lower limits for cost control
   - Adjust based on your use case

5. **Image Handling:**
   - Prefer local file paths for better performance
   - Use URLs only when necessary
   - Ensure file paths are absolute paths
   - Check image file permissions
