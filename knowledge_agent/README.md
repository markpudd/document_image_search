# Document Question Answering Agent

An AI agent that answers questions about documents by searching Elastic and analyzing images using MCP (Model Context Protocol) tools.

**🚀 [Quick Start Guide](QUICKSTART.md)** | **🌐 [Web UI Guide](UI_GUIDE.md)** | **🔧 [Troubleshooting](TROUBLESHOOTING.md)**

## Features

- 🌐 **Optional Web UI** - Easy-to-use browser interface for testing
- 🤖 **Multi-Provider Support** - Use OpenAI (GPT-4) or Anthropic (Claude)
- 🔍 **Document Search** - Searches documents using Elasticsearch via MCP
- 🖼️ **Image Analysis** - Analyzes images from local file paths or URLs
- 💬 **Interactive Interface** - Both web UI and command-line options
- ⚙️ **Fully Configurable** - Customize via environment variables and system prompts
- 🔧 **MCP Integration** - Uses Model Context Protocol for tool access
- 📊 **Tool Visibility** - See which tools are called and their results (in UI)

## Prerequisites

- Python 3.8+
- API key for your chosen provider:
  - Anthropic API key (for Claude), OR
  - OpenAI API key (for GPT-4)
- Running MCP servers:
  - Elastic document search MCP server
  - Image analysis MCP server

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up your MCP servers:

See [MCP_SETUP_GUIDE.md](MCP_SETUP_GUIDE.md) for detailed instructions on configuring MCP servers, or use the [example servers](examples/) provided.

Quick start with examples:
```bash
# Install MCP server dependencies
pip install elasticsearch httpx

# The example servers are in the examples/ directory
```

3. Configure environment variables:

```bash
cp .env.example .env
```

4. Edit `.env` with your configuration:

**Option A: Using the provided example servers**
```env
# Choose your AI provider
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key

# Point to example MCP servers (update paths to match your setup)
ELASTIC_SEARCH_MCP_COMMAND=python
ELASTIC_SEARCH_MCP_ARGS=/Users/yourname/knowledge_agent/examples/elastic_search_mcp_example.py

IMAGE_ANALYSIS_MCP_COMMAND=python
IMAGE_ANALYSIS_MCP_ARGS=/Users/yourname/knowledge_agent/examples/image_analysis_mcp_example.py
```

**Option B: Using your own MCP servers**
```env
# Choose your AI provider: 'anthropic' or 'openai'
AI_PROVIDER=anthropic

# If using Anthropic (Claude)
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# If using OpenAI (GPT-4)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4-turbo-preview

# Configure paths to your MCP servers
ELASTIC_SEARCH_MCP_COMMAND=node
ELASTIC_SEARCH_MCP_ARGS=/path/to/your/elastic-search-server/index.js

IMAGE_ANALYSIS_MCP_COMMAND=node
IMAGE_ANALYSIS_MCP_ARGS=/path/to/your/image-analysis-server/index.js

# Model settings
MAX_TOKENS=4096
TEMPERATURE=0.7
```

See [MCP_SETUP_GUIDE.md](MCP_SETUP_GUIDE.md) for more configuration options.

## Usage

### Option 1: Web UI (Recommended for Testing)

Launch the web interface for an easier testing experience:

```bash
python ui.py
```

Then open your browser to `http://localhost:7860`

**Features:**
- Chat interface with history
- Visual tool call tracking
- Configuration viewer
- Example questions
- Easy testing and debugging

See [UI_GUIDE.md](UI_GUIDE.md) for detailed instructions.

### Option 2: Command Line

Run the agent in interactive mode:

```bash
python agent.py
```

Then ask questions about your documents:

```
You: What information is in the latest quarterly report?
Agent: [Searches documents and provides answer]

You: Can you analyze the chart on page 5?
Agent: [Retrieves image and analyzes it]
```

Type `quit`, `exit`, or `q` to exit.

### Programmatic Usage

You can also use the agent programmatically:

```python
import asyncio
from agent import DocumentAgent

async def ask_question():
    agent = DocumentAgent()
    await agent.connect_mcp_servers()

    answer = await agent.answer_question(
        "What are the key findings in the research document?"
    )
    print(answer)

asyncio.run(ask_question())
```

## How It Works

1. **Initialization**: The agent connects to both MCP servers and retrieves available tools
2. **Question Processing**: When you ask a question, the agent uses your chosen AI provider (Claude or GPT-4) to determine which tools to use
3. **Document Search**: The elastic-document-search tool finds relevant documents
4. **Image Analysis**: If images are found, the image analysis tool examines them
5. **Answer Generation**: The AI synthesizes the information into a comprehensive answer

## Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_PROVIDER` | AI provider to use: `anthropic` or `openai` | `anthropic` |
| `ANTHROPIC_API_KEY` | Your Anthropic API key (if using Claude) | Required for Anthropic |
| `ANTHROPIC_MODEL` | Claude model to use | `claude-sonnet-4-5-20250929` |
| `OPENAI_API_KEY` | Your OpenAI API key (if using GPT) | Required for OpenAI |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4-turbo-preview` |
| `ELASTIC_SEARCH_MCP_COMMAND` | Command to run elastic search MCP server | `node` |
| `ELASTIC_SEARCH_MCP_ARGS` | Arguments for elastic search MCP server | Required |
| `IMAGE_ANALYSIS_MCP_COMMAND` | Command to run image analysis MCP server | `node` |
| `IMAGE_ANALYSIS_MCP_ARGS` | Arguments for image analysis MCP server | Required |
| `MAX_TOKENS` | Maximum tokens for responses | `4096` |
| `TEMPERATURE` | Response creativity (0-1) | `0.7` |
| `SYSTEM_PROMPT` | Custom instructions for the agent's behavior | Default prompt |

## Testing Your Setup

Before running the agent, test that your MCP servers are working:

```bash
python test_mcp_tools.py
```

This will:
- Verify both MCP servers can connect
- List all available tools
- Check tool compatibility
- Identify configuration issues

For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Troubleshooting

### "API_KEY not found" errors
Make sure you've created a `.env` file and added the API key for your chosen provider (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`).

### "Unsupported AI provider" error
Verify that `AI_PROVIDER` is set to either `anthropic` or `openai` in your `.env` file.

### "Tool not found"
Verify that your MCP servers are running and the paths in `.env` are correct.

### Connection errors
Ensure both MCP servers are accessible and running properly. Test them independently first.

### Image tool errors

If images aren't being analyzed:

1. **Run the test script:**
   ```bash
   python test_mcp_tools.py
   ```

2. **Check tool names:** Ensure the image analysis server exposes:
   - `analyze_image` (for file paths)
   - `analyze_image_url` (for URLs)

3. **Verify image paths:** Make sure image paths in Elasticsearch are:
   - Absolute paths (e.g., `/full/path/to/image.png`)
   - Accessible to the MCP server
   - Valid image files (jpg, png, etc.)

4. **Check permissions:** Ensure the MCP server can read image files:
   ```bash
   ls -l /path/to/image.png
   ```

5. **Test image analysis directly:**
   Create a test image and verify the tool works:
   ```python
   # Modify test_mcp_tools.py to test with your image
   result = await session.call_tool('analyze_image', {
       'image_path': '/path/to/test/image.png',
       'question': 'What is in this image?'
   })
   ```

## Customizing the Agent

### Switching Providers

To switch between OpenAI and Anthropic, simply update your `.env` file:

**For OpenAI:**
```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4-turbo-preview
```

**For Anthropic:**
```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
```

### Customizing the System Prompt

You can customize how the agent behaves by setting the `SYSTEM_PROMPT` in your `.env` file:

```env
SYSTEM_PROMPT=You are a specialized research assistant focused on technical documentation. When searching for documents, prioritize technical accuracy and cite your sources. Always analyze any images found in documents to extract charts, diagrams, and visual data.
```

**Example use cases:**
- **Legal document assistant:** "You are a legal document analyst. Focus on finding relevant case law and statutes..."
- **Medical research:** "You are a medical research assistant. Prioritize peer-reviewed sources and clinical data..."
- **Code documentation:** "You are a technical documentation expert. Help developers find API documentation and code examples..."

## Architecture

```
┌─────────────────┐
│   User Question │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Document Agent │
│   (Claude AI)   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────┐
│Elastic │ │  Image   │
│Search  │ │ Analysis │
│  MCP   │ │   MCP    │
└────────┘ └──────────┘
```

