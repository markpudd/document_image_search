# Image Analysis MCP Server

An MCP (Model Context Protocol) server that enables image analysis using vision-capable LLMs. This tool allows you to ask questions about one or more images using either local vision models via LMStudio or cloud-based models via OpenAI.

## Features

- Analyze single or multiple images with natural language questions
- Support for both local file paths and image URLs
- Configurable response parameters (temperature, max tokens)
- Multiple provider options:
  - **LMStudio**: Use local vision models (LLaVA, BakLLaVA, etc.)
  - **OpenAI**: Use GPT-4o, GPT-4o-mini, or other OpenAI vision models
- Maintains image order for sequential analysis

## Prerequisites

1. **Python 3.10 or higher**

2. **Choose a provider:**
   - **LMStudio** (for local models)
     - Download from [https://lmstudio.ai/](https://lmstudio.ai/)
     - Load a vision model (e.g., LLaVA, BakLLaVA, or similar multimodal models)
     - Start the local server (default: http://localhost:1234)

   - **OpenAI** (for cloud models)
     - Get an API key from [https://platform.openai.com/](https://platform.openai.com/)

## Installation

1. Clone or download this repository:
```bash
cd image_mcp_service
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
```
Then edit `.env` to match your LMStudio setup.

## Configuration

### Using .env File (Recommended)

The easiest way to configure the server is using a `.env` file:

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your settings based on your chosen provider:

   **For LMStudio (local models):**
   ```bash
   PROVIDER=lmstudio
   LMSTUDIO_BASE_URL=http://localhost:1234/v1
   LMSTUDIO_MODEL=llava-v1.6-vicuna-7b

   # Optional defaults
   DEFAULT_MAX_TOKENS=1000
   DEFAULT_TEMPERATURE=0.7
   ```

   **For OpenAI:**
   ```bash
   PROVIDER=openai
   OPENAI_API_KEY=sk-your-api-key-here
   OPENAI_MODEL=gpt-4o

   # Optional: Use custom OpenAI-compatible endpoint
   # OPENAI_BASE_URL=https://api.openai.com/v1

   # Optional defaults
   DEFAULT_MAX_TOKENS=1000
   DEFAULT_TEMPERATURE=0.7
   ```

### Environment Variables

All configuration options:

**General:**
- `PROVIDER`: Choose provider - `lmstudio` or `openai` (default: `lmstudio`)
- `DEFAULT_MAX_TOKENS`: Default max tokens for responses (default: `1000`)
- `DEFAULT_TEMPERATURE`: Default temperature for responses (default: `0.7`)

**LMStudio (when PROVIDER=lmstudio):**
- `LMSTUDIO_BASE_URL`: Base URL for LMStudio API (default: `http://localhost:1234/v1`)
- `LMSTUDIO_MODEL`: Model name to use (default: `local-model`)

**OpenAI (when PROVIDER=openai):**
- `OPENAI_API_KEY`: Your OpenAI API key (required when using OpenAI)
- `OPENAI_MODEL`: Model to use - `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, etc. (default: `gpt-4o`)
- `OPENAI_BASE_URL`: API base URL (default: `https://api.openai.com/v1`)

### Claude Desktop Configuration

To use this MCP server with Claude Desktop, add the following to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

#### Option 1: Using .env file (Recommended)
```json
{
  "mcpServers": {
    "image-analysis": {
      "command": "~/miniconda3/bin/python3",
      "args": ["~/image_mcp_service/server.py"]
    }
  }
}
```

The server will automatically load settings from the `.env` file in the project directory.

#### Option 2: Using environment variables in config

**For LMStudio:**
```json
{
  "mcpServers": {
    "image-analysis": {
      "command": "~/miniconda3/bin/python3",
      "args": ["~/image_mcp_service/server.py"],
      "env": {
        "PROVIDER": "lmstudio",
        "LMSTUDIO_BASE_URL": "http://localhost:1234/v1",
        "LMSTUDIO_MODEL": "llava-v1.6-vicuna-7b"
      }
    }
  }
}
```

**For OpenAI:**
```json
{
  "mcpServers": {
    "image-analysis": {
      "command": "~/miniconda3/bin/python3",
      "args": ["~/image_mcp_service/server.py"],
      "env": {
        "PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-your-api-key-here",
        "OPENAI_MODEL": "gpt-4o"
      }
    }
  }
}
```

**Important Notes:**
1. Use the **absolute path** to your Python executable (find it with `which python3`)
2. Update both the `command` path and `args` path to match your installation
3. When using OpenAI, make sure to set your API key securely
4. The `.env` file approach (Option 1) is recommended for better security and easier configuration management

## Usage

### Provider Setup

#### For LMStudio

1. Open LMStudio
2. Download and load a vision-capable model (e.g., "llava-v1.6-vicuna-7b")
3. Go to the "Local Server" tab
4. Click "Start Server"
5. Note the port number (default is 1234)

#### For OpenAI

1. Get your API key from [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Add it to your `.env` file or Claude Desktop config
3. No local setup required - the service runs in the cloud

### Using the Tool

Once configured with Claude Desktop, you can use the `analyze_images` tool:

```
Can you analyze these images for me?
Images: ["/path/to/image1.jpg", "/path/to/image2.png"]
Question: "What are the main differences between these two images?"
```

Or with URLs:
```
Analyze this image: https://example.com/image.jpg
Question: "What objects are visible in this image?"
```

### Tool Parameters

The `analyze_images` tool accepts:

- **images** (required): Array of image file paths or URLs
  - Example: `["/Users/me/photo.jpg", "https://example.com/image.png"]`
- **question** (required): The question to ask about the image(s)
- **max_tokens** (optional): Maximum tokens in response (default: 1000)
- **temperature** (optional): Creativity of response, 0.0-1.0 (default: 0.7)

## Examples

### Single Image Analysis
```json
{
  "images": ["~/photos/sunset.jpg"],
  "question": "Describe this image in detail"
}
```

### Multiple Image Comparison
```json
{
  "images": [
    "~/before.jpg",
    "~/after.jpg"
  ],
  "question": "What changed between the before and after images?"
}
```

### URL-based Analysis
```json
{
  "images": ["https://example.com/chart.png"],
  "question": "What trends does this chart show?",
  "max_tokens": 500,
  "temperature": 0.5
}
```

## Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- WebP (.webp)

## Troubleshooting

### "spawn python ENOENT" Error

If you get this error when starting Claude Desktop:
```
spawn python ENOENT
```

**Solution:** Use the absolute path to your Python executable in the config file.

1. Find your Python path:
   ```bash
   which python3
   ```

2. Update your Claude Desktop config to use this absolute path:
   ```json
   {
     "mcpServers": {
       "image-analysis": {
         "command": "~/miniconda3/bin/python3",
         "args": ["~/image_mcp_service/server.py"]
       }
     }
   }
   ```

3. Restart Claude Desktop

### Connection Errors

**For LMStudio:**
1. Verify LMStudio server is running
2. Check the port number in LMStudio matches your configuration
3. Ensure `LMSTUDIO_BASE_URL` is set correctly

**For OpenAI:**
1. Verify your API key is correct and active
2. Check if you have sufficient API credits
3. Ensure `OPENAI_BASE_URL` is correct (if using custom endpoint)

### Authentication Errors

If you get "OPENAI_API_KEY must be set" error:
1. Ensure `PROVIDER=openai` is set in your `.env` file
2. Verify `OPENAI_API_KEY` is set with a valid API key
3. Check that the `.env` file is in the same directory as `server.py`

### Model Not Found

**For LMStudio:**
1. Check the model name in LMStudio's local server tab
2. Update `LMSTUDIO_MODEL` environment variable to match exactly

**For OpenAI:**
1. Verify the model name is correct (e.g., `gpt-4o`, `gpt-4o-mini`)
2. Ensure your API key has access to the specified model

### Image Not Found

For local files:
- Use absolute paths
- Verify file exists and is readable
- Check file extension is supported

For URLs:
- Ensure URL is accessible
- Check if the URL requires authentication

## Development

To run the server directly for testing:

```bash
python server.py
```

The server communicates via stdio and expects MCP protocol messages.



## Contributing

Feel free to open issues or submit pull requests for improvements.
