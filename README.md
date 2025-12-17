# Document Image Search

A comprehensive AI-powered system for extracting, indexing, and querying PDF documents with semantic search and image analysis capabilities.

## Overview

This repository contains two integrated projects that work together to provide intelligent document search and question-answering:

1. **[pdf_import](./pdf_import/)** - PDF extraction and Elasticsearch ingestion pipeline
2. **[knowledge_agent](./knowledge_agent/)** - AI agent for document question answering with image analysis

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Document Image Search                       │
└─────────────────────────────────────────────────────────────────┘

1. PDF Processing (pdf_import)
   ┌──────────┐      ┌─────────────┐      ┌──────────────┐
   │   PDF    │─────>│ Extraction  │─────>│ Elasticsearch│
   │  Files   │      │ + LM Studio │      │   (E5 model) │
   └──────────┘      └─────────────┘      └──────────────┘
                            │
                            v
                     ┌─────────────┐
                     │  Text +     │
                     │  Images +   │
                     │  Captions   │
                     └─────────────┘

2. Question Answering (knowledge_agent)
   ┌──────────┐      ┌─────────────┐      ┌──────────────┐
   │  User    │─────>│   Claude/   │─────>│  Elastic MCP │
   │ Question │      │  GPT Agent  │      │  Server      │
   └──────────┘      └─────────────┘      └──────────────┘
                            │                     │
                            │                     v
                            │              ┌──────────────┐
                            │              │ Search Index │
                            │              └──────────────┘
                            │
                            v
                     ┌─────────────┐
                     │  Image MCP  │
                     │   Server    │
                     └─────────────┘
                            │
                            v
                     ┌─────────────┐
                     │  LM Studio/ │
                     │   OpenAI    │
                     └─────────────┘
```

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd document_image_search

# Install dependencies for both projects
pip install -r pdf_import/requirements.txt
pip install -r knowledge_agent/requirements.txt
```

### 2. Configuration

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your API keys and configuration:

```env
# Required: Choose your AI provider
AI_PROVIDER=anthropic  # or 'openai'
ANTHROPIC_API_KEY=your_key_here

# Required: Elasticsearch configuration
ELASTICSEARCH_HOST=http://localhost:9200
ELASTICSEARCH_API_KEY=your_api_key_here
ELASTICSEARCH_INDEX=pdf_documents
ELASTICSEARCH_INFERENCE_ID=my_e5_model

# Optional: LM Studio for image captioning
LM_STUDIO_URL=http://localhost:1234/v1/chat/completions
LMSTUDIO_MODEL=qwen/qwen3-vl-8b

# MCP Server paths (update to your actual paths)
ELASTIC_SEARCH_MCP_COMMAND=python
ELASTIC_SEARCH_MCP_ARGS=/full/path/to/knowledge_agent/document_search_tool/server.py
IMAGE_ANALYSIS_MCP_COMMAND=python
IMAGE_ANALYSIS_MCP_ARGS=/full/path/to/knowledge_agent/image_mcp_service/server.py
```

### 3. Setup Elasticsearch

Set up your Elasticsearch index with the proper mappings:

```bash
cd pdf_import
python elasticsearch_setup.py
```

### 4. Process PDFs

Extract and index your PDF documents:

```bash
# Single PDF
python elasticsearch_ingest.py /path/to/document.pdf

# Directory of PDFs
python elasticsearch_ingest.py /path/to/pdfs/

# With custom output directory
python elasticsearch_ingest.py document.pdf --output-dir custom_output
```

### 5. Run the Knowledge Agent

Start the web UI for interactive querying:

```bash
cd knowledge_agent
python ui.py
```

Then open your browser to `http://localhost:7860`

Or use the command-line interface:

```bash
python agent.py
```

## Projects

### pdf_import

Extracts text and images from PDFs, generates AI captions for pages, and indexes everything in Elasticsearch with semantic search capabilities.

**Features:**
- Full PDF text extraction
- Page rendering to capture charts and graphs
- AI-powered image captioning using LM Studio
- Semantic search indexing with E5 embeddings
- Batch processing support

**Key Files:**
- `pdf_extractor.py` - Extracts text and images from PDFs
- `elasticsearch_setup.py` - Creates Elasticsearch index with proper mappings
- `elasticsearch_ingest.py` - Ingests extracted data into Elasticsearch

See [pdf_import/README.md](./pdf_import/README.md) for detailed documentation.

### knowledge_agent

AI agent that answers questions about your documents by combining semantic search with image analysis.

**Features:**
- Multi-provider support (Anthropic Claude, OpenAI GPT)
- Web UI for easy testing
- MCP (Model Context Protocol) integration
- Image analysis capabilities
- Real-time tool call tracking

**Key Components:**
- `agent.py` - Main agent implementation
- `ui.py` - Web-based Gradio interface
- `document_search_tool/` - MCP server for Elasticsearch
- `image_mcp_service/` - MCP server for image analysis

See [knowledge_agent/README.md](./knowledge_agent/README.md) for detailed documentation.

## Configuration

This repository uses a centralized configuration system. You can configure settings in three ways (in order of precedence):

1. **Project-specific** `.env` files (e.g., `pdf_import/.env`)
2. **Top-level** `.env` file (shared across all projects)
3. **Environment variables** set in your shell

All projects will automatically search for and use the top-level `.env` file if present, allowing you to configure API keys and common settings in one place.

### Configuration Hierarchy

```
document_image_search/
├── .env                          # Top-level (shared config)
├── .env.example                  # Template with all options
├── config_loader.py              # Centralized config loader
├── pdf_import/
│   ├── .env                      # Project-specific (optional)
│   └── .env.example
└── knowledge_agent/
    ├── .env                      # Project-specific (optional)
    ├── .env.example
    ├── document_search_tool/
    │   ├── .env                  # Tool-specific (optional)
    │   └── .env.example
    └── image_mcp_service/
        ├── .env                  # Tool-specific (optional)
        └── .env.example
```

## Common Workflows

### Complete Document Processing Workflow

```bash
# 1. Setup (one-time)
cp .env.example .env
# Edit .env with your settings
cd pdf_import
python elasticsearch_setup.py

# 2. Process documents
python elasticsearch_ingest.py reports/*.pdf

# 3. Query documents
cd ../knowledge_agent
python ui.py
# Open browser to http://localhost:7860
# Ask: "What are the key findings in the Q4 report?"
```

### Development Workflow

```bash
# Process a test PDF
cd pdf_import
python pdf_extractor.py test_document.pdf test_output

# Review extracted content
ls test_output/
cat test_output/extracted_text.txt
cat test_output/page_captions.json

# Ingest to Elasticsearch
python elasticsearch_ingest.py test_output/

# Test queries
cd ../knowledge_agent
python agent.py
# Ask questions about your test document
```

## Prerequisites

- Python 3.8+
- Elasticsearch 8.x with E5 inference endpoint configured
- API key for Anthropic Claude or OpenAI GPT
- (Optional) LM Studio with a vision-capable model for image captioning

## Documentation

- [pdf_import/README.md](./pdf_import/README.md) - PDF extraction and ingestion guide
- [knowledge_agent/README.md](./knowledge_agent/README.md) - Agent setup and usage
- [knowledge_agent/QUICKSTART.md](./knowledge_agent/QUICKSTART.md) - Quick start guide
- [knowledge_agent/UI_GUIDE.md](./knowledge_agent/UI_GUIDE.md) - Web UI guide
- [knowledge_agent/MCP_SETUP_GUIDE.md](./knowledge_agent/MCP_SETUP_GUIDE.md) - MCP server configuration
- [knowledge_agent/TROUBLESHOOTING.md](./knowledge_agent/TROUBLESHOOTING.md) - Common issues and solutions

## Environment Variables Reference

See [.env.example](./.env.example) for a complete list of configuration options.

### Essential Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AI_PROVIDER` | AI provider: 'anthropic' or 'openai' | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key (if using Claude) | If using Anthropic |
| `OPENAI_API_KEY` | OpenAI API key (if using GPT) | If using OpenAI |
| `ELASTICSEARCH_HOST` | Elasticsearch URL | Yes |
| `ELASTICSEARCH_API_KEY` | Elasticsearch API key | Yes* |
| `ELASTICSEARCH_INDEX` | Index name for documents | Yes |
| `ELASTICSEARCH_INFERENCE_ID` | E5 inference endpoint ID | Yes |

*Or use `ELASTICSEARCH_USERNAME` and `ELASTICSEARCH_PASSWORD`

## Troubleshooting

### Common Issues

**"API_KEY not found" errors**
- Ensure you've created a `.env` file from `.env.example`
- Add the appropriate API key for your chosen provider

**Elasticsearch connection errors**
- Verify Elasticsearch is running: `curl http://localhost:9200`
- Check your `ELASTICSEARCH_HOST` setting
- Verify authentication credentials

**LM Studio not working**
- Ensure LM Studio is running with a vision model loaded
- Check the URL: `curl http://localhost:1234/v1/models`
- Set `LM_STUDIO_ENABLED=false` to disable (will skip captioning)

**MCP server errors**
- Update MCP server paths in `.env` to absolute paths
- Test MCP servers independently before running the agent

See [knowledge_agent/TROUBLESHOOTING.md](./knowledge_agent/TROUBLESHOOTING.md) for more detailed troubleshooting.


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
