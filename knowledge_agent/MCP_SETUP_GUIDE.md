# MCP Tools Configuration Guide

This guide explains how to configure and connect your MCP (Model Context Protocol) servers with the Document Agent.

## Overview

The agent requires two MCP servers:
1. **Elastic Document Search** - Searches for documents in Elasticsearch
2. **Image Analysis** - Analyzes images from URLs

## MCP Server Basics

MCP servers are typically Node.js applications that expose tools via the Model Context Protocol. They run as stdio-based servers that communicate with the agent.

## Configuration Methods

### Method 1: Using Existing MCP Servers

If you already have MCP servers running, configure them in `.env`:

```env
# Elastic Search MCP Server
ELASTIC_SEARCH_MCP_COMMAND=node
ELASTIC_SEARCH_MCP_ARGS=/path/to/elastic-search-server/build/index.js

# Image Analysis MCP Server
IMAGE_ANALYSIS_MCP_COMMAND=node
IMAGE_ANALYSIS_MCP_ARGS=/path/to/image-analysis-server/build/index.js
```

### Method 2: Using npx (Recommended for Testing)

If your MCP servers are published as npm packages:

```env
# Using npx to run MCP servers
ELASTIC_SEARCH_MCP_COMMAND=npx
ELASTIC_SEARCH_MCP_ARGS=-y @yourorg/elastic-search-mcp-server

IMAGE_ANALYSIS_MCP_COMMAND=npx
IMAGE_ANALYSIS_MCP_ARGS=-y @yourorg/image-analysis-mcp-server
```

### Method 3: Using Python MCP Servers

If your MCP servers are written in Python:

```env
# Python-based MCP servers
ELASTIC_SEARCH_MCP_COMMAND=python
ELASTIC_SEARCH_MCP_ARGS=/path/to/elastic_search_server.py

IMAGE_ANALYSIS_MCP_COMMAND=python
IMAGE_ANALYSIS_MCP_ARGS=/path/to/image_analysis_server.py
```

## Example MCP Server Structures

### Example 1: Elastic Document Search MCP Server

Here's what a typical elastic search MCP server configuration looks like:

**Directory Structure:**
```
elastic-search-mcp-server/
├── package.json
├── src/
│   └── index.ts
└── build/
    └── index.js
```

**Expected Tool Schema:**
The elastic search server should expose a tool like:

```json
{
  "name": "search_documents",
  "description": "Search for documents in Elasticsearch",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      },
      "index": {
        "type": "string",
        "description": "Elasticsearch index name"
      },
      "max_results": {
        "type": "number",
        "description": "Maximum number of results to return",
        "default": 10
      }
    },
    "required": ["query"]
  }
}
```

**Configuration in .env:**
```env
ELASTIC_SEARCH_MCP_COMMAND=node
ELASTIC_SEARCH_MCP_ARGS=/Users/yourname/mcp-servers/elastic-search-mcp-server/build/index.js
```

### Example 2: Image Analysis MCP Server

**Expected Tool Schema:**
The image analysis server should expose a tool like:

```json
{
  "name": "analyze_image",
  "description": "Analyze an image from a URL and answer questions about it",
  "inputSchema": {
    "type": "object",
    "properties": {
      "image_url": {
        "type": "string",
        "description": "URL of the image to analyze"
      },
      "question": {
        "type": "string",
        "description": "Question to ask about the image"
      }
    },
    "required": ["image_url", "question"]
  }
}
```

**Configuration in .env:**
```env
IMAGE_ANALYSIS_MCP_COMMAND=node
IMAGE_ANALYSIS_MCP_ARGS=/Users/yourname/mcp-servers/image-analysis-mcp-server/build/index.js
```

## Complete .env Example

Here's a complete `.env` file with all configurations:

```env
# AI Provider Selection
AI_PROVIDER=anthropic

# Anthropic Configuration
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# OpenAI Configuration (if using OpenAI)
OPENAI_API_KEY=sk-xxxxx
OPENAI_MODEL=gpt-4-turbo-preview

# Elastic Search MCP Server
ELASTIC_SEARCH_MCP_COMMAND=node
ELASTIC_SEARCH_MCP_ARGS=/Users/yourname/projects/elastic-search-mcp/build/index.js

# Image Analysis MCP Server
IMAGE_ANALYSIS_MCP_COMMAND=node
IMAGE_ANALYSIS_MCP_ARGS=/Users/yourname/projects/image-analysis-mcp/build/index.js

# Agent Settings
MAX_TOKENS=4096
TEMPERATURE=0.7
```

## Testing Your MCP Servers

Before running the agent, test that your MCP servers work independently:

### Test 1: Verify Server Starts
```bash
# Test elastic search server
node /path/to/elastic-search-server/build/index.js

# Should start without errors and wait for stdio input
```

### Test 2: Check Tool Registration
When the agent starts, it will display loaded tools:

```
Connecting to MCP servers...
  - Loaded tool: search_documents (Elastic Search)
  - Loaded tool: analyze_image (Image Analysis)
Total tools loaded: 2
```

## Common MCP Server Patterns

### Pattern 1: MCP Server with Environment Variables

Some MCP servers need their own configuration:

```env
# Main agent config
ELASTIC_SEARCH_MCP_COMMAND=node
ELASTIC_SEARCH_MCP_ARGS=/path/to/server/index.js

# If the MCP server itself needs config, create a wrapper script
```

**Wrapper script** (`run-elastic-mcp.sh`):
```bash
#!/bin/bash
export ELASTICSEARCH_URL=http://localhost:9200
export ELASTICSEARCH_API_KEY=your_api_key
node /path/to/elastic-search-server/index.js
```

**Then in .env:**
```env
ELASTIC_SEARCH_MCP_COMMAND=bash
ELASTIC_SEARCH_MCP_ARGS=/path/to/run-elastic-mcp.sh
```

### Pattern 2: Docker-based MCP Servers

If your MCP servers run in Docker:

```env
ELASTIC_SEARCH_MCP_COMMAND=docker
ELASTIC_SEARCH_MCP_ARGS=run --rm -i elastic-search-mcp-server
```

## Troubleshooting

### Issue: "Tool not found"
- Verify the MCP server path is correct
- Check that the server executable has proper permissions
- Test running the server command manually

### Issue: "Connection timeout"
- Ensure the MCP server starts quickly (< 10 seconds)
- Check for errors in the server's startup logs
- Verify the server implements the MCP stdio protocol correctly

### Issue: Tools not showing up
- Verify the MCP server implements `tools/list` method
- Check that the server is outputting valid JSON-RPC responses
- Review the server's tool registration code

## Finding or Creating MCP Servers

### Option 1: Use Existing Servers
Check the MCP ecosystem:
- [Anthropic MCP Servers](https://github.com/anthropics/anthropic-quickstarts/tree/main/mcp)
- [Community MCP Servers](https://github.com/topics/mcp-server)

### Option 2: Create Your Own
Use the MCP SDK to create custom servers:
- **TypeScript/Node.js**: `@modelcontextprotocol/sdk`
- **Python**: `mcp` package

Example minimal MCP server (TypeScript):
```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server({
  name: "my-mcp-server",
  version: "1.0.0"
}, {
  capabilities: {
    tools: {}
  }
});

// Register your tools
server.setRequestHandler("tools/list", async () => ({
  tools: [{
    name: "my_tool",
    description: "My tool description",
    inputSchema: {
      type: "object",
      properties: {
        param: { type: "string" }
      }
    }
  }]
}));

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
```

## Next Steps

1. Verify your MCP servers are running correctly
2. Configure the paths in your `.env` file
3. Run the agent: `python agent.py`
4. Check that tools load successfully

For more help, see the main README.md or visit the [MCP documentation](https://modelcontextprotocol.io).
