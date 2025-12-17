# PDF Text and Image Extractor with AI Captions & Elasticsearch

A Python application to extract all text and images (including graphs, charts, and figures) from PDF files. Features AI-powered image captioning using LM Studio and semantic search ingestion into Elasticsearch.

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**

Copy the example environment file and customize it:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# LM Studio Configuration
LM_STUDIO_URL=http://localhost:1234/v1/chat/completions
LM_STUDIO_ENABLED=true

# Elasticsearch Configuration
ELASTICSEARCH_HOST=http://localhost:9200
ELASTICSEARCH_API_KEY=your_api_key_here
# OR use username/password instead of API key:
# ELASTICSEARCH_USERNAME=elastic
# ELASTICSEARCH_PASSWORD=your_password

ELASTICSEARCH_INDEX=pdf_documents
ELASTICSEARCH_INFERENCE_ID=my_e5_model

# SSL/TLS Configuration (optional)
ELASTICSEARCH_VERIFY_CERTS=true
# ELASTICSEARCH_CA_CERTS=/path/to/ca.crt

# General Settings
PDF_RENDER_DPI=150
```

3. **Optional: Set up LM Studio for AI captions**
   - Download and install [LM Studio](https://lmstudio.ai/)
   - Load a vision-capable model (e.g., LLaVA, BakLLaVA, or any multimodal model)
   - Start the local server (Server tab in LM Studio, default port: 1234)
   - The app will automatically use LM Studio if it's running, or skip captions if not available

## Usage

### Basic usage (auto-generates output directory):

```bash
python pdf_extractor.py document.pdf
```

This will create a directory named `document_extracted/` containing:
- `extracted_text.txt` - All text from the PDF with page separators
- `page{N}_rendered.png` - Full page renders (captures vector graphs/charts)
- `page_captions.json` - AI-generated descriptions of each page (if LM Studio is running)
- `page{N}_img{M}.{ext}` - Embedded images extracted from the PDF

### Specify custom output directory:

```bash
python pdf_extractor.py document.pdf my_output_folder
```

## Features

- **Text Extraction**: Extracts all text from PDF pages with clear separators
- **Page Rendering**: Renders each page as an image to capture vector graphics (graphs, charts, diagrams)
- **AI Captions**: Uses LM Studio's vision models to describe page content, especially useful for graphs and charts
- **Embedded Image Extraction**: Extracts embedded images while filtering out 1px decorative elements
- **Smart Filtering**: Ignores 1-pixel wide/tall images (decorative lines)
- **JSON Output**: Captions saved in structured JSON format for easy processing
- **Simple CLI**: Easy-to-use command-line interface

## Requirements

- Python 3.6+
- PyMuPDF (fitz)
- Pillow
- requests
- elasticsearch
- python-dotenv
- **Optional**: LM Studio with a vision-capable model for AI captions
- **Optional**: Elasticsearch cluster with E5 model configured for semantic search

## Environment Variables

All configuration is managed through environment variables in `.env` file:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `LM_STUDIO_URL` | LM Studio API endpoint | `http://localhost:1234/v1/chat/completions` | No |
| `LM_STUDIO_ENABLED` | Enable/disable LM Studio captioning | `true` | No |
| `ELASTICSEARCH_HOST` | Elasticsearch server URL | `http://localhost:9200` | Yes (for ingestion) |
| `ELASTICSEARCH_API_KEY` | API key for authentication | - | No* |
| `ELASTICSEARCH_USERNAME` | Username for basic auth | - | No* |
| `ELASTICSEARCH_PASSWORD` | Password for basic auth | - | No* |
| `ELASTICSEARCH_INDEX` | Index name for documents | `pdf_documents` | No |
| `ELASTICSEARCH_INFERENCE_ID` | Inference endpoint ID | `my_e5_model` | No |
| `ELASTICSEARCH_VERIFY_CERTS` | Verify SSL certificates | `true` | No |
| `ELASTICSEARCH_CA_CERTS` | Path to CA certificates | - | No |
| `PDF_RENDER_DPI` | DPI for page rendering | `150` | No |

*Either API key OR username/password required for authenticated Elasticsearch clusters.

## Example

```bash
python pdf_extractor.py my_report.pdf report_output
```

Output:
```
Extracting content from: my_report.pdf
Output directory: report_output

Extracting text...
Processing 3 pages...
Text successfully saved to: report_output/extracted_text.txt

Rendering pages to images...
  Rendered: report_output/page1_rendered.png (1275x1650px)
    Getting caption from LM Studio...
    Caption: This page shows a bar chart comparing quarterly sales data across four regions...
  Rendered: report_output/page2_rendered.png (1275x1650px)
    Getting caption from LM Studio...
    Caption: The page contains a line graph showing revenue trends over a 12-month period...
  Rendered: report_output/page3_rendered.png (1275x1650px)
    Getting caption from LM Studio...
    Caption: This page displays a pie chart breaking down market share by product category...
Rendered 3 page(s)

Captions saved to: report_output/page_captions.json

Extracting embedded images...
  Extracted: report_output/page1_img1.png (800x600px)
  Skipped: page2_img1 (1x800px - too small)
Extracted 1 embedded image(s)

Done! All content saved to: report_output/
```

## Output Structure

```
document_extracted/
├── extracted_text.txt
├── page_captions.json
├── page1_rendered.png
├── page2_rendered.png
├── page3_rendered.png
└── page1_img1.png
```

## LM Studio Setup

To get AI-generated captions for your PDF pages:

1. Download [LM Studio](https://lmstudio.ai/)
2. Load a vision model (recommended models):
   - **LLaVA 1.6** (7B or 13B)
   - **BakLLaVA**
   - Any other multimodal model that supports vision
3. Go to the "Server" tab in LM Studio
4. Click "Start Server" (default: http://localhost:1234)
5. Run the PDF extractor - it will automatically detect and use LM Studio

If LM Studio is not running, the app will still work but skip the captioning step.

## Caption Output Format

The `page_captions.json` file contains structured captions:

```json
{
  "page1": "This page shows a bar chart comparing quarterly sales data across four regions. The chart indicates strong growth in the North region with approximately 45% increase, while the South region shows modest 12% growth. Key insights include seasonal variations and regional performance metrics.",
  "page2": "The page contains a line graph showing revenue trends over a 12-month period...",
  "page3": "This page displays a pie chart breaking down market share..."
}
```

---

## Elasticsearch Integration

The application includes full Elasticsearch integration with semantic search capabilities using the E5 model.

### Index Schema

The Elasticsearch index uses the following mapping:

- **title** (text): Auto-derived document title from first meaningful text
- **filename** (keyword): Original PDF filename
- **main_text** (semantic_text): Full PDF text content with automatic E5 embeddings
- **page_descriptions** (nested array):
  - **page_number** (integer): Page number
  - **description_text** (text): AI-generated page description text (stored)
  - **description_vector** (dense_vector): E5 embedding vector (384 dims, cosine similarity)
    - **Auto-generated via ingest pipeline** from description_text during ingestion
  - **image_path** (keyword): Absolute path to rendered page image
  - **image_dimensions** (object): Width and height of the image
- **extracted_date** (date): Timestamp of extraction
- **total_pages** (integer): Total number of pages
- **output_directory** (keyword): Path to extraction directory

**Note:** Page descriptions use explicit `dense_vector` fields with an **automatic ingest pipeline** that generates embeddings from `description_text` during document ingestion. This provides more control over query construction with `query_vector_builder` or direct KNN searches, while eliminating the need for manual embedding generation.

### Setup Elasticsearch Index

Before ingesting documents, you need to set up the Elasticsearch index with the proper mappings.

**Prerequisites:**
1. Elasticsearch 8.x running and accessible
2. E5 inference endpoint configured (see [Elastic documentation](https://www.elastic.co/docs/solutions/search/semantic-search/semantic-search-semantic-text))

**Create the index:**

```bash
python elasticsearch_setup.py
```

**Options:**
```bash
python elasticsearch_setup.py --host http://localhost:9200 \
                               --index pdf_documents \
                               --inference-id my_e5_model
```

**Output:**
```
Connecting to Elasticsearch at http://localhost:9200...
Connected successfully!

Creating ingest pipeline 'pdf_documents_pipeline'...
✓ Ingest pipeline 'pdf_documents_pipeline' created successfully!

Creating index 'pdf_documents' with semantic_text mappings...
✓ Index 'pdf_documents' created successfully!
  Default pipeline: pdf_documents_pipeline

Index mapping:
  - title: text (with keyword subfield)
  - filename: keyword
  - main_text: semantic_text (using my_e5_model)
  - page_descriptions: nested array
    - page_number: integer
    - description_text: text (stores the caption)
    - description_vector: dense_vector (384 dims, cosine similarity)
      → Auto-generated via ingest pipeline from description_text
    - image_path: keyword
    - image_dimensions: object (width, height)
  - extracted_date: date
  - total_pages: integer
  - output_directory: keyword

✓ Setup complete! Ready to ingest PDF documents.
  Embeddings will be automatically generated during ingestion.
```

The setup script creates:
1. **Ingest Pipeline** (`pdf_documents_pipeline`): Automatically generates embeddings from `description_text` using the E5 model
2. **Index** with the pipeline set as default, ensuring all documents are processed automatically

### Ingest PDF Data

The ingest script can now accept **either a PDF file OR an extracted directory**:

**Option 1: Direct PDF ingestion (recommended - one command)**
```bash
python elasticsearch_ingest.py quarterly_report.pdf
```

**Option 2: Use pre-extracted directory**
```bash
python elasticsearch_ingest.py document_extracted/
```

**With options:**
```bash
python elasticsearch_ingest.py quarterly_report.pdf \
    --output-dir custom_output \
    --host http://localhost:9200 \
    --index pdf_documents
```

**Output (when ingesting PDF directly):**
```
============================================================
STEP 1: EXTRACTING PDF
============================================================

Extracting PDF: quarterly_report.pdf
Output directory: quarterly_report_extracted

Extracting content from: quarterly_report.pdf
Output directory: quarterly_report_extracted

Extracting text...
Processing 3 pages...
Text successfully saved to: quarterly_report_extracted/extracted_text.txt

Rendering pages to images...
  Rendered: quarterly_report_extracted/page1_rendered.png (1275x1650px)
    Getting caption from LM Studio...
    Caption: This page shows a bar chart comparing quarterly sales...
  Rendered: quarterly_report_extracted/page2_rendered.png (1275x1650px)
    Getting caption from LM Studio...
    Caption: The page contains a line graph showing revenue trends...
  Rendered: quarterly_report_extracted/page3_rendered.png (1275x1650px)
    Getting caption from LM Studio...
    Caption: This page displays a pie chart breaking down market share...
Rendered 3 page(s)

Captions saved to: quarterly_report_extracted/page_captions.json

Extracting embedded images...
Extracted 0 embedded image(s)

Done! All content saved to: quarterly_report_extracted/

✓ PDF extraction complete!

============================================================
STEP 2: INGESTING TO ELASTICSEARCH
============================================================

Reading extracted data from: quarterly_report_extracted
  ✓ Read text (15234 characters)
  ✓ Derived title: Quarterly Sales Report Q4 2024 Executive Summary
  ✓ Read 3 page captions

Connecting to Elasticsearch at http://localhost:9200...
Connected successfully!

Processing page descriptions...
  ✓ Prepared 3 page descriptions
  Note: Embeddings will be generated automatically by ingest pipeline

Indexing document to 'pdf_documents'...
✓ Document indexed successfully!
  Document ID: xY9zaBc123
  Index: pdf_documents
  Title: Quarterly Sales Report Q4 2024 Executive Summary
  Pages: 3
  Descriptions: 3

============================================================
✓ COMPLETE!
============================================================
PDF extracted and indexed successfully
Document ID: xY9zaBc123
```

### Complete Workflow Examples

**Simple workflow (recommended):**
```bash
# 1. Configure your environment (one-time setup)
cp .env.example .env
# Edit .env with your settings

# 2. Setup Elasticsearch index (one-time setup)
python elasticsearch_setup.py

# 3. Extract and ingest PDF in one command!
python elasticsearch_ingest.py quarterly_report.pdf

# Done! Document is now searchable with semantic search
```

**Advanced workflow (manual extraction first):**
```bash
# 1. Configure environment
cp .env.example .env

# 2. Setup Elasticsearch index
python elasticsearch_setup.py

# 3. Extract PDF separately (if you need to review/modify extracted data)
python pdf_extractor.py quarterly_report.pdf

# 4. Ingest pre-extracted data
python elasticsearch_ingest.py quarterly_report_extracted/

# Result: Document is searchable with semantic search
```

**Batch processing multiple PDFs:**
```bash
# Process multiple PDFs in sequence
for pdf in reports/*.pdf; do
  python elasticsearch_ingest.py "$pdf"
done
```

All scripts automatically use the `.env` configuration. Command-line arguments override environment variables if needed.

### Semantic Search Queries

Once ingested, you can perform semantic searches on your documents:

**Search main text:**
```json
GET /pdf_documents/_search
{
  "query": {
    "semantic": {
      "field": "main_text",
      "query": "revenue growth trends"
    }
  }
}
```

**Search page descriptions (using query_vector_builder):**
```json
GET /pdf_documents/_search
{
  "query": {
    "nested": {
      "path": "page_descriptions",
      "query": {
        "knn": {
          "field": "page_descriptions.description_vector",
          "query_vector_builder": {
            "text_embedding": {
              "model_id": "my_e5_model",
              "model_text": "bar chart showing regional sales"
            }
          },
          "k": 5,
          "num_candidates": 50
        }
      }
    }
  }
}
```

**Search description text (keyword search):**
```json
GET /pdf_documents/_search
{
  "query": {
    "nested": {
      "path": "page_descriptions",
      "query": {
        "match": {
          "page_descriptions.description_text": "bar chart regional sales"
        }
      }
    }
  }
}
```

**Combined semantic search (text + page descriptions):**
```json
GET /pdf_documents/_search
{
  "query": {
    "bool": {
      "should": [
        {
          "semantic": {
            "field": "main_text",
            "query": "quarterly performance metrics"
          }
        },
        {
          "nested": {
            "path": "page_descriptions",
            "query": {
              "knn": {
                "field": "page_descriptions.description_vector",
                "query_vector_builder": {
                  "text_embedding": {
                    "model_id": "my_e5_model",
                    "model_text": "quarterly performance metrics"
                  }
                },
                "k": 5,
                "num_candidates": 50
              }
            }
          }
        }
      ]
    }
  }
}
```

**Hybrid search (text + semantic vectors):**
```json
GET /pdf_documents/_search
{
  "query": {
    "nested": {
      "path": "page_descriptions",
      "query": {
        "bool": {
          "should": [
            {
              "match": {
                "page_descriptions.description_text": "sales performance"
              }
            },
            {
              "knn": {
                "field": "page_descriptions.description_vector",
                "query_vector_builder": {
                  "text_embedding": {
                    "model_id": "my_e5_model",
                    "model_text": "sales performance graphs"
                  }
                },
                "k": 5,
                "num_candidates": 50
              }
            }
          ]
        }
      }
    }
  }
}
```

### Benefits of Semantic Search

- **Natural language queries**: Search using conversational phrases
- **Graph/chart discovery**: Find documents with specific visualizations
- **Contextual understanding**: Matches based on meaning, not just keywords
- **Image-aware search**: Search descriptions of graphs and charts generated by LM Studio
- **Multi-field search**: Query both text content and visual descriptions
