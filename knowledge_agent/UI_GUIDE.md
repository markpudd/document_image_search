# Web UI Guide

The Document Agent includes an optional web-based UI for easier testing and interaction.

## Features

- 💬 **Chat Interface** - Natural conversation with the agent
- 🔧 **Tool Visibility** - See which tools are called and their results
- ⚙️ **Configuration Display** - View current settings
- 📊 **System Status** - Check MCP server connections
- 🎯 **Example Questions** - Quick start with pre-made examples
- 📝 **History Management** - Clear and restart conversations

## Installation

Install the UI dependency:

```bash
pip install gradio>=4.0.0
```

Or install all dependencies:

```bash
pip install -r requirements.txt
```

## Starting the UI

### Basic Usage

```bash
python ui.py
```

The UI will start and automatically open in your browser at `http://localhost:7860`

### Advanced Options

You can modify `ui.py` to customize the launch settings:

```python
demo.launch(
    server_name="0.0.0.0",  # Allow external access
    server_port=7860,        # Port number
    share=True,              # Create public shareable link
    show_error=True,         # Show detailed errors
)
```

## Using the UI

### 1. Initial Setup

When you first open the UI:

1. The agent will automatically initialize
2. Check the **System Status** panel to verify:
   - MCP servers connected
   - Tools loaded
   - Configuration is correct

### 2. Asking Questions

**Method 1: Type your question**
1. Enter your question in the text box
2. Click "Ask" or press Enter
3. Watch the conversation and tool activity panels

**Method 2: Use examples**
1. Click on any example question
2. Modify if needed
3. Submit

### 3. Understanding Tool Calls

The **Tool Activity** panel shows:
- Which tools were called
- What arguments were passed
- What results were returned

Example:
```
### 1. search_documents
Arguments: `{'query': 'Q4 results', 'max_results': 10}`
Result: Found 3 documents: ...

### 2. analyze_image
Arguments: `{'image_path': '/docs/chart.png', 'question': 'What does this show?'}`
Result: This image shows a bar chart ...
```

### 4. Viewing Configuration

Click **Configuration** to see:
- Current AI provider and model
- API key status
- MCP server paths
- System prompt
- Other settings

### 5. Managing Conversation

- **Clear History** - Reset the conversation
- **Reinitialize Agent** - Reconnect to MCP servers

## UI Layout

```
┌─────────────────────────────────────────┬─────────────────────┐
│  Document Q&A Agent                      │                     │
├─────────────────────────────────────────┤  Tool Activity      │
│                                          │                     │
│  Chat Conversation                       │  • Tool calls       │
│                                          │  • Arguments        │
│  User: Question here                     │  • Results          │
│  Agent: Answer here...                   │                     │
│                                          ├─────────────────────┤
│                                          │  Configuration      │
├─────────────────────────────────────────┤  • Provider         │
│  Your Question: [____________] [Ask]     │  • Model            │
├─────────────────────────────────────────┤  • Settings         │
│  [Clear History] [Reinitialize Agent]    │                     │
├─────────────────────────────────────────┤─────────────────────┤
│  Example Questions                       │  System Status      │
│  • What documents...                     │  ✓ Initialized      │
│  • Search for...                         │  ✓ 3 tools loaded   │
└─────────────────────────────────────────┴─────────────────────┘
```

## Testing Workflow

### Recommended Testing Steps

1. **Start the UI**
   ```bash
   python ui.py
   ```

2. **Verify Setup**
   - Check System Status shows "✓ Agent initialized"
   - Verify tools are loaded in Configuration panel

3. **Test Document Search**
   - Ask: "Search for documents about X"
   - Verify search_documents tool is called
   - Check results in Tool Activity

4. **Test Image Analysis**
   - Ensure your Elasticsearch has documents with image_path fields
   - Ask: "What's in the images from document X?"
   - Verify analyze_image tool is called
   - Check Tool Activity for image analysis results

5. **Test Different Queries**
   - Use example questions
   - Try custom queries
   - Observe tool usage patterns

## Troubleshooting

### UI Won't Start

**Error: `ModuleNotFoundError: No module named 'gradio'`**

Solution:
```bash
pip install gradio>=4.0.0
```

**Error: `Address already in use`**

Another process is using port 7860. Either:
1. Stop the other process
2. Change the port in ui.py:
   ```python
   demo.launch(server_port=7861)  # Use different port
   ```

### Agent Not Initializing

**Check System Status panel for errors**

Common issues:
1. MCP servers not configured correctly
2. API keys missing
3. .env file not found

Solution:
```bash
# Run diagnostic
python test_mcp_tools.py

# Check .env file exists
ls -la .env

# Verify configuration
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('ANTHROPIC_API_KEY'))"
```

### Tools Not Being Called

**Symptoms:**
- Agent responds but Tool Activity shows "No tool calls"
- Generic answers without searching

**Solutions:**

1. Check System Prompt:
   - Open Configuration panel
   - Verify prompt mentions using tools
   - Update in .env if needed

2. Lower Temperature:
   ```env
   TEMPERATURE=0.3
   ```

3. Reinitialize Agent:
   - Click "Reinitialize Agent" button

### Images Not Being Analyzed

**Symptoms:**
- Search works but images not analyzed
- No analyze_image in Tool Activity

**Solutions:**

1. Verify image paths in Elasticsearch are absolute:
   ```json
   {"image_path": "/full/path/to/image.png"}
   ```

2. Check Tool Activity to see if search returned image paths

3. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed image troubleshooting

### Slow Responses

**Causes:**
- Large documents in Elasticsearch
- Big images to analyze
- Network latency

**Solutions:**

1. Reduce max_results in search queries
2. Resize large images
3. Use local file paths instead of URLs
4. Check your internet connection

## UI Customization

### Change Theme

Edit `ui.py`:

```python
with gr.Blocks(
    title="Document Q&A Agent",
    theme=gr.themes.Monochrome(),  # or Glass, Soft, Base
) as demo:
```

Available themes: `Soft`, `Monochrome`, `Glass`, `Base`

### Change Port

```python
demo.launch(server_port=8080)  # Your port
```

### Enable Public Sharing

```python
demo.launch(share=True)  # Creates public URL
```

**Warning:** Public URLs expose your agent to the internet. Only use for testing.

### Custom Examples

Edit the examples list in `ui.py`:

```python
gr.Examples(
    examples=[
        "Your custom question 1",
        "Your custom question 2",
        "Your custom question 3",
    ],
    inputs=question_input,
)
```

## Keyboard Shortcuts

- **Enter** - Submit question
- **Ctrl+C** (in terminal) - Stop the UI server

## Production Deployment

For production use:

1. **Use a production WSGI server**
   ```bash
   # Install gunicorn
   pip install gunicorn

   # Run with gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker ui:app
   ```

2. **Add authentication**
   ```python
   demo.launch(
       auth=("username", "password"),
       auth_message="Enter credentials"
   )
   ```

3. **Use environment variables for secrets**
   - Never hardcode API keys
   - Use .env files (never commit them)
   - Set share=False for production

4. **Add rate limiting**
   - Implement request throttling
   - Monitor usage
   - Set timeouts

## Advanced Features

### Accessing UI Programmatically

The UI can be accessed via API:

```python
import requests

response = requests.post(
    "http://localhost:7860/api/predict",
    json={
        "data": ["What documents do you have?", []]
    }
)
print(response.json())
```

### Integration with Other Tools

The UI can be embedded in other applications:

```python
from ui import create_ui

# Create the interface
demo = create_ui()

# Integrate with your app
# ...
```

## Comparison: UI vs CLI

| Feature | Web UI | CLI (agent.py) |
|---------|--------|----------------|
| Ease of use | ✓ Very easy | Moderate |
| Tool visibility | ✓ Visual panel | Text logs only |
| History | ✓ Scrollable | Terminal buffer |
| Configuration view | ✓ Built-in panel | Manual .env check |
| Sharing | ✓ Public URLs | Not available |
| Automation | API available | ✓ Easier |
| Resource usage | Higher | Lower |
| Best for | Testing, demos | Scripts, automation |

## Tips for Best Results

1. **Use Specific Questions**
   - Good: "What does the Q4 revenue chart show?"
   - Bad: "Tell me about charts"

2. **Check Tool Activity**
   - Verify correct tools are called
   - Check if image paths are found
   - Review tool results for errors

3. **Monitor System Status**
   - Ensure MCP servers stay connected
   - Watch for error messages
   - Reinitialize if tools stop working

4. **Clear History Regularly**
   - Prevents context overflow
   - Improves response speed
   - Reduces token usage

5. **Review Configuration**
   - Verify API keys are set
   - Check system prompt is appropriate
   - Adjust temperature for your use case

## Next Steps

- Review [README.md](README.md) for general usage
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for issues
- See [CONFIGURATION_EXAMPLES.md](CONFIGURATION_EXAMPLES.md) for advanced setups
- Explore [MCP_SETUP_GUIDE.md](MCP_SETUP_GUIDE.md) for MCP configuration
