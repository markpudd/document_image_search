#!/usr/bin/env python3
"""
Elasticsearch Ingestion Script
Ingests extracted PDF data into Elasticsearch with semantic search capabilities.
Can accept either a PDF file (will extract first) or an extracted directory.
"""

import sys
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime
from elasticsearch import Elasticsearch
from PIL import Image
import requests

# Add parent directory to path to import config_loader
sys.path.insert(0, str(Path(__file__).parent.parent))
from config_loader import load_config

# Load environment variables (checks local and parent directories)
load_config()


def extract_pdf(pdf_path, output_dir=None):
    """
    Extract PDF using pdf_extractor.py script.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Optional output directory (auto-generated if not provided)

    Returns:
        Path to extraction directory if successful, None otherwise
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        print(f"Error: PDF file '{pdf_path}' does not exist")
        return None

    if not pdf_path.suffix.lower() == '.pdf':
        print(f"Error: File '{pdf_path}' is not a PDF")
        return None

    # Determine output directory
    if output_dir is None:
        output_dir = pdf_path.stem + "_extracted"

    output_path = Path(output_dir)

    # Check if already extracted
    if output_path.exists():
        print(f"Note: Directory '{output_dir}' already exists")
        response = input("Use existing extraction? (yes/no): ")
        if response.lower() == 'yes':
            return str(output_path)

    print(f"\nExtracting PDF: {pdf_path}")
    print(f"Output directory: {output_dir}")

    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    extractor_script = script_dir / "pdf_extractor.py"

    if not extractor_script.exists():
        print(f"Error: pdf_extractor.py not found at {extractor_script}")
        return None

    # Run pdf_extractor.py
    try:
        cmd = [sys.executable, str(extractor_script), str(pdf_path), str(output_dir)]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Print output from extractor
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        # Verify extraction was successful
        if not output_path.exists():
            print(f"Error: Extraction failed - output directory not created")
            return None

        print(f"✓ PDF extraction complete!")
        return str(output_path)

    except subprocess.CalledProcessError as e:
        print(f"Error running pdf_extractor.py: {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def derive_title_from_text(text, max_words=10):
    """
    Derive a title from the extracted text.
    Takes the first meaningful line or first N words.

    Args:
        text: Extracted text from PDF
        max_words: Maximum words for title

    Returns:
        Derived title string
    """
    if not text:
        return "Untitled Document"

    # Split into lines and find first non-empty line
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        # Skip page markers
        if line and not line.startswith('---'):
            # Take first line or first N words
            words = line.split()[:max_words]
            title = ' '.join(words)
            # Truncate if too long
            if len(title) > 100:
                title = title[:97] + "..."
            return title

    # Fallback: take first N words from entire text
    words = text.strip().split()[:max_words]
    return ' '.join(words) if words else "Untitled Document"


def get_image_dimensions(image_path):
    """
    Get dimensions of an image file.

    Args:
        image_path: Path to image file

    Returns:
        Dictionary with width and height
    """
    try:
        with Image.open(image_path) as img:
            return {"width": img.width, "height": img.height}
    except Exception as e:
        print(f"    Warning: Could not get dimensions for {image_path}: {e}")
        return {"width": 0, "height": 0}


def ingest_pdf_to_elasticsearch(
    output_dir,
    es_host=None,
    index_name=None,
    pdf_filename=None,
    api_key=None,
    username=None,
    password=None,
    timeout=None
):
    """
    Ingest extracted PDF data into Elasticsearch.

    Args:
        output_dir: Directory containing extracted PDF data
        es_host: Elasticsearch host URL (uses env var if not provided)
        index_name: Name of the index to ingest into (uses env var if not provided)
        pdf_filename: Original PDF filename (for metadata)

    Returns:
        Document ID if successful, None otherwise
    """

    # Use environment variables if not provided
    if es_host is None:
        es_host = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
    if index_name is None:
        index_name = os.getenv("ELASTICSEARCH_INDEX", "pdf_documents")
    if api_key is None:
        api_key = os.getenv("ELASTICSEARCH_API_KEY")
    if username is None:
        username = os.getenv("ELASTICSEARCH_USERNAME")
    if password is None:
        password = os.getenv("ELASTICSEARCH_PASSWORD")

    inference_id = os.getenv("ELASTICSEARCH_INFERENCE_ID", "my_e5_model")

    output_path = Path(output_dir)

    if not output_path.exists():
        print(f"Error: Output directory '{output_dir}' does not exist")
        return None

    print(f"Reading extracted data from: {output_dir}")

    # Read extracted text
    text_file = output_path / "extracted_text.txt"
    if not text_file.exists():
        print(f"Error: Text file not found at {text_file}")
        return None

    with open(text_file, 'r', encoding='utf-8') as f:
        main_text = f.read()

    print(f"  ✓ Read text ({len(main_text)} characters)")

    # Derive title from text
    title = derive_title_from_text(main_text)
    print(f"  ✓ Derived title: {title}")

    # Read captions
    captions_file = output_path / "page_captions.json"
    captions = {}
    if captions_file.exists():
        with open(captions_file, 'r', encoding='utf-8') as f:
            captions = json.load(f)
        print(f"  ✓ Read {len(captions)} page captions")
    else:
        print(f"  ! No captions file found (LM Studio may not have been used)")

    # Build Elasticsearch connection parameters first (needed for embeddings)
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

    # Add timeout configuration (default 300 seconds = 5 minutes for embedding generation)
    if timeout is not None:
        request_timeout = timeout
    else:
        request_timeout = int(os.getenv("ELASTICSEARCH_TIMEOUT", "300"))
    es_params["request_timeout"] = request_timeout

    # Connect to Elasticsearch
    print(f"\nConnecting to Elasticsearch at {es_host}...")
    print(f"Request timeout: {request_timeout} seconds")
    es = Elasticsearch(**es_params)

    if not es.ping():
        print("Error: Could not connect to Elasticsearch")
        return None

    print("Connected successfully!")

    # Check if index exists
    if not es.indices.exists(index=index_name):
        print(f"Error: Index '{index_name}' does not exist")
        print("Run elasticsearch_setup.py first to create the index")
        return None

    # Build page_descriptions array (without embeddings - pipeline will generate them)
    print("\nProcessing page descriptions...")
    page_descriptions = []

    # Find all rendered page images
    rendered_images = sorted(output_path.glob("page*_rendered.png"))

    for img_path in rendered_images:
        # Extract page number from filename (e.g., "page1_rendered.png" -> 1)
        page_num_str = img_path.stem.split('_')[0].replace('page', '')
        try:
            page_number = int(page_num_str)
        except ValueError:
            continue

        page_key = f"page{page_number}"
        description_text = captions.get(page_key, "No description available")

        # Get image dimensions
        dimensions = get_image_dimensions(str(img_path))

        page_desc = {
            "page_number": page_number,
            "description_text": description_text,
            "image_path": str(img_path.absolute()),
            "image_dimensions": dimensions
        }
        # Note: description_vector will be generated automatically by the ingest pipeline

        page_descriptions.append(page_desc)

    print(f"  ✓ Prepared {len(page_descriptions)} page descriptions")
    print(f"  Note: Embeddings will be generated automatically by ingest pipeline")

    # Count total pages (from text markers or rendered images)
    total_pages = len(rendered_images)

    # Build document
    document = {
        "title": title,
        "filename": pdf_filename or output_path.stem.replace('_extracted', ''),
        "main_text": main_text,
        "page_descriptions": page_descriptions,
        "extracted_date": datetime.now().isoformat(),
        "total_pages": total_pages,
        "output_directory": str(output_path.absolute())
    }

    print(document)
    # Index the document
    print(f"\nIndexing document to '{index_name}'...")
    print(f"Note: This may take a while as embeddings are being generated...")
    result = es.index(index=index_name, document=document, timeout=f"{request_timeout}s")

    doc_id = result['_id']
    print(f"✓ Document indexed successfully!")
    print(f"  Document ID: {doc_id}")
    print(f"  Index: {index_name}")
    print(f"  Title: {title}")
    print(f"  Pages: {total_pages}")
    print(f"  Descriptions: {len(page_descriptions)}")

    return doc_id


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract and ingest PDF(s) into Elasticsearch. Accepts PDF file, directory of PDFs, or extracted directory."
    )
    parser.add_argument(
        "input_path",
        help="Path to PDF file, directory of PDFs, or directory containing extracted PDF data"
    )
    parser.add_argument(
        "--output-dir",
        default="renders",
        help="Output directory for extraction (default: renders)"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Elasticsearch host (default from .env)"
    )
    parser.add_argument(
        "--index",
        default=None,
        help="Index name (default from .env)"
    )
    parser.add_argument(
        "--pdf-filename",
        help="Original PDF filename (optional, for metadata)"
    )
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Skip extraction step (assumes PDFs are already extracted in renders/)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Elasticsearch request timeout in seconds (default: 300)"
    )

    args = parser.parse_args()

    try:
        input_path = Path(args.input_path)

        # Determine if input is a PDF file, directory of PDFs, or extracted directory
        if input_path.is_file() and input_path.suffix.lower() == '.pdf':
            # Single PDF file
            print("=" * 60)
            print("STEP 1: EXTRACTING PDF")
            print("=" * 60)

            # Determine output directory for this specific PDF
            pdf_output_dir = Path(args.output_dir) / input_path.stem
            extraction_dir = extract_pdf(str(input_path), str(pdf_output_dir))
            if not extraction_dir:
                print("\n✗ Extraction failed")
                sys.exit(1)

            # Use PDF filename for metadata
            if not args.pdf_filename:
                args.pdf_filename = input_path.name

            # Ingest to Elasticsearch
            print("\n" + "=" * 60)
            print("STEP 2: INGESTING TO ELASTICSEARCH")
            print("=" * 60)

            doc_id = ingest_pdf_to_elasticsearch(
                output_dir=extraction_dir,
                es_host=args.host,
                index_name=args.index,
                pdf_filename=args.pdf_filename,
                timeout=args.timeout
            )

            if doc_id:
                print("\n" + "=" * 60)
                print("✓ COMPLETE!")
                print("=" * 60)
                print(f"PDF extracted and indexed successfully")
                print(f"Document ID: {doc_id}")
                sys.exit(0)
            else:
                print("\n✗ Ingestion failed")
                sys.exit(1)

        elif input_path.is_dir():
            # Check if this is a directory of PDFs or an already-extracted directory
            pdf_files = list(input_path.glob("*.pdf")) + list(input_path.glob("*.PDF"))

            # Check for extracted_text.txt to determine if it's an extraction directory
            is_extraction_dir = (input_path / "extracted_text.txt").exists()

            if is_extraction_dir:
                # This is a single extracted directory
                print(f"Using existing extraction directory: {input_path}")

                print("\n" + "=" * 60)
                print("INGESTING TO ELASTICSEARCH")
                print("=" * 60)

                doc_id = ingest_pdf_to_elasticsearch(
                    output_dir=str(input_path),
                    es_host=args.host,
                    index_name=args.index,
                    pdf_filename=args.pdf_filename,
                    timeout=args.timeout
                )

                if doc_id:
                    print("\n" + "=" * 60)
                    print("✓ COMPLETE!")
                    print("=" * 60)
                    print(f"Document indexed successfully")
                    print(f"Document ID: {doc_id}")
                    sys.exit(0)
                else:
                    print("\n✗ Ingestion failed")
                    sys.exit(1)

            elif pdf_files:
                # This is a directory containing PDFs
                print(f"Found {len(pdf_files)} PDF file(s) in {input_path}")
                print("=" * 60)

                successful_ingestions = 0
                failed_ingestions = 0
                doc_ids = []

                for idx, pdf_file in enumerate(pdf_files, 1):
                    print(f"\n[{idx}/{len(pdf_files)}] Processing: {pdf_file.name}")
                    print("=" * 60)

                    # Determine output directory for this PDF
                    pdf_output_dir = Path(args.output_dir) / pdf_file.stem

                    # Extract if not skipping extraction
                    if not args.skip_extraction:
                        print("\nSTEP 1: EXTRACTING PDF")
                        print("-" * 60)

                        extraction_dir = extract_pdf(str(pdf_file), str(pdf_output_dir))
                        if not extraction_dir:
                            print(f"\n✗ Extraction failed for {pdf_file.name}")
                            failed_ingestions += 1
                            continue
                    else:
                        # Check if extraction directory exists
                        if not pdf_output_dir.exists():
                            print(f"✗ Extraction directory not found: {pdf_output_dir}")
                            print(f"  Run without --skip-extraction first")
                            failed_ingestions += 1
                            continue
                        extraction_dir = str(pdf_output_dir)
                        print(f"Using existing extraction: {extraction_dir}")

                    # Ingest to Elasticsearch
                    print("\nSTEP 2: INGESTING TO ELASTICSEARCH")
                    print("-" * 60)

                    doc_id = ingest_pdf_to_elasticsearch(
                        output_dir=extraction_dir,
                        es_host=args.host,
                        index_name=args.index,
                        pdf_filename=pdf_file.name,
                        timeout=args.timeout
                    )

                    if doc_id:
                        print(f"✓ Successfully indexed: {pdf_file.name}")
                        print(f"  Document ID: {doc_id}")
                        successful_ingestions += 1
                        doc_ids.append(doc_id)
                    else:
                        print(f"✗ Ingestion failed for {pdf_file.name}")
                        failed_ingestions += 1

                    print("=" * 60)

                # Print summary
                print("\n" + "=" * 60)
                print("BATCH PROCESSING COMPLETE")
                print("=" * 60)
                print(f"Total PDFs: {len(pdf_files)}")
                print(f"Successful: {successful_ingestions}")
                print(f"Failed: {failed_ingestions}")
                if doc_ids:
                    print(f"\nIndexed document IDs:")
                    for doc_id in doc_ids:
                        print(f"  - {doc_id}")

                sys.exit(0 if failed_ingestions == 0 else 1)

            else:
                print(f"Error: Directory '{input_path}' contains no PDF files")
                sys.exit(1)

        else:
            print(f"Error: '{args.input_path}' is neither a PDF file nor a directory")
            sys.exit(1)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
