"""
Clean Manual JSON Files Script
================================
This script specifically processes and cleans manual JSON files
from the input/ directory, removing encoding issues and corrupted text.
"""

import os
import json
import re
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output" / "cleaned_manuals"

# Language mappings
LANGUAGE_MAP = {
    "english": {"code": "en", "name": "English"},
    "danish": {"code": "da", "name": "Danish"},
    "german": {"code": "de", "name": "German"},
    "french": {"code": "fr", "name": "French"},
    "spanish": {"code": "es", "name": "Spanish"},
    "italian": {"code": "it", "name": "Italian"},
}


def clean_text(text: str) -> str:
    """Clean and normalize text content, removing encoding issues."""
    if not text:
        return ""
    
    # Fix common encoding issues
    encoding_fixes = {
        'Ã©': 'é', 'Ã¨': 'è', 'Ã§': 'ç', 'Ã´': 'ô', 'Ã¢': 'â',
        'Ã': 'à', 'Ã¯': 'ï', 'Ã«': 'ë', 'Ã¹': 'ù', 'Ã»': 'û',
        'Ã': 'É', 'Ã‰': 'É', 'Ã': 'À', 'Ã‡': 'Ç', 'Ãª': 'ê',
        'â€™': "'", 'â€"': '-', 'â€"': '–', 'â€œ': '"', 'â€\x9d': '"',
        'â€¢': '•', 'â€¦': '...', '\u0002': '', '\u0003': '',
    }
    
    for corrupted, fixed in encoding_fixes.items():
        text = text.replace(corrupted, fixed)
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    # Remove corrupted Unicode patterns (these appear as gibberish)
    # Pattern matches sequences like "Ä›Â¼Å²Ä£" which are clearly corrupted
    text = re.sub(r'[Ä-ÆË][^\s]{0,3}', '', text)
    text = re.sub(r'[Ì-Í][^\s]{0,2}', '', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    
    # Remove image references
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'<img[^>]*>', '', text)
    text = re.sub(r'\b(image|img|photo|picture|figure|fig\.?)[\s:]*\d*\b', '', text, flags=re.IGNORECASE)
    
    # Clean up
    text = re.sub(r' +', ' ', text)
    
    return text.strip()


def extract_language_from_filename(filename: str) -> dict:
    """Extract language info from filename."""
    filename_lower = filename.lower()
    for lang_key, lang_info in LANGUAGE_MAP.items():
        if lang_key in filename_lower:
            return lang_info
    return {"code": "en", "name": "English"}


def clean_manual_json(manual_path: Path) -> dict:
    """Clean and process manual JSON file."""
    print(f"  Processing: {manual_path.name}")
    
    try:
        with open(manual_path, 'r', encoding='utf-8') as f:
            manual_data = json.load(f)
    except Exception as e:
        print(f"    ERROR reading file: {e}")
        return None
    
    # Process the JSON content
    if isinstance(manual_data, list):
        cleaned_data = []
        for item in manual_data:
            if isinstance(item, dict) and 'markdown' in item:
                # Clean the markdown content
                original_len = len(item['markdown'])
                cleaned_markdown = clean_text(item['markdown'])
                cleaned_len = len(cleaned_markdown)
                
                print(f"    Cleaned: {original_len} chars → {cleaned_len} chars ({original_len - cleaned_len} removed)")
                
                cleaned_data.append({
                    "markdown": cleaned_markdown
                })
            else:
                # Keep other structures as is
                cleaned_data.append(item)
        return cleaned_data
    else:
        print(f"    WARNING: Unexpected JSON structure")
        return manual_data


def main():
    """Main entry point."""
    print("="*70)
    print("   MANUAL JSON CLEANING SCRIPT")
    print("="*70)
    
    if not INPUT_DIR.exists():
        print(f"\nERROR: Input directory not found: {INPUT_DIR}")
        return
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get all JSON files
    json_files = list(INPUT_DIR.glob("*.json"))
    
    if not json_files:
        print(f"\nNo JSON files found in: {INPUT_DIR}")
        return
    
    print(f"\nFound {len(json_files)} JSON files to process\n")
    
    success_count = 0
    failed_count = 0
    
    for json_file in json_files:
        try:
            # Extract language
            lang_info = extract_language_from_filename(json_file.name)
            
            # Clean the JSON
            cleaned_data = clean_manual_json(json_file)
            
            if cleaned_data is not None:
                # Save cleaned JSON
                output_path = OUTPUT_DIR / json_file.name
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
                
                print(f"    ✓ Saved to: {output_path.name}\n")
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"    ERROR: {e}\n")
            failed_count += 1
    
    # Summary
    print("="*70)
    print("   PROCESSING COMPLETE")
    print("="*70)
    print(f"  ✓ Successfully processed: {success_count} files")
    if failed_count > 0:
        print(f"  ✗ Failed: {failed_count} files")
    print(f"\n  Output directory: {OUTPUT_DIR}")
    print("="*70)


if __name__ == "__main__":
    main()
