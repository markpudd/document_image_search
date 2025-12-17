#!/usr/bin/env python3
"""
AI Agent for answering questions about documents using Elastic search and image analysis.
"""

import os
import asyncio
import json
import sys
from pathlib import Path
from anthropic import Anthropic
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add parent directory to path to import config_loader
sys.path.insert(0, str(Path(__file__).parent.parent))
from config_loader import load_config

# Load environment variables (checks local and parent directories)
load_config()


class DocumentAgent:
    """Agent that answers questions about documents using MCP tools."""

    def __init__(self):
        """Initialize the agent with API keys and configuration."""
        self.provider = os.getenv("AI_PROVIDER", "anthropic").lower()

        if self.provider == "anthropic":
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            self.client = Anthropic(api_key=self.api_key)
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        elif self.provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            self.client = OpenAI(api_key=self.api_key)
            self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}. Choose 'anthropic' or 'openai'")

        self.max_tokens = int(os.getenv("MAX_TOKENS", "4096"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))

        # System prompt configuration
        self.system_prompt = os.getenv(
            "SYSTEM_PROMPT",
            "You are a helpful AI assistant that answers questions about documents. "
            "Follow these steps: 1) Use the search_documents tool to find relevant documents. "
            "2) If search results include an 'Image Path' field, use the analyze_image tool with the image_path parameter to examine the image. "
            "3) If search results include an 'Image URL' field, use the analyze_image_url tool with the image_url parameter. "
            "4) Synthesize information from both document content and image analysis to provide a comprehensive answer."
        )

        # MCP server configurations
        self.elastic_search_config = StdioServerParameters(
            command=os.getenv("ELASTIC_SEARCH_MCP_COMMAND", "node"),
            args=[os.getenv("ELASTIC_SEARCH_MCP_ARGS", "")],
            env=None
        )

        self.image_analysis_config = StdioServerParameters(
            command=os.getenv("IMAGE_ANALYSIS_MCP_COMMAND", "node"),
            args=[os.getenv("IMAGE_ANALYSIS_MCP_ARGS", "")],
            env=None
        )

        self.tools = []
        self.tool_call_callback = None  # Optional callback for UI

    async def connect_mcp_servers(self):
        """Connect to MCP servers and retrieve available tools."""
        print("Connecting to MCP servers...")

        # Connect to Elastic Search MCP server
        async with stdio_client(self.elastic_search_config) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                elastic_tools = await session.list_tools()

                for tool in elastic_tools.tools:
                    self.tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema,
                        "server": "elastic_search"
                    })
                    print(f"  - Loaded tool: {tool.name} (Elastic Search)")

        # Connect to Image Analysis MCP server
        async with stdio_client(self.image_analysis_config) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                image_tools = await session.list_tools()

                for tool in image_tools.tools:
                    self.tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema,
                        "server": "image_analysis"
                    })
                    print(f"  - Loaded tool: {tool.name} (Image Analysis)")

        print(f"Total tools loaded: {len(self.tools)}\n")

    async def call_tool(self, tool_name: str, arguments: dict):
        """Execute a tool call on the appropriate MCP server."""
        # Find which server this tool belongs to
        tool_info = next((t for t in self.tools if t["name"] == tool_name), None)
        if not tool_info:
            raise ValueError(f"Tool {tool_name} not found")

        server = tool_info["server"]

        # Connect to the appropriate server and execute the tool
        if server == "elastic_search":
            async with stdio_client(self.elastic_search_config) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    return result
        elif server == "image_analysis":
            async with stdio_client(self.image_analysis_config) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    return result
        else:
            raise ValueError(f"Unknown server: {server}")

    async def _answer_with_anthropic(self, question: str) -> str:
        """Answer question using Anthropic's Claude."""
        # Prepare tools for Claude
        claude_tools = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            }
            for tool in self.tools
        ]

        # Initialize conversation
        messages = [{"role": "user", "content": question}]

        # Agent loop - continue until Claude provides a final answer
        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system_prompt,
                tools=claude_tools,
                messages=messages
            )

            # Check if we've reached the end
            if response.stop_reason == "end_turn":
                # Extract final text response
                final_response = next(
                    (block.text for block in response.content if hasattr(block, "text")),
                    "I couldn't generate a response."
                )
                return final_response

            # Handle tool use
            if response.stop_reason == "tool_use":
                # Add assistant's response to messages
                messages.append({"role": "assistant", "content": response.content})

                # Process tool calls
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input

                        print(f"Using tool: {tool_name}")
                        print(f"  Input: {tool_input}")

                        # Execute tool
                        result = await self.call_tool(tool_name, tool_input)

                        print(f"  Result: {result.content[:200]}...")
                        print()

                        # Call callback if provided (for UI)
                        if self.tool_call_callback:
                            self.tool_call_callback(tool_name, tool_input, str(result.content))

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result.content)
                        })

                # Add tool results to messages
                messages.append({"role": "user", "content": tool_results})
            else:
                # Unexpected stop reason
                return f"Unexpected stop reason: {response.stop_reason}"

    async def _answer_with_openai(self, question: str) -> str:
        """Answer question using OpenAI's GPT."""
        # Prepare tools for OpenAI
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            }
            for tool in self.tools
        ]

        # Initialize conversation with system prompt
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question}
        ]

        # Agent loop - continue until we get a final answer
        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                tools=openai_tools,
                messages=messages
            )

            message = response.choices[0].message

            # Check if we have tool calls
            if message.tool_calls:
                # Add assistant's response to messages
                messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": message.tool_calls
                })

                # Process tool calls
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_input = json.loads(tool_call.function.arguments)

                    print(f"Using tool: {tool_name}")
                    print(f"  Input: {tool_input}")

                    # Execute tool
                    result = await self.call_tool(tool_name, tool_input)

                    print(f"  Result: {result.content[:200]}...")
                    print()

                    # Call callback if provided (for UI)
                    if self.tool_call_callback:
                        self.tool_call_callback(tool_name, tool_input, str(result.content))

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result.content)
                    })
            else:
                # No tool calls, return the response
                return message.content or "I couldn't generate a response."

    async def answer_question(self, question: str) -> str:
        """
        Answer a question about documents using available tools.

        Args:
            question: The user's question about documents

        Returns:
            The agent's answer
        """
        print(f"Question: {question}\n")

        if self.provider == "anthropic":
            return await self._answer_with_anthropic(question)
        elif self.provider == "openai":
            return await self._answer_with_openai(question)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def run_interactive(self):
        """Run the agent in interactive mode."""
        print("=" * 60)
        print("Document Question Answering Agent")
        print("=" * 60)
        print(f"Provider: {self.provider.upper()}")
        print(f"Model: {self.model}")
        print()

        # Connect to MCP servers
        await self.connect_mcp_servers()

        print("Agent ready! Ask questions about documents (type 'quit' to exit)")
        print("=" * 60)
        print()

        while True:
            try:
                question = input("You: ").strip()

                if question.lower() in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break

                if not question:
                    continue

                answer = await self.answer_question(question)
                print(f"\nAgent: {answer}\n")
                print("-" * 60)
                print()

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}\n")
                print("-" * 60)
                print()


async def main():
    """Main entry point."""
    agent = DocumentAgent()
    await agent.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())
