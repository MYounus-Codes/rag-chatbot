"""
Document Processing Script for RAG Chatbot
==========================================
This script processes PDF catalogues and source files to create structured JSON files
for use in a RAG (Retrieval-Augmented Generation) chatbot system.

Phase 1: Process PDF catalogues → Convert to structured JSON
Phase 2: Create main product metadata JSON from sourceFile.txt

Author: AI Assistant
Date: 2025-01-01
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import hashlib

# PDF Processing library
try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF not installed. Please run: pip install PyMuPDF")
    exit(1)


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input_pdfs"
OUTPUT_DIR = BASE_DIR / "output_pdfs"
EXAMPLE_DIR = BASE_DIR / "example_output"
MANUAL_INPUT_DIR = BASE_DIR / "input"  # For standalone manual JSON files

# Language mappings for catalogue naming
LANGUAGE_MAP = {
    "english": {"code": "en", "name": "English"},
    "danish": {"code": "da", "name": "Danish"},
    "german": {"code": "de", "name": "German"},
    "french": {"code": "fr", "name": "French"},
    "spanish": {"code": "es", "name": "Spanish"},
    "italian": {"code": "it", "name": "Italian"},
}

# Schema version
SCHEMA_VERSION = "1.0"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from product title."""
    slug = title.lower()
    slug = re.sub(r'[,.]', '', slug)
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug


def generate_product_id(title: str) -> str:
    """Generate a unique product ID from title."""
    slug = generate_slug(title)
    return slug[:50]  # Limit length


def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    
    # Fix encoding issues - replace common corrupted characters
    # Map of corrupted patterns to their proper replacements
    encoding_fixes = {
        'Ã©': 'é', 'Ã¨': 'è', 'Ã§': 'ç', 'Ã´': 'ô', 'Ã¢': 'â',
        'Ã': 'à', 'Ã¯': 'ï', 'Ã«': 'ë', 'Ã¹': 'ù', 'Ã»': 'û',
        'Ã': 'É', 'Ã‰': 'É', 'Ã': 'À', 'Ã‡': 'Ç', 'Ãª': 'ê',
        'â€™': "'", 'â€"': '-', 'â€"': '–', 'â€œ': '"', 'â€\x9d': '"',
        'â€¢': '•', 'â€¦': '...', '\u0002': '', '\u0003': '',
    }
    
    for corrupted, fixed in encoding_fixes.items():
        text = text.replace(corrupted, fixed)
    
    # Remove control characters and other corrupted text patterns
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    # Remove strange Unicode characters that look corrupted
    # This pattern matches many accented characters that appear corrupted
    text = re.sub(r'[Ä-Å›Ã][^\s]*[Ä-Å›Ã]', ' ', text)
    text = re.sub(r'[Æ-Ç][^\s]*', ' ', text)
    text = re.sub(r'[Ì-Í][^\s]*', ' ', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove image references and paths
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)  # Markdown images
    text = re.sub(r'<img[^>]*>', '', text)  # HTML img tags
    text = re.sub(r'\b(image|img|photo|picture|figure|fig\.?)[\s:]*\d*\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'([A-Z]:\\[^\s]+|/[^\s]+\.(png|jpg|jpeg|gif|svg|bmp|webp))', '', text, flags=re.IGNORECASE)
    
    # Remove video/click references
    text = re.sub(r'Video\s*-\s*Click to watch', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Click here', '', text, flags=re.IGNORECASE)
    
    # Clean up multiple spaces and newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    
    return text.strip()


def extract_language_from_filename(filename: str) -> Optional[dict]:
    """Extract language info from PDF filename."""
    filename_lower = filename.lower()
    for lang_key, lang_info in LANGUAGE_MAP.items():
        if lang_key in filename_lower:
            return lang_info
    return None


def get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def count_tokens_approx(text: str) -> int:
    """Approximate token count (rough estimate: ~4 chars per token)."""
    return len(text) // 4


# ============================================================================
# PDF PROCESSING FUNCTIONS
# ============================================================================

def extract_pdf_content(pdf_path: Path) -> list[dict]:
    """
    Extract content from PDF file using PyMuPDF.
    Returns a list of page dictionaries with markdown content.
    """
    pages = []
    
    try:
        doc = fitz.open(str(pdf_path))
        
        for page_num, page in enumerate(doc, 1):
            # Extract text with proper formatting
            text = page.get_text("text")
            
            if text and text.strip():
                # Clean the extracted text
                cleaned_text = clean_text(text)
                
                if cleaned_text:
                    pages.append({
                        "page_number": page_num,
                        "text": cleaned_text
                    })
        
        doc.close()
        
    except Exception as e:
        print(f"    ERROR extracting PDF {pdf_path.name}: {e}")
        return []
    
    return pages


def process_pdf_to_markdown(pdf_path: Path) -> str:
    """
    Convert PDF to clean markdown content.
    Removes visual elements and keeps only textual content.
    """
    markdown_content = []
    
    try:
        doc = fitz.open(str(pdf_path))
        
        for page_num, page in enumerate(doc, 1):
            # Get text blocks for better structure preservation
            blocks = page.get_text("dict")["blocks"]
            
            page_text = []
            for block in blocks:
                if block["type"] == 0:  # Text block (not image)
                    for line in block.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                # Check if it's a heading (larger font or bold)
                                font_size = span.get("size", 12)
                                flags = span.get("flags", 0)
                                is_bold = flags & 2 ** 4  # Bold flag
                                
                                if font_size > 14 or is_bold:
                                    if text and not text.startswith("#"):
                                        text = f"# {text}"
                                
                                line_text += text + " "
                        
                        if line_text.strip():
                            page_text.append(line_text.strip())
            
            if page_text:
                markdown_content.append("\n".join(page_text))
        
        doc.close()
        
    except Exception as e:
        print(f"    ERROR processing PDF {pdf_path.name}: {e}")
        return ""
    
    # Combine and clean the content
    full_content = "\n\n".join(markdown_content)
    return clean_text(full_content)


def create_catalogue_json(pdf_path: Path, language_info: dict) -> dict:
    """
    Create structured JSON from PDF catalogue.
    Following the schema from example_output catalogues.
    """
    # Extract markdown content from PDF
    markdown_content = process_pdf_to_markdown(pdf_path)
    
    if not markdown_content:
        # Fallback: try simple text extraction
        pages = extract_pdf_content(pdf_path)
        if pages:
            markdown_content = "\n\n".join([p["text"] for p in pages])
    
    # Create JSON structure matching example_output format
    catalogue_data = [
        {
            "markdown": markdown_content
        }
    ]
    
    return catalogue_data


# ============================================================================
# MANUAL JSON PROCESSING FUNCTIONS
# ============================================================================

def clean_manual_json(manual_path: Path, language_info: dict) -> dict:
    """
    Clean and process manual JSON files.
    Returns structured JSON with cleaned content.
    """
    try:
        with open(manual_path, 'r', encoding='utf-8') as f:
            manual_data = json.load(f)
    except Exception as e:
        print(f"    ERROR reading manual JSON {manual_path.name}: {e}")
        return None
    
    # Process the JSON content
    if isinstance(manual_data, list):
        cleaned_data = []
        for item in manual_data:
            if isinstance(item, dict) and 'markdown' in item:
                # Clean the markdown content
                cleaned_markdown = clean_text(item['markdown'])
                cleaned_data.append({
                    "markdown": cleaned_markdown
                })
            else:
                # Keep other structures as is
                cleaned_data.append(item)
        return cleaned_data
    else:
        print(f"    WARNING: Unexpected manual JSON structure in {manual_path.name}")
        return manual_data


# ============================================================================
# SOURCE FILE PARSING
# ============================================================================

def parse_source_file(source_path: Path) -> dict:
    """
    Parse sourceFile.txt and extract product information.
    Returns structured product data.
    """
    product_info = {
        "title": "",
        "description": "",
        "short_description": "",
        "long_description": "",
        "sku": None,
        "category": None,
        "categories": [],
        "tags": [],
        "weight": None,
        "dimensions": None,
        "features": [],
        "specs": {},
        "additional_info": {}
    }
    
    try:
        content = source_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"    ERROR reading source file: {e}")
        return product_info
    
    lines = content.split("\n")
    current_section = None
    description_text = []
    features_text = []
    
    # Keywords that indicate end of description section
    end_description_keywords = ["about:", "sku:", "category:", "categories:", "tags:", 
                                 "additional information", "catalogues are in", "all above files"]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()
        line_lower = line_stripped.lower()
        
        # Skip empty lines in certain contexts
        if not line_stripped:
            i += 1
            continue
        
        # Detect section headers
        if line_lower.startswith("title:"):
            current_section = "title"
            value = line_stripped[6:].strip()
            if value:
                product_info["title"] = value
                current_section = None
            i += 1
            continue
        
        # Handle title on next line
        if current_section == "title" and line_stripped:
            product_info["title"] = line_stripped
            current_section = None
            i += 1
            continue
        
        # Description section - check various formats
        if any(line_lower.startswith(x) for x in ["description/information/details:", "description:", "description/information:"]):
            current_section = "description"
            # Get value after colon if on same line
            colon_idx = line_stripped.find(":")
            if colon_idx > -1:
                value = line_stripped[colon_idx + 1:].strip()
                if value:
                    description_text.append(value)
            i += 1
            continue
        
        # About/Features section
        if line_lower.startswith("about:"):
            # Save any collected description first
            if description_text:
                product_info["long_description"] = " ".join(description_text)
            current_section = "features"
            i += 1
            continue
        
        # SKU
        if line_lower.startswith("sku:"):
            if current_section == "description" and description_text:
                product_info["long_description"] = " ".join(description_text)
            sku_val = line_stripped[4:].strip()
            if sku_val:
                product_info["sku"] = sku_val
            current_section = None
            i += 1
            continue
        
        # Category
        if line_lower.startswith("category:"):
            if current_section == "description" and description_text:
                product_info["long_description"] = " ".join(description_text)
            product_info["category"] = line_stripped[9:].strip()
            current_section = None
            i += 1
            continue
        
        # Categories
        if line_lower.startswith("categories:"):
            if current_section == "description" and description_text:
                product_info["long_description"] = " ".join(description_text)
            cats = line_stripped[11:].strip()
            product_info["categories"] = [c.strip() for c in cats.split(",") if c.strip()]
            current_section = None
            i += 1
            continue
        
        # Tags
        if line_lower.startswith("tags:"):
            if current_section == "description" and description_text:
                product_info["long_description"] = " ".join(description_text)
            tags = line_stripped[5:].strip()
            product_info["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
            current_section = None
            i += 1
            continue
        
        # Weight
        if line_lower.startswith("weight"):
            if current_section == "description" and description_text:
                product_info["long_description"] = " ".join(description_text)
            match = re.search(r'weight[:\s\t]+([^\n]+)', line_stripped, re.IGNORECASE)
            if match:
                weight_val = match.group(1).strip()
                if weight_val.lower() not in ["n/a", ""]:
                    product_info["weight"] = weight_val
            current_section = None
            i += 1
            continue
        
        # Dimensions
        if line_lower.startswith("dimensions"):
            match = re.search(r'dimensions[:\s\t]+([^\n]+)', line_stripped, re.IGNORECASE)
            if match:
                dim_val = match.group(1).strip()
                if dim_val.lower() not in ["n/a", ""]:
                    product_info["dimensions"] = dim_val
            current_section = None
            i += 1
            continue
        
        # Additional information section
        if line_lower.startswith("additional information"):
            if current_section == "description" and description_text:
                product_info["long_description"] = " ".join(description_text)
            current_section = "additional"
            i += 1
            continue
        
        # End markers
        if line_lower.startswith("catalogues are in") or line_lower.startswith("all above files"):
            if current_section == "description" and description_text:
                product_info["long_description"] = " ".join(description_text)
            current_section = None
            i += 1
            continue
        
        # Collect content for current section
        if current_section == "description" and line_stripped:
            # Check if this line starts a new section
            is_new_section = any(line_lower.startswith(kw) for kw in end_description_keywords)
            if not is_new_section:
                description_text.append(line_stripped)
        
        elif current_section == "features" and line_stripped:
            # Features are often key-value pairs or bullet points
            if ":" in line_stripped:
                parts = line_stripped.split(":", 1)
                key = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else ""
                if key and value:
                    product_info["specs"][key.lower().replace(" ", "_")] = value
                features_text.append(line_stripped)
            else:
                features_text.append(line_stripped)
        
        elif current_section == "additional" and line_stripped:
            # Parse key-value pairs in additional info
            if ":" in line_stripped or "\t" in line_stripped:
                parts = re.split(r'[:\t]+', line_stripped, 1)
                if len(parts) == 2:
                    key = parts[0].strip().lower().replace(" ", "_")
                    value = parts[1].strip()
                    if value.lower() not in ["n/a", ""]:
                        product_info["additional_info"][key] = value
        
        i += 1
    
    # Final save of description if still in that section
    if current_section == "description" and description_text:
        product_info["long_description"] = " ".join(description_text)
    
    # Store features
    if features_text:
        product_info["features"] = features_text
    
    # Create short description from long description
    long_desc = product_info.get("long_description", "")
    if long_desc:
        # First sentence or first 200 chars
        sentences = long_desc.split(".")
        if sentences and len(sentences[0]) < 200:
            product_info["short_description"] = sentences[0].strip() + "."
        else:
            product_info["short_description"] = long_desc[:200].rsplit(" ", 1)[0] + "..."
    
    return product_info


# ============================================================================
# MAIN PRODUCT JSON CREATION
# ============================================================================

def create_product_json(product_name: str, product_info: dict, catalogue_files: list[str]) -> dict:
    """
    Create main product metadata JSON following the schema from storm2000.json.
    """
    timestamp = get_timestamp()
    product_id = generate_product_id(product_info.get("title", product_name))
    slug = generate_slug(product_info.get("title", product_name))
    
    # Determine product type from categories or title
    title_lower = product_info.get("title", "").lower()
    categories = product_info.get("categories", [])
    category = product_info.get("category", "")
    
    product_type = "accessory"  # Default
    if any(x in title_lower for x in ["garage", "home", "shelter"]):
        product_type = "garage"
    elif any(x in title_lower for x in ["cable", "wire"]):
        product_type = "boundary-cable"
    elif any(x in title_lower for x in ["blade"]):
        product_type = "blade"
    elif any(x in title_lower for x in ["tracker"]):
        product_type = "tool"
    elif any(x in title_lower for x in ["heat gun", "tool"]):
        product_type = "tool"
    elif any(x in title_lower for x in ["connector", "peg"]):
        product_type = "connector"
    
    # Build specs from parsed info
    specs = {}
    if product_info.get("weight"):
        specs["weight"] = product_info["weight"]
    if product_info.get("dimensions"):
        specs["dimensions"] = product_info["dimensions"]
    
    # Add any additional specs from features
    for feature in product_info.get("features", []):
        if ":" in feature:
            key, value = feature.split(":", 1)
            specs[key.strip().lower().replace(" ", "_")] = value.strip()
    
    # Add additional_info specs
    specs.update(product_info.get("additional_info", {}))
    
    if not specs:
        specs["notes"] = "See catalogue for detailed specifications."
    
    # Build source files list
    source_files = [
        {
            "type": "product_details",
            "filename": "sourceFile.txt",
            "language": "en"
        }
    ]
    
    for cat_file in catalogue_files:
        lang_info = extract_language_from_filename(cat_file)
        if lang_info:
            source_files.append({
                "type": "catalogue",
                "filename": cat_file,
                "language": lang_info["code"]
            })
    
    # Build tags
    tags = product_info.get("tags", [])
    if not tags:
        # Generate tags from title
        words = product_info.get("title", product_name).split()
        tags = [w for w in words if len(w) > 2 and w.lower() not in ["the", "and", "for"]]
    
    # Build categories
    final_categories = product_info.get("categories", [])
    if not final_categories and category:
        final_categories = [category]
    
    # Create documents section
    documents = [
        {
            "doc_id": f"proddetail-en-{product_id[:8]}",
            "doc_type": "product_details",
            "language": "en",
            "source": "sourceFile.txt",
            "pages": [
                {
                    "page_number": 1,
                    "heading": "Product Overview",
                    "text": product_info.get("long_description", product_info.get("short_description", ""))
                }
            ]
        }
    ]
    
    # Add catalogue document references
    for cat_file in catalogue_files:
        lang_info = extract_language_from_filename(cat_file)
        if lang_info:
            documents.append({
                "doc_id": f"catalogue-{lang_info['code']}-{product_id[:8]}",
                "doc_type": "catalogue",
                "language": lang_info["code"],
                "source": cat_file,
                "pages": [
                    {
                        "page_number": 1,
                        "heading": f"Catalogue Reference ({lang_info['name']})",
                        "text": f"See attached catalogue for product family context and specifications. ({lang_info['name']} catalogue included.)"
                    }
                ],
                "metadata": {
                    "attached_file": cat_file
                }
            })
    
    # Create chunks for RAG retrieval
    chunks = []
    
    # Overview chunk
    overview_text = product_info.get("short_description", "")
    if overview_text:
        chunks.append({
            "chunk_id": f"c-{product_id[:10]}-overview-0001",
            "doc_id": f"proddetail-en-{product_id[:8]}",
            "language": "en",
            "doc_type": "product_details",
            "page_number": 1,
            "heading": "Overview",
            "chunk_index": 0,
            "text": overview_text,
            "token_count": count_tokens_approx(overview_text),
            "metadata": {
                "product_id": product_id,
                "source": "sourceFile.txt"
            }
        })
    
    # Description chunk
    long_desc = product_info.get("long_description", "")
    if long_desc and long_desc != overview_text:
        chunks.append({
            "chunk_id": f"c-{product_id[:10]}-desc-0002",
            "doc_id": f"proddetail-en-{product_id[:8]}",
            "language": "en",
            "doc_type": "product_details",
            "page_number": 1,
            "heading": "Description",
            "chunk_index": 1,
            "text": long_desc[:500],  # Limit chunk size
            "token_count": count_tokens_approx(long_desc[:500]),
            "metadata": {
                "product_id": product_id,
                "source": "sourceFile.txt"
            }
        })
    
    # Features chunk
    features = product_info.get("features", [])
    if features:
        features_text = "Features: " + ", ".join(features)
        chunks.append({
            "chunk_id": f"c-{product_id[:10]}-feat-0003",
            "doc_id": f"proddetail-en-{product_id[:8]}",
            "language": "en",
            "doc_type": "product_details",
            "page_number": 1,
            "heading": "Features",
            "chunk_index": 2,
            "text": features_text,
            "token_count": count_tokens_approx(features_text),
            "metadata": {
                "product_id": product_id,
                "source": "sourceFile.txt"
            }
        })
    
    # Build final JSON structure
    product_json = {
        "schema_version": SCHEMA_VERSION,
        "product": {
            "product_id": product_id,
            "slug": slug,
            "title": product_info.get("title", product_name),
            "short_description": product_info.get("short_description", ""),
            "long_description": product_info.get("long_description", ""),
            "brand": "AM ROBOTS",
            "product_type": product_type,
            "categories": final_categories,
            "tags": tags,
            "identifiers": {
                "sku": product_info.get("sku"),
                "manufacturer": "AM ROBOTS"
            },
            "specs": specs,
            "variants": [],  # Can be populated if variant info is available
            "created_at": timestamp,
            "updated_at": timestamp,
            "source_files": source_files
        },
        "documents": documents,
        "chunks": chunks,
        "provenance": {
            "ingested_at": timestamp,
            "ingested_by": "document-processor-v1.0",
            "raw_files": ["sourceFile.txt"] + catalogue_files
        }
    }
    
    return product_json


# ============================================================================
# MAIN PROCESSING FUNCTIONS
# ============================================================================

def process_product(product_folder: Path, output_base: Path) -> bool:
    """
    Process a single product folder.
    Returns True if successful, False otherwise.
    """
    product_name = product_folder.name
    print(f"\n{'='*60}")
    print(f"Processing: {product_name}")
    print(f"{'='*60}")
    
    # Create output folder structure
    output_folder = output_base / product_name
    output_catalogues = output_folder / "catalogues"
    output_manuals = output_folder / "manuals"
    output_catalogues.mkdir(parents=True, exist_ok=True)
    output_manuals.mkdir(parents=True, exist_ok=True)
    
    # Track processed catalogue files
    processed_catalogues = []
    processed_manuals = []
    
    # ========== PHASE 1: Process PDF Catalogues ==========
    print("\n[PHASE 1] Processing PDF Catalogues...")
    
    catalogues_folder = product_folder / "catalogues"
    if catalogues_folder.exists():
        pdf_files = list(catalogues_folder.glob("*.pdf"))
        
        if pdf_files:
            for pdf_file in pdf_files:
                print(f"  - Processing: {pdf_file.name}")
                
                # Extract language from filename
                lang_info = extract_language_from_filename(pdf_file.name)
                
                if lang_info:
                    output_filename = f"Catalogue_{lang_info['name']}.json"
                else:
                    # Fallback naming
                    base_name = pdf_file.stem.replace("Catalogue 2025-26_", "").replace("Catalogue_", "")
                    output_filename = f"Catalogue_{base_name}.json"
                
                # Process PDF to JSON
                catalogue_data = create_catalogue_json(pdf_file, lang_info or {"code": "en", "name": "English"})
                
                # Save catalogue JSON
                output_path = output_catalogues / output_filename
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(catalogue_data, f, indent=2, ensure_ascii=False)
                
                processed_catalogues.append(output_filename)
                print(f"    ✓ Saved: {output_filename}")
        else:
            print("  - No PDF files found in catalogues folder")
    else:
        print("  - No catalogues folder found")
    
    # ========== PHASE 1B: Process Manual JSON files ==========
    print("\n[PHASE 1B] Processing Manual JSON files...")
    
    manuals_folder = product_folder / "manuals"
    if manuals_folder.exists():
        json_files = list(manuals_folder.glob("*.json"))
        
        if json_files:
            for json_file in json_files:
                print(f"  - Processing: {json_file.name}")
                
                # Extract language from filename
                lang_info = extract_language_from_filename(json_file.name)
                
                if lang_info:
                    output_filename = json_file.name
                else:
                    # Keep original filename
                    output_filename = json_file.name
                
                # Clean the manual JSON
                cleaned_data = clean_manual_json(json_file, lang_info or {"code": "en", "name": "English"})
                
                if cleaned_data is not None:
                    # Save cleaned manual JSON
                    output_path = output_manuals / output_filename
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
                    
                    processed_manuals.append(output_filename)
                    print(f"    ✓ Saved: {output_filename}")
        else:
            print("  - No JSON files found in manuals folder")
    else:
        print("  - No manuals folder found")
    
    # ========== PHASE 2: Create Main Product JSON ==========
    print("\n[PHASE 2] Creating Main Product JSON...")
    
    source_file = product_folder / "sourceFile.txt"
    if source_file.exists():
        print(f"  - Parsing: sourceFile.txt")
        product_info = parse_source_file(source_file)
        
        # Use folder name if title not found
        if not product_info.get("title"):
            product_info["title"] = product_name
        
        # Create main product JSON
        product_json = create_product_json(product_name, product_info, processed_catalogues)
        
        # Generate output filename from product name
        safe_filename = re.sub(r'[<>:"/\\|?*]', '', product_name.lower())
        safe_filename = re.sub(r'\s+', '_', safe_filename)
        output_filename = f"{safe_filename}.json"
        
        output_path = output_folder / output_filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(product_json, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Saved: {output_filename}")
    else:
        print("  - WARNING: sourceFile.txt not found")
        return False
    
    print(f"\n✓ Product '{product_name}' processed successfully!")
    return True


def process_standalone_manuals():
    """Process standalone manual JSON files from input/ directory."""
    print("\n" + "="*70)
    print("   PROCESSING STANDALONE MANUAL JSON FILES")
    print("="*70)
    
    if not MANUAL_INPUT_DIR.exists():
        print(f"\nNo manual input directory found: {MANUAL_INPUT_DIR}")
        return 0
    
    # Get all JSON files from input directory
    json_files = list(MANUAL_INPUT_DIR.glob("*.json"))
    
    if not json_files:
        print(f"\nNo JSON files found in: {MANUAL_INPUT_DIR}")
        return 0
    
    print(f"\nFound {len(json_files)} manual JSON files to process")
    
    # Create output directory for standalone manuals
    standalone_output = OUTPUT_DIR / "standalone_manuals"
    standalone_output.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    failed_count = 0
    
    for json_file in json_files:
        try:
            print(f"\n  Processing: {json_file.name}")
            
            # Extract language from filename
            lang_info = extract_language_from_filename(json_file.name)
            
            # Clean the manual JSON
            cleaned_data = clean_manual_json(json_file, lang_info or {"code": "en", "name": "English"})
            
            if cleaned_data is not None:
                # Save cleaned manual JSON
                output_path = standalone_output / json_file.name
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
                
                print(f"    ✓ Saved: {json_file.name}")
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"    ERROR processing {json_file.name}: {e}")
            failed_count += 1
    
    print(f"\n  ✓ Successfully processed: {success_count} manual files")
    if failed_count > 0:
        print(f"  ✗ Failed: {failed_count} manual files")
    
    return success_count


def main():
    """Main entry point for document processing."""
    print("="*70)
    print("   DOCUMENT PROCESSING SCRIPT FOR RAG CHATBOT")
    print("   Processing PDFs, Manuals and creating structured JSON files")
    print("="*70)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # ========== PART 1: Process products with PDFs ==========
    if INPUT_DIR.exists():
        # Get all product folders
        product_folders = [f for f in INPUT_DIR.iterdir() if f.is_dir()]
        
        if product_folders:
            print(f"\nFound {len(product_folders)} products to process:")
            for folder in product_folders:
                print(f"  - {folder.name}")
            
            # Process each product
            success_count = 0
            failed_count = 0
            
            for product_folder in product_folders:
                try:
                    if process_product(product_folder, OUTPUT_DIR):
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    print(f"\nERROR processing {product_folder.name}: {e}")
                    failed_count += 1
            
            print("\n" + "="*70)
            print("   PDF PROCESSING COMPLETE")
            print("="*70)
            print(f"  ✓ Successfully processed: {success_count} products")
            if failed_count > 0:
                print(f"  ✗ Failed: {failed_count} products")
        else:
            print(f"\nNo product folders found in: {INPUT_DIR}")
    else:
        print(f"\nInput directory not found: {INPUT_DIR}")
    
    # ========== PART 2: Process standalone manual JSON files ==========
    manual_count = process_standalone_manuals()
    
    # Final Summary
    print("\n" + "="*70)
    print("   ALL PROCESSING COMPLETE")
    print("="*70
        print(f"  - Parsing: sourceFile.txt")
        product_info = parse_source_file(source_file)
        
        # Use folder name if title not found
        if not product_info.get("title"):
            product_info["title"] = product_name
        
        # Create main product JSON
        product_json = create_product_json(product_name, product_info, processed_catalogues)
        
        # Generate output filename from product name
        safe_filename = re.sub(r'[<>:"/\\|?*]', '', product_name.lower())
        safe_filename = re.sub(r'\s+', '_', safe_filename)
        output_filename = f"{safe_filename}.json"
        
        output_path = output_folder / output_filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(product_json, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Saved: {output_filename}")
    else:
        print("  - WARNING: sourceFile.txt not found")
        return False
    
    print(f"\n✓ Product '{product_name}' processed successfully!")
    return True


def main():
    """Main entry point for document processing."""
    print("="*70)
    print("   DOCUMENT PROCESSING SCRIPT FOR RAG CHATBOT")
    print("   Processing PDFs and creating structured JSON files")
    print("="*70)
    
    # Verify directories exist
    if not INPUT_DIR.exists():
        print(f"\nERROR: Input directory not found: {INPUT_DIR}")
        return
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get all product folders
    product_folders = [f for f in INPUT_DIR.iterdir() if f.is_dir()]
    
    if not product_folders:
        print(f"\nNo product folders found in: {INPUT_DIR}")
        return
    
    print(f"\nFound {len(product_folders)} products to process:")
    for folder in product_folders:
        print(f"  - {folder.name}")
    
    # Process each product
    success_count = 0
    failed_count = 0
    
    for product_folder in product_folders:
        try:
            if process_product(product_folder, OUTPUT_DIR):
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"\nERROR processing {product_folder.name}: {e}")
            failed_count += 1
    
    # Summary
    print("\n" + "="*70)
    print("   PROCESSING COMPLETE")
    print("="*70)
    print(f"  ✓ Successfully processed: {success_count} products")
    if failed_count > 0:
        print(f"  ✗ Failed: {failed_count} products")
    print(f"\n  Output directory: {OUTPUT_DIR}")
    print("="*70)


if __name__ == "__main__":
    main()
