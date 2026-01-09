import os
from pathlib import Path


def read_all_product_files(base_path: str = "products") -> dict:
    """
    Recursively read all files in the products folder and return their contents.
    Returns a dict with file paths as keys and file contents as values.
    """
    all_files = {}
    for root, dirs, files in os.walk(base_path):
        for file in files:
            file_path = Path(root) / file
            try:
                # Read as text, fallback to binary if error
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                all_files[str(file_path)] = content
            except Exception:
                try:
                    with open(file_path, "rb") as f:
                        content = f.read()
                    all_files[str(file_path)] = content
                except Exception:
                    all_files[str(file_path)] = None
    return all_files
