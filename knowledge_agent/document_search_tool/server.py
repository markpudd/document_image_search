#!/usr/bin/env python3
"""
MCP Server for Elasticsearch Document Search with Image Support

This server provides hybrid search capabilities across documents with text and image content.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Optional
from elasticsearch import Elasticsearch
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from pydantic import BaseModel, Field

# Add parent directories to path to import config_loader
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config_loader import load_config

# Load environment variables (checks local and parent directories)
load_config()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elastic-search-mcp")

# Configuration
ELASTIC_URL = os.getenv("ELASTIC_URL")
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")
ELASTIC_INDEX = os.getenv("ELASTIC_INDEX", "documents")
INFERENCE_ID = os.getenv("INFERENCE_ID", "my-embedding-model")

# Initialize Elasticsearch client
es_client: Optional[Elasticsearch] = None


class SearchResult(BaseModel):
    """Structured search result"""
    title: str = Field(description="Document title")
    filename: str = Field(description="Source filename")
    main_text: Optional[str] = Field(default=None, description="Main document text")
    total_pages: Optional[int] = Field(default=None, description="Total pages in document")
    extracted_date: Optional[str] = Field(default=None, description="Document extraction date")
    relevance_score: float = Field(description="Search relevance score")
    images: list[dict[str, Any]] = Field(default_factory=list, description="Relevant images with descriptions")


def initialize_clients():
    """Initialize Elasticsearch client"""
    global es_client

    if not ELASTIC_URL or not ELASTIC_API_KEY:
        raise ValueError("ELASTIC_URL and ELASTIC_API_KEY must be set in .env file")

    # Initialize Elasticsearch client
    es_client = Elasticsearch(
        ELASTIC_URL,
        api_key=ELASTIC_API_KEY,
        verify_certs=True
    )

    # Test connection
    if not es_client.ping():
        raise ConnectionError("Failed to connect to Elasticsearch")

    logger.info(f"Connected to Elasticsearch at {ELASTIC_URL}")
    logger.info(f"Using inference endpoint: {INFERENCE_ID}")


def create_hybrid_search_query(
    question: str,
    top_k: int = 10,
    min_score: float = 0.5
) -> dict[str, Any]:
    """
    Create a hybrid search query combining:
    1. Semantic search on main_text using semantic_text field
    2. Keyword search on title and main_text
    3. Vector search on image descriptions using Elasticsearch inference (nested)

    Args:
        question: The search question
        top_k: Number of results to return
        min_score: Minimum relevance score

    Returns:
        Elasticsearch query dictionary
    """
    query = {
        "size": top_k,
        "min_score": min_score,
        "query": {
            "bool": {
                "should": [
                    # Semantic search on main_text (using semantic_text field)
                    {
                        "semantic": {
                            "field": "main_text",
                            "query": question
                        }
                    },
                    # Keyword search on title (boosted)
                    {
                        "match": {
                            "title": {
                                "query": question,
                                "boost": 2.0
                            }
                        }
                    },
                    # Nested kNN search on image descriptions using Elasticsearch inference
                    {
                        "nested": {
                            "path": "page_descriptions",
                            "query": {
                                "knn": {
                                    "field": "page_descriptions.description_vector",
                                    "query_vector_builder": {
                                        "text_embedding": {
                                            "model_id": INFERENCE_ID,
                                            "model_text": question
                                        }
                                    },
                                    "num_candidates": 50
                                }
                            },
                            "inner_hits": {
                                "size": 3,
                                "_source": ["page_descriptions.page_number", "page_descriptions.description_text",
                                          "page_descriptions.image_path", "page_descriptions.image_dimensions"]
                            },
                            "score_mode": "max"
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        },
        "_source": ["title", "filename", "main_text", "total_pages", "extracted_date", "output_directory"]
    }

    return query


def format_search_results(es_response: dict[str, Any]) -> list[SearchResult]:
    """
    Format Elasticsearch response into structured results

    Args:
        es_response: Raw Elasticsearch response

    Returns:
        List of SearchResult objects
    """
    results = []

    for hit in es_response.get("hits", {}).get("hits", []):
        source = hit["_source"]

        # Extract images from nested inner_hits if available
        images = []
        if "inner_hits" in hit and "page_descriptions" in hit["inner_hits"]:
            for inner_hit in hit["inner_hits"]["page_descriptions"]["hits"]["hits"]:
                img_source = inner_hit["_source"]
                images.append({
                    "page_number": img_source.get("page_number"),
                    "description": img_source.get("description_text"),
                    "image_path": img_source.get("image_path"),
                    "dimensions": img_source.get("image_dimensions"),
                    "score": inner_hit.get("_score", 0)
                })

        result = SearchResult(
            title=source.get("title", ""),
            filename=source.get("filename", ""),
            main_text=source.get("main_text", "")[:1000] if source.get("main_text") else None,  # Truncate for brevity
            total_pages=source.get("total_pages"),
            extracted_date=source.get("extracted_date"),
            relevance_score=hit["_score"],
            images=images
        )

        results.append(result)

    return results


async def search_documents(question: str, top_k: int = 10, min_score: float = 0.5) -> str:
    """
    Search documents using hybrid search with Elasticsearch-native embedding generation

    Args:
        question: The search question
        top_k: Number of results to return
        min_score: Minimum relevance score

    Returns:
        Formatted search results as a string
    """
    if not es_client:
        return "Error: Elasticsearch client not initialized"

    try:
        # Create hybrid search query (embeddings generated by Elasticsearch)
        search_query = create_hybrid_search_query(question, top_k, min_score)

        # Execute search
        response = es_client.search(index=ELASTIC_INDEX, body=search_query)

        # Format results
        results = format_search_results(response)

        if not results:
            return "No results found for your question."

        # Format output
        output = f"Found {len(results)} relevant documents:\n\n"

        for idx, result in enumerate(results, 1):
            output += f"## Result {idx}: {result.title}\n"
            output += f"**Filename:** {result.filename}\n"
            output += f"**Relevance Score:** {result.relevance_score:.2f}\n"

            if result.total_pages:
                output += f"**Total Pages:** {result.total_pages}\n"

            if result.extracted_date:
                output += f"**Date:** {result.extracted_date}\n"

            if result.main_text:
                output += f"\n**Text Excerpt:**\n{result.main_text}...\n"

            # Add image information
            if result.images:
                output += f"\n**Relevant Images ({len(result.images)}):**\n"
                for img_idx, img in enumerate(result.images, 1):
                    output += f"  {img_idx}. Page {img['page_number']}: {img['description']}\n"
                    output += f"     Image: {img['image_path']}\n"
                    if img.get('dimensions'):
                        output += f"     Size: {img['dimensions']['width']}x{img['dimensions']['height']}px\n"
                    output += f"     Relevance: {img['score']:.2f}\n"

            output += "\n" + "-" * 80 + "\n\n"

        return output

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return f"Error performing search: {str(e)}"


# Create MCP server
app = Server("elastic-document-search")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="search_documents",
            description="""Search through documents using hybrid search combining semantic understanding and keyword matching.

This tool searches across document text and image descriptions to find relevant context for answering questions.
It uses:
- Semantic search on document text for understanding context
- Keyword matching on titles for precise matches
- Vector search on image descriptions to find relevant visual content

Returns relevant text excerpts and links to images with their descriptions.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question or search query"
                    },
                    "top_k": {
                        "type": "number",
                        "description": "Number of results to return (default: 10)",
                        "default": 10
                    },
                    "min_score": {
                        "type": "number",
                        "description": "Minimum relevance score threshold (default: 0.5)",
                        "default": 0.5
                    }
                },
                "required": ["question"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[types.TextContent]:
    """Handle tool calls"""
    if name == "search_documents":
        question = arguments.get("question")
        top_k = arguments.get("top_k", 10)
        min_score = arguments.get("min_score", 0.5)

        if not question:
            return [types.TextContent(type="text", text="Error: question parameter is required")]

        result = await search_documents(question, top_k, min_score)
        return [types.TextContent(type="text", text=result)]
    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Main entry point"""
    # Initialize clients
    try:
        initialize_clients()
    except Exception as e:
        logger.error(f"Failed to initialize: {str(e)}")
        raise

    # Run server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
