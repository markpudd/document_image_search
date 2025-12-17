#!/usr/bin/env python3
"""
PDF Text and Image Extractor
Extracts all text and images from a PDF file.
"""

import sys
import io
import base64
import json
import os
import argparse
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF
import requests

# Add parent directory to path to import config_loader
sys.path.insert(0, str(Path(__file__).parent.parent))
from config_loader import load_config

# Load environment variables (checks local and parent directories)
load_config()


def get_image_caption_from_lm_studio(image_path, lm_studio_url=None):
    """
    Get a caption for an image using LM Studio's vision model.

    Args:
        image_path: Path to the image file
        lm_studio_url: URL of LM Studio API endpoint (uses env var if not provided)

    Returns:
        Caption string or None if failed
    """
    # Use environment variable if not provided
    if lm_studio_url is None:
        lm_studio_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1/chat/completions")

    # Check if LM Studio is enabled
    if os.getenv("LM_STUDIO_ENABLED", "true").lower() == "false":
        return None

    try:
        # Read and encode image to base64
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")

        # Prepare the request for LM Studio's OpenAI-compatible API
        payload = {
            "model": "local-model",  # LM Studio uses whatever model is loaded
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this image in detail. If it contains graphs, charts, or data visualizations, describe what they show including any trends, labels, or key insights."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }

        # Make request to LM Studio
        response = requests.post(lm_studio_url, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            caption = result["choices"][0]["message"]["content"]
            return caption.strip()
        else:
            print(f"    Warning: LM Studio API returned status {response.status_code}")
            return None

    except requests.exceptions.ConnectionError:
        print(f"    Warning: Could not connect to LM Studio at {lm_studio_url}")
        print(f"    Make sure LM Studio is running with a vision-capable model loaded")
        return None
    except Exception as e:
        print(f"    Warning: Error getting caption: {e}")
        return None


def render_pages_to_images(pdf_path, output_dir, dpi=None, use_captions=True, mono=False):
    """
    Render each PDF page to an image (captures vector graphics like graphs/charts).

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save rendered page images
        dpi: Resolution for rendering (uses env var if not provided, default 150)
        use_captions: Whether to generate captions using LM Studio (default True)
        mono: Whether to render in monochrome/grayscale (default False)

    Returns:
        Tuple of (number of pages rendered, captions dictionary)
    """
    # Use environment variable if not provided
    if dpi is None:
        dpi = int(os.getenv("PDF_RENDER_DPI", "150"))

    try:
        doc = fitz.open(pdf_path)
        page_count = 0
        captions = {}

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Render page to image at specified DPI
            # Higher DPI = better quality but larger files
            mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72 is default DPI

            # Render with or without color
            if mono:
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
            else:
                pix = page.get_pixmap(matrix=mat)

            # Save as PNG
            image_filename = f"{output_dir}/page{page_num + 1}_rendered.png"
            pix.save(image_filename)

            page_count += 1
            mode_str = "mono" if mono else "color"
            print(f"  Rendered: {image_filename} ({pix.width}x{pix.height}px, {dpi}dpi, {mode_str})")

            # Get caption from LM Studio if enabled
            if use_captions:
                print(f"    Getting caption from LM Studio...")
                caption = get_image_caption_from_lm_studio(image_filename)
                if caption:
                    captions[f"page{page_num + 1}"] = caption
                    print(f"    Caption: {caption[:100]}..." if len(caption) > 100 else f"    Caption: {caption}")

        doc.close()
        return page_count, captions

    except FileNotFoundError:
        print(f"Error: File '{pdf_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error rendering pages: {e}")
        return 0, {}


def extract_images_from_pdf(pdf_path, output_dir):
    """
    Extract embedded images from a PDF file.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted images

    Returns:
        Number of images extracted
    """
    try:
        doc = fitz.open(pdf_path)
        image_count = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()

            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # Get image dimensions
                width = base_image.get("width", 0)
                height = base_image.get("height", 0)

                # Skip images that are 1 pixel wide or tall (likely decorative lines)
                if width <= 1 or height <= 1:
                    print(f"  Skipped: page{page_num + 1}_img{img_index + 1} ({width}x{height}px - too small)")
                    continue

                # Save image
                image_filename = f"{output_dir}/page{page_num + 1}_img{img_index + 1}.{image_ext}"
                with open(image_filename, "wb") as image_file:
                    image_file.write(image_bytes)

                image_count += 1
                print(f"  Extracted: {image_filename} ({width}x{height}px)")

        doc.close()
        return image_count

    except FileNotFoundError:
        print(f"Error: File '{pdf_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error extracting images: {e}")
        return 0


def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Extracted text as a string
    """
    text = ""

    try:
        doc = fitz.open(pdf_path)
        num_pages = len(doc)

        print(f"Processing {num_pages} pages...")

        for page_num in range(num_pages):
            page = doc[page_num]
            text += f"\n--- Page {page_num + 1} ---\n"
            text += page.get_text()

        doc.close()
        return text

    except FileNotFoundError:
        print(f"Error: File '{pdf_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing PDF: {e}")
        sys.exit(1)


def save_text_to_file(text, output_path):
    """
    Save extracted text to a file.

    Args:
        text: Text to save
        output_path: Path to the output file
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(text)
        print(f"Text successfully saved to: {output_path}")
    except Exception as e:
        print(f"Error saving file: {e}")
        sys.exit(1)


def process_single_pdf(pdf_path, output_dir, render_only=False, dpi=None, mono=False, use_captions=True):
    """
    Process a single PDF file: extract text, render pages, and extract images.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save all extracted content
        render_only: If True, only render pages (skip text and image extraction)
        dpi: Resolution for rendering (uses env var if not provided)
        mono: Whether to render in monochrome/grayscale
        use_captions: Whether to generate captions using LM Studio
    """
    print(f"{'Rendering' if render_only else 'Extracting content from'}: {pdf_path}")
    print(f"Output directory: {output_dir}\n")

    if not render_only:
        # Extract text
        print("Extracting text...")
        text = extract_text_from_pdf(pdf_path)
        text_output_path = f"{output_dir}/extracted_text.txt"
        save_text_to_file(text, text_output_path)

    # Render pages to images (captures vector graphics like graphs/charts)
    print("\nRendering pages to images...")
    page_count, captions = render_pages_to_images(pdf_path, output_dir, dpi=dpi, use_captions=use_captions, mono=mono)
    print(f"Rendered {page_count} page(s)")

    # Save captions to a file
    if captions:
        captions_path = f"{output_dir}/page_captions.json"
        try:
            with open(captions_path, 'w', encoding='utf-8') as f:
                json.dump(captions, f, indent=2)
            print(f"\nCaptions saved to: {captions_path}")
        except Exception as e:
            print(f"\nWarning: Could not save captions: {e}")

    if not render_only:
        # Extract embedded images
        print("\nExtracting embedded images...")
        image_count = extract_images_from_pdf(pdf_path, output_dir)

        if image_count > 0:
            print(f"Extracted {image_count} embedded image(s)")
        else:
            print("No embedded images found in PDF")

    print(f"\nDone! All content saved to: {output_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="PDF Text and Image Extractor - Extracts text, renders pages, and extracts images from PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pdf_extractor.py document.pdf
  python pdf_extractor.py ./pdfs/
  python pdf_extractor.py document.pdf --render-only --dpi 300
  python pdf_extractor.py document.pdf --mono --dpi 200
  python pdf_extractor.py document.pdf -o output_folder --render-only --dpi 150 --mono
        """
    )

    parser.add_argument(
        "input",
        help="PDF file or directory containing PDFs to process"
    )
    parser.add_argument(
        "-o", "--output",
        dest="output_dir",
        help="Output directory (default: 'renders')"
    )
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="Only render pages to images (skip text and embedded image extraction)"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        help="DPI for rendering pages (default: from PDF_RENDER_DPI env var or 150)"
    )
    parser.add_argument(
        "--mono",
        action="store_true",
        help="Render pages in monochrome/grayscale instead of color"
    )
    parser.add_argument(
        "--no-captions",
        action="store_true",
        help="Disable LM Studio caption generation for rendered pages"
    )
    parser.add_argument(
        "--with-captions",
        action="store_true",
        help="Enable captions even in --render-only mode (captions are disabled by default in render-only mode)"
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    # Determine base output directory
    base_output_dir = args.output_dir if args.output_dir else "renders"

    # Determine if captions should be generated
    # In render-only mode, captions are OFF by default unless --with-captions is specified
    # In full extraction mode, captions are ON by default unless --no-captions is specified
    if args.render_only:
        use_captions = args.with_captions and not args.no_captions
    else:
        use_captions = not args.no_captions

    # Check if input is a file or directory
    if input_path.is_file():
        # Single PDF file
        if input_path.suffix.lower() != '.pdf':
            print(f"Error: '{input_path}' is not a PDF file.")
            sys.exit(1)

        # If output directory was explicitly provided, use it directly
        # Otherwise, create a subdirectory with the PDF name
        if args.output_dir:
            output_dir = Path(base_output_dir)
        else:
            output_dir = Path(base_output_dir) / input_path.stem

        output_dir.mkdir(parents=True, exist_ok=True)

        process_single_pdf(
            str(input_path),
            str(output_dir),
            render_only=args.render_only,
            dpi=args.dpi,
            mono=args.mono,
            use_captions=use_captions
        )

    elif input_path.is_dir():
        # Directory containing PDFs
        pdf_files = list(input_path.glob("*.pdf")) + list(input_path.glob("*.PDF"))

        if not pdf_files:
            print(f"No PDF files found in directory: {input_path}")
            sys.exit(1)

        print(f"Found {len(pdf_files)} PDF file(s) in {input_path}\n")
        print("="*60)

        # Create base output directory
        Path(base_output_dir).mkdir(parents=True, exist_ok=True)

        # Process each PDF
        for idx, pdf_file in enumerate(pdf_files, 1):
            print(f"\n[{idx}/{len(pdf_files)}] Processing: {pdf_file.name}")
            print("="*60)

            # Create subdirectory for this PDF
            output_dir = Path(base_output_dir) / pdf_file.stem
            output_dir.mkdir(parents=True, exist_ok=True)

            process_single_pdf(
                str(pdf_file),
                str(output_dir),
                render_only=args.render_only,
                dpi=args.dpi,
                mono=args.mono,
                use_captions=use_captions
            )
            print("="*60)

        print(f"\n\nAll PDFs processed! Output saved to: {base_output_dir}/")

    else:
        print(f"Error: '{input_path}' is not a valid file or directory.")
        sys.exit(1)


if __name__ == "__main__":
    main()
