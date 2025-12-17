# Troubleshooting Guide

This guide helps you diagnose and fix common issues with the Document Agent.

## Quick Diagnostics

Run this command first to check your setup:

```bash
python test_mcp_tools.py
```

This test script will identify most configuration issues automatically.

## Common Issues

### 1. Images Not Being Analyzed

**Symptoms:**
- Agent finds documents but doesn't analyze images
- No image analysis in the response
- Tool errors related to images

**Solutions:**

#### A. Verify Tool Names
The image analysis MCP server must expose these exact tool names:
- `analyze_image` - for file paths
- `analyze_image_url` - for URLs (optional)

Check with:
```bash
python test_mcp_tools.py
```

Look for the tool names in the output.

#### B. Check System Prompt
Make sure the system prompt instructs the agent to use image tools:

```env
SYSTEM_PROMPT=You are a helpful AI assistant that answers questions about documents. Follow these steps: 1) Use the search_documents tool to find relevant documents. 2) If search results include an 'Image Path' field, use the analyze_image tool with the image_path parameter to examine the image. 3) If search results include an 'Image URL' field, use the analyze_image_url tool with the image_url parameter. 4) Synthesize information from both document content and image analysis to provide a comprehensive answer.
```

#### C. Verify Image Path Format
Image paths in Elasticsearch must be:
- **Absolute paths:** `/full/path/to/image.png` ✓
- **Not relative paths:** `../images/pic.png` ✗

Example Elasticsearch document:
```json
{
  "title": "Report",
  "content": "...",
  "image_path": "/data/documents/images/chart.png"
}
```

#### D. Check File Permissions
Ensure the image files are readable:

```bash
# Check if file exists and is readable
ls -l /path/to/image.png

# Should show: -rw-r--r-- or similar
# If you see permission denied, fix with:
chmod 644 /path/to/image.png
```

#### E. Verify Anthropic API Key
The image analysis server needs an Anthropic API key:

```bash
# Check if set
echo $ANTHROPIC_API_KEY

# If not set, add to your shell startup file or .env
export ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

### 2. MCP Server Connection Errors

**Symptoms:**
- "Error connecting to MCP server"
- "Tool not found"
- Server starts but no tools load

**Solutions:**

#### A. Verify Server Paths
Check that the paths in `.env` are correct:

```bash
# For Python servers
ls -l /path/from/ELASTIC_SEARCH_MCP_ARGS
ls -l /path/from/IMAGE_ANALYSIS_MCP_ARGS

# For Node.js servers
ls -l /path/to/server/index.js
```

#### B. Test Servers Independently
Run each server directly to see errors:

```bash
# Test Elastic Search server
python /path/to/elastic_search_mcp_example.py

# Test Image Analysis server
python /path/to/image_analysis_mcp_example.py

# Server should start and wait for input without errors
# Press Ctrl+C to exit
```

#### C. Check Server Dependencies
Make sure required packages are installed:

```bash
# For Python MCP servers
pip install mcp anthropic httpx elasticsearch

# Verify installation
pip list | grep mcp
pip list | grep anthropic
```

#### D. Review Server Logs
If servers start but don't work, check for errors:

```bash
# Run with verbose output
python -v /path/to/elastic_search_mcp_example.py 2>&1 | head -50
```

### 3. Search Results But No Documents Found

**Symptoms:**
- Agent says "Found 0 documents"
- Search completes but returns empty results

**Solutions:**

#### A. Verify Elasticsearch Connection
Test Elasticsearch directly:

```bash
# Check if Elasticsearch is running
curl http://localhost:9200/_cluster/health

# List indices
curl http://localhost:9200/_cat/indices

# Test search
curl "http://localhost:9200/your_index/_search?q=test"
```

#### B. Check Elasticsearch Configuration
Verify environment variables for the elastic search server:

```bash
export ELASTICSEARCH_URL=http://localhost:9200
export ELASTICSEARCH_INDEX=documents
export ELASTICSEARCH_API_KEY=your_key  # if needed
```

#### C. Index Some Test Data
Create a test document:

```bash
curl -X POST "http://localhost:9200/documents/_doc/1" -H 'Content-Type: application/json' -d'
{
  "title": "Test Document",
  "content": "This is test content for searching",
  "image_path": "/path/to/test/image.png"
}
'
```

### 4. Agent Responds But Ignores Tools

**Symptoms:**
- Agent provides generic answers
- Tools are available but not called
- No tool execution logs

**Solutions:**

#### A. Check System Prompt
Ensure system prompt explicitly mentions using tools:

```env
SYSTEM_PROMPT=You are a helpful AI assistant. ALWAYS use the search_documents tool to find information before answering. If results include images, ALWAYS analyze them with the appropriate tool.
```

#### B. Lower Temperature
More deterministic responses may help:

```env
TEMPERATURE=0.3
```

#### C. Try Different Model
Some models are better at tool use:

```env
# For Anthropic
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# For OpenAI
OPENAI_MODEL=gpt-4-turbo-preview
```

### 5. "Image Path Not Found" Errors

**Symptoms:**
- Error: "Error reading image from file path"
- File not found errors

**Solutions:**

#### A. Use Absolute Paths
Always use full paths in your Elasticsearch documents:

```json
{
  "image_path": "/Users/yourname/documents/images/pic.png"
}
```

NOT:
```json
{
  "image_path": "images/pic.png"
}
```

#### B. Check Working Directory
The MCP server's working directory affects relative paths. Use absolute paths to avoid this.

#### C. Verify Path in Search Results
Check what the search tool returns:

```bash
python test_mcp_tools.py
# Look at the search results to see the exact image_path value
```

### 6. Image Analysis Takes Too Long

**Symptoms:**
- Long delays when analyzing images
- Timeout errors

**Solutions:**

#### A. Check Image Size
Large images take longer to process:

```bash
# Check image size
ls -lh /path/to/image.png

# If > 5MB, consider resizing:
# (requires ImageMagick)
convert input.png -resize 1920x1920\> output.png
```

#### B. Increase Timeout
Modify the MCP server if needed (in `image_analysis_mcp_example.py`):

```python
# Increase timeout for image fetching
async with httpx.AsyncClient(timeout=60.0) as client:
    # ...
```

#### C. Use Local Files Instead of URLs
File paths are faster than URLs:
- File path: ~1-2 seconds
- URL: ~3-5 seconds (network delay)

### 7. Environment Variable Not Loading

**Symptoms:**
- "API_KEY not found"
- Default values being used instead of your config

**Solutions:**

#### A. Verify .env File Location
The `.env` file must be in the same directory as `agent.py`:

```bash
ls -la /path/to/knowledge_agent/.env
```

#### B. Check .env Syntax
Ensure proper format (no spaces around =):

```env
# Correct
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Incorrect
ANTHROPIC_API_KEY = sk-ant-api03-xxxxx
```

#### C. Reload Environment
If you just created `.env`, reload it:

```bash
# Either restart your terminal, or:
source .env  # if using bash
```

#### D. Test Loading
Verify variables load:

```python
from dotenv import load_dotenv
import os
load_dotenv()
print(os.getenv("ANTHROPIC_API_KEY"))
```

## Advanced Diagnostics

### Enable Debug Logging

Add debug output to `agent.py`:

```python
# At the top of agent.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Individual Tool Calls

Modify `test_mcp_tools.py` to test specific scenarios:

```python
# Test with actual image
result = await session.call_tool('analyze_image', {
    'image_path': '/full/path/to/your/test/image.png',
    'question': 'Describe this image'
})
print(result.content)
```

### Check MCP Protocol

Verify the MCP servers implement the protocol correctly:

```bash
# Servers should respond to JSON-RPC calls
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python /path/to/server.py
```

## UI-Specific Issues

### UI Won't Start

**Symptoms:**
- Error when running `python ui.py`
- Import errors
- Server won't launch

**Solutions:**

1. **Test UI components:**
   ```bash
   python test_ui.py
   ```

2. **Check Gradio installation:**
   ```bash
   pip install gradio>=4.0.0
   ```

3. **Verify all dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Check port availability:**
   ```bash
   # On Linux/Mac
   lsof -i :7860

   # If port is in use, change it in ui.py:
   # demo.launch(server_port=7861)
   ```

### UI Shows Errors on Load

**Symptoms:**
- UI opens but shows error messages
- "Error initializing agent"
- MCP connection failures

**Solutions:**

1. **Check System Status panel** for specific errors

2. **Verify .env configuration:**
   ```bash
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Provider:', os.getenv('AI_PROVIDER')); print('Key set:', bool(os.getenv('ANTHROPIC_API_KEY')))"
   ```

3. **Test MCP servers separately:**
   ```bash
   python test_mcp_tools.py
   ```

4. **Check browser console** (F12) for JavaScript errors

### Tool Calls Not Showing in UI

**Symptoms:**
- Agent responds but "Tool Activity" panel empty
- No tools listed

**Solutions:**

1. **Reinitialize Agent** - Click the button in UI

2. **Check callback is set** - Should happen automatically

3. **Clear browser cache** and reload

4. **Try CLI mode** to verify tools work:
   ```bash
   python agent.py
   ```

### Slow UI Response

**Symptoms:**
- Long delays between question and answer
- UI becomes unresponsive

**Solutions:**

1. **Check agent is processing** - Look for activity in terminal

2. **Reduce max_tokens:**
   ```env
   MAX_TOKENS=2048
   ```

3. **Use faster model:**
   ```env
   ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
   ```

4. **Check network connection** to API servers

## Getting More Help

If you're still having issues:

1. Run the full diagnostic:
   ```bash
   python test_mcp_tools.py > diagnostic.log 2>&1
   ```

2. Check the diagnostic log for errors

3. Review the MCP Setup Guide: `MCP_SETUP_GUIDE.md`

4. Check the examples: `examples/README.md`

5. Verify your Elasticsearch documents have the correct schema

## Quick Reference: Common Fixes

| Issue | Quick Fix |
|-------|-----------|
| Images not analyzed | Update SYSTEM_PROMPT to explicitly use image tools |
| Server won't start | Check file paths in .env are correct |
| No search results | Verify ELASTICSEARCH_URL and test with curl |
| Permission denied | chmod 644 on image files |
| API key errors | Check .env file exists and has correct syntax |
| Tool not found | Run test_mcp_tools.py to verify tool names |
| Timeout errors | Reduce image sizes or increase timeouts |
