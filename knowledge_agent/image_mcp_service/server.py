#!/usr/bin/env python3
"""
MCP Server for Image Analysis using LMStudio Vision LLM
"""

import asyncio
import base64
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Add parent directories to path to import config_loader
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config_loader import load_config

# Load environment variables (checks local and parent directories)
load_config()


class ImageAnalysisServer:
    def __init__(self):
        self.server = Server("image-analysis-server")

        # Provider configuration
        self.provider = os.getenv("PROVIDER", "lmstudio").lower()

        # LMStudio configuration
        self.lmstudio_base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
        self.lmstudio_model = os.getenv("LMSTUDIO_MODEL", "local-model")

        # OpenAI configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

        # Common configuration
        self.default_max_tokens = int(os.getenv("DEFAULT_MAX_TOKENS", "1000"))
        self.default_temperature = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))

        # Validate configuration
        if self.provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set when using OpenAI provider")

        if self.provider not in ["lmstudio", "openai"]:
            raise ValueError(f"Invalid provider: {self.provider}. Must be 'lmstudio' or 'openai'")

        self._setup_handlers()

    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="analyze_images",
                    description="Analyze one or more images using a vision LLM. Accepts a list of image file paths or URLs and a question to ask about the images.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "images": {
                                "type": "array",
                                "description": "List of image file paths or URLs (in order)",
                                "items": {
                                    "type": "string"
                                }
                            },
                            "question": {
                                "type": "string",
                                "description": "Question to ask about the image(s)"
                            },
                            "max_tokens": {
                                "type": "integer",
                                "description": "Maximum tokens in the response (default: 1000)",
                                "default": 1000
                            },
                            "temperature": {
                                "type": "number",
                                "description": "Temperature for response generation (default: 0.7)",
                                "default": 0.9
                            }
                        },
                        "required": ["images", "question"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
            if name != "analyze_images":
                raise ValueError(f"Unknown tool: {name}")

            images = arguments.get("images", [])
            question = arguments.get("question", "")
            max_tokens = arguments.get("max_tokens", self.default_max_tokens)
            temperature = arguments.get("temperature", self.default_temperature)

            if not images:
                raise ValueError("At least one image is required")

            if not question:
                raise ValueError("Question is required")

            try:
                result = await self.analyze_images(
                    images=images,
                    question=question,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return [TextContent(type="text", text=result)]
            except Exception as e:
                error_msg = f"Error analyzing images: {str(e)}"
                return [TextContent(type="text", text=error_msg)]

    def _is_url(self, path: str) -> bool:
        """Check if the path is a URL"""
        try:
            result = urlparse(path)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _encode_image(self, image_path: str) -> str:
        """Encode local image file to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _get_image_format(self, path: str) -> str:
        """Determine image format from file extension"""
        ext = Path(path).suffix.lower()
        format_map = {
            ".jpg": "jpeg",
            ".jpeg": "jpeg",
            ".png": "png",
            ".gif": "gif",
            ".webp": "webp"
        }
        return format_map.get(ext, "jpeg")

    async def analyze_images(
        self,
        images: list[str],
        question: str,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """
        Analyze images using configured vision LLM provider

        Args:
            images: List of image file paths or URLs
            question: Question to ask about the images
            max_tokens: Maximum tokens in response
            temperature: Temperature for generation

        Returns:
            The LLM's response as a string
        """
        if self.provider == "openai":
            return await self._analyze_with_openai(images, question, max_tokens, temperature)
        else:
            return await self._analyze_with_lmstudio(images, question, max_tokens, temperature)

    async def _analyze_with_lmstudio(
        self,
        images: list[str],
        question: str,
        max_tokens: int,
        temperature: float
    ) -> str:
        """Analyze images using LMStudio's vision LLM"""
        content = self._build_content(images, question)

        payload = {
            "model": self.lmstudio_model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.lmstudio_base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                raise Exception(
                    f"LMStudio API error (status {response.status_code}): {response.text}"
                )

            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception(f"Unexpected response format from LMStudio: {result}")

    async def _analyze_with_openai(
        self,
        images: list[str],
        question: str,
        max_tokens: int,
        temperature: float
    ) -> str:
        """Analyze images using OpenAI's vision API"""
        content = self._build_content(images, question)

        payload = {
            "model": self.openai_model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}"
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.openai_base_url}/chat/completions",
                json=payload,
                headers=headers
            )

            if response.status_code != 200:
                raise Exception(
                    f"OpenAI API error (status {response.status_code}): {response.text}"
                )

            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception(f"Unexpected response format from OpenAI: {result}")

    def _build_content(self, images: list[str], question: str) -> list[dict]:
        """Build the content array with images and text"""
        content = []

        # Add all images to the content
        for image in images:
            if self._is_url(image):
                # For URLs, use the URL directly
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image}
                })
            else:
                # For local files, encode to base64
                if not os.path.exists(image):
                    raise FileNotFoundError(f"Image file not found: {image}")

                base64_image = self._encode_image(image)
                image_format = self._get_image_format(image)

                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{image_format};base64,{base64_image}"
                    }
                })

        # Add the text question
        content.append({
            "type": "text",
            "text": question
        })

        return content

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    server = ImageAnalysisServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
