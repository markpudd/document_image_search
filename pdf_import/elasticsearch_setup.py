#!/usr/bin/env python3
"""
Elasticsearch Setup Script
Creates the index with proper mappings for PDF document ingestion.
"""

import sys
import os
from pathlib import Path
from elasticsearch import Elasticsearch

# Add parent directory to path to import config_loader
sys.path.insert(0, str(Path(__file__).parent.parent))
from config_loader import load_config

# Load environment variables (checks local and parent directories)
load_config()


def create_elasticsearch_index(
    es_host=None,
    index_name=None,
    inference_id=None,
    api_key=None,
    username=None,
    password=None
):
    """
    Create Elasticsearch index with semantic_text mappings.

    Args:
        es_host: Elasticsearch host URL (uses env var if not provided)
        index_name: Name of the index to create (uses env var if not provided)
        inference_id: Inference endpoint ID for semantic text (uses env var if not provided)
        api_key: API key for authentication (uses env var if not provided)
        username: Username for basic auth (uses env var if not provided)
        password: Password for basic auth (uses env var if not provided)
    """

    # Use environment variables if not provided
    if es_host is None:
        es_host = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
    if index_name is None:
        index_name = os.getenv("ELASTICSEARCH_INDEX", "pdf_documents")
    if inference_id is None:
        inference_id = os.getenv("ELASTICSEARCH_INFERENCE_ID", "my_e5_model")
    if api_key is None:
        api_key = os.getenv("ELASTICSEARCH_API_KEY")
    if username is None:
        username = os.getenv("ELASTICSEARCH_USERNAME")
    if password is None:
        password = os.getenv("ELASTICSEARCH_PASSWORD")

    # Build Elasticsearch connection parameters
    es_params = {"hosts": [es_host]}

    # Add authentication if provided
    if api_key:
        es_params["api_key"] = api_key
    elif username and password:
        es_params["basic_auth"] = (username, password)

    # Add SSL/TLS configuration
    verify_certs = os.getenv("ELASTICSEARCH_VERIFY_CERTS", "true").lower() == "true"
    ca_certs = os.getenv("ELASTICSEARCH_CA_CERTS")

    es_params["verify_certs"] = verify_certs
    if ca_certs:
        es_params["ca_certs"] = ca_certs

    # Connect to Elasticsearch
    print(f"Connecting to Elasticsearch at {es_host}...")
    es = Elasticsearch(**es_params)

    # Check connection
    if not es.ping():
        print("Error: Could not connect to Elasticsearch")
        print("Make sure Elasticsearch is running and accessible")
        sys.exit(1)

    print("Connected successfully!")

    # Check if index already exists
    if es.indices.exists(index=index_name):
        print(f"\nIndex '{index_name}' already exists.")
        response = input("Do you want to delete and recreate it? (yes/no): ")
        if response.lower() == 'yes':
            es.indices.delete(index=index_name)
            print(f"Deleted existing index '{index_name}'")
        else:
            print("Keeping existing index. Exiting...")
            return

    # Define the mapping
    mapping = {
        "mappings": {
            "properties": {
                "title": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                "filename": {
                    "type": "keyword"
                },
                "main_text": {
                    "type": "semantic_text",
                    "inference_id": inference_id
                },
                "page_descriptions": {
                    "type": "nested",
                    "properties": {
                        "page_number": {
                            "type": "integer"
                        },
                        "description_text": {
                            "type": "text"
                        },
                        "description_vector": {
                            "type": "dense_vector",
                            "dims": 384,
                            "index": True,
                            "similarity": "cosine"
                        },
                        "image_path": {
                            "type": "keyword"
                        },
                        "image_dimensions": {
                            "type": "object",
                            "properties": {
                                "width": {"type": "integer"},
                                "height": {"type": "integer"}
                            }
                        }
                    }
                },
                "extracted_date": {
                    "type": "date"
                },
                "total_pages": {
                    "type": "integer"
                },
                "output_directory": {
                    "type": "keyword"
                }
            }
        }
    }

    # Create ingest pipeline for automatic embedding generation
    pipeline_name = f"{index_name}_pipeline"
    print(f"\nCreating ingest pipeline '{pipeline_name}'...")

    pipeline_definition = {
        "description": "Generate embeddings for page descriptions using inference processor",
        "processors": [
            {
                "foreach": {
                    "field": "page_descriptions",
                    "processor": {
                        "inference": {
                            "model_id": inference_id,
                            "input_output": [
                                {
                                    "input_field": "_ingest._value.description_text",
                                    "output_field": "_ingest._value.description_vector"
                                }
                            ]
                        }
                    }
                }
            }
        ]
    }

    try:
        es.ingest.put_pipeline(id=pipeline_name, body=pipeline_definition)
        print(f"✓ Ingest pipeline '{pipeline_name}' created successfully!")
    except Exception as e:
        print(f"Warning: Failed to create ingest pipeline: {e}")
        print("You may need to create the pipeline manually or check inference endpoint configuration")

    # Create the index with default pipeline setting
    print(f"\nCreating index '{index_name}' with semantic_text mappings...")

    # Add default pipeline to index settings
    index_settings = {
        "settings": {
            "index": {
                "default_pipeline": pipeline_name
            }
        },
        "mappings": mapping["mappings"]
    }

    es.indices.create(index=index_name, body=index_settings)
    print(f"✓ Index '{index_name}' created successfully!")
    print(f"  Default pipeline: {pipeline_name}")

    # Display the mapping
    print("\nIndex mapping:")
    print(f"  - title: text (with keyword subfield)")
    print(f"  - filename: keyword")
    print(f"  - main_text: semantic_text (using {inference_id})")
    print(f"  - page_descriptions: nested array")
    print(f"    - page_number: integer")
    print(f"    - description_text: text (stores the caption)")
    print(f"    - description_vector: dense_vector (384 dims, cosine similarity)")
    print(f"      → Auto-generated via ingest pipeline from description_text")
    print(f"    - image_path: keyword")
    print(f"    - image_dimensions: object (width, height)")
    print(f"  - extracted_date: date")
    print(f"  - total_pages: integer")
    print(f"  - output_directory: keyword")

    print(f"\n✓ Setup complete! Ready to ingest PDF documents.")
    print(f"  Embeddings will be automatically generated during ingestion.")


def main():
    import argparse

    # Get defaults from environment variables
    default_host = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
    default_index = os.getenv("ELASTICSEARCH_INDEX", "pdf_documents")
    default_inference_id = os.getenv("ELASTICSEARCH_INFERENCE_ID", "my_e5_model")

    parser = argparse.ArgumentParser(
        description="Setup Elasticsearch index for PDF document ingestion"
    )
    parser.add_argument(
        "--host",
        default=None,
        help=f"Elasticsearch host (default from .env: {default_host})"
    )
    parser.add_argument(
        "--index",
        default=None,
        help=f"Index name (default from .env: {default_index})"
    )
    parser.add_argument(
        "--inference-id",
        default=None,
        help=f"Inference endpoint ID for semantic_text (default from .env: {default_inference_id})"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Elasticsearch API key (default from .env)"
    )
    parser.add_argument(
        "--username",
        default=None,
        help="Elasticsearch username for basic auth (default from .env)"
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Elasticsearch password for basic auth (default from .env)"
    )

    args = parser.parse_args()

    try:
        create_elasticsearch_index(
            es_host=args.host,
            index_name=args.index,
            inference_id=args.inference_id,
            api_key=args.api_key,
            username=args.username,
            password=args.password
        )
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
