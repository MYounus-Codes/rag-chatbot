"""
Product Service - Handles all product data loading and retrieval from /products directory.
Provides efficient caching and structured access to product information.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache


class ProductService:
    """Service for managing and retrieving product data from the products directory."""
    
    def __init__(self, products_path: str = "products"):
        self.products_path = Path(products_path)
        self._products_cache: Dict[str, Dict] = {}
        self._all_products_loaded = False
    
    def load_all_products(self) -> Dict[str, Dict]:
        """
        Load all products from the products directory.
        Returns a dictionary with product folder names as keys.
        """
        if self._all_products_loaded and self._products_cache:
            return self._products_cache
        
        if not self.products_path.exists():
            return {}
        
        for product_folder in self.products_path.iterdir():
            if product_folder.is_dir():
                product_data = self._load_product_folder(product_folder)
                if product_data:
                    self._products_cache[product_folder.name] = product_data
        
        self._all_products_loaded = True
        return self._products_cache
    
    def _load_product_folder(self, folder_path: Path) -> Optional[Dict]:
        """Load product data from a specific folder."""
        product_data = {
            "folder_name": folder_path.name,
            "main_info": None,
            "catalogues": {},
            "manuals": {}
        }
        
        # Load main product JSON file
        json_files = list(folder_path.glob("*.json"))
        if json_files:
            try:
                with open(json_files[0], 'r', encoding='utf-8') as f:
                    product_data["main_info"] = json.load(f)
            except Exception as e:
                print(f"Error loading {json_files[0]}: {e}")
        
        # Load catalogues
        catalogues_path = folder_path / "catalogues"
        if catalogues_path.exists():
            for catalogue_file in catalogues_path.glob("*.json"):
                lang_key = self._extract_language_from_filename(catalogue_file.name)
                try:
                    with open(catalogue_file, 'r', encoding='utf-8') as f:
                        product_data["catalogues"][lang_key] = json.load(f)
                except Exception:
                    pass
        
        # Load manuals if they exist
        manuals_path = folder_path / "manuals"
        if manuals_path.exists():
            for manual_file in manuals_path.glob("*.json"):
                lang_key = self._extract_language_from_filename(manual_file.name)
                try:
                    with open(manual_file, 'r', encoding='utf-8') as f:
                        product_data["manuals"][lang_key] = json.load(f)
                except Exception:
                    pass
        
        return product_data
    
    def _extract_language_from_filename(self, filename: str) -> str:
        """Extract language code from filename like 'Catalogue_English.json'."""
        lang_map = {
            "english": "en",
            "french": "fr", 
            "german": "de",
            "italian": "it",
            "spanish": "es",
            "danish": "da"
        }
        filename_lower = filename.lower()
        for lang_name, lang_code in lang_map.items():
            if lang_name in filename_lower:
                return lang_code
        return "en"
    
    def get_product_by_name(self, query: str) -> Optional[Dict]:
        """
        Find a product by matching query against product names/titles.
        Returns the best matching product or None.
        """
        self.load_all_products()
        query_lower = query.lower()
        
        best_match = None
        best_score = 0
        
        for folder_name, product_data in self._products_cache.items():
            score = self._calculate_match_score(query_lower, folder_name, product_data)
            if score > best_score:
                best_score = score
                best_match = product_data
        
        return best_match if best_score > 0 else None
    
    def _calculate_match_score(self, query: str, folder_name: str, product_data: Dict) -> int:
        """Calculate how well a product matches the query."""
        score = 0
        
        # Check folder name
        folder_lower = folder_name.lower()
        if query in folder_lower:
            score += 10
        
        # Check product title
        main_info = product_data.get("main_info", {})
        if main_info:
            product = main_info.get("product", main_info)
            title = product.get("title", "").lower()
            if query in title:
                score += 20
            
            # Check short description
            short_desc = product.get("short_description", "").lower()
            if query in short_desc:
                score += 5
            
            # Check categories
            categories = product.get("categories", [])
            for cat in categories:
                if query in cat.lower():
                    score += 3
            
            # Check tags
            tags = product.get("tags", [])
            for tag in tags:
                if query in tag.lower():
                    score += 2
        
        return score
    
    def search_products(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search for products matching the query.
        Returns a list of matching products sorted by relevance.
        """
        self.load_all_products()
        query_lower = query.lower()
        
        scored_products = []
        for folder_name, product_data in self._products_cache.items():
            score = self._calculate_match_score(query_lower, folder_name, product_data)
            if score > 0:
                scored_products.append((score, product_data))
        
        # Sort by score descending
        scored_products.sort(key=lambda x: x[0], reverse=True)
        
        return [p[1] for p in scored_products[:limit]]
    
    def get_all_product_names(self) -> List[str]:
        """Get a list of all product names/titles."""
        self.load_all_products()
        names = []
        
        for product_data in self._products_cache.values():
            main_info = product_data.get("main_info", {})
            if main_info:
                product = main_info.get("product", main_info)
                title = product.get("title", product_data.get("folder_name", "Unknown"))
                names.append(title)
        
        return names
    
    def get_product_info_formatted(self, product_data: Dict, language: str = "en") -> str:
        """
        Format product information for display.
        Returns a well-structured string with product details.
        """
        main_info = product_data.get("main_info", {})
        if not main_info:
            return "Product information not available."
        
        product = main_info.get("product", main_info)
        
        parts = []
        
        # Title
        title = product.get("title", "Unknown Product")
        parts.append(f"**{title}**\n")
        
        # Short description
        short_desc = product.get("short_description", "")
        if short_desc:
            parts.append(f"{short_desc}\n")
        
        # Long description
        long_desc = product.get("long_description", "")
        if long_desc:
            parts.append(f"\n{long_desc}\n")
        
        # Specifications
        specs = product.get("specs", {})
        if specs and isinstance(specs, dict):
            parts.append("\n**Specifications:**")
            for key, value in specs.items():
                if value and value != "N/A":
                    key_formatted = key.replace("_", " ").title()
                    parts.append(f"- {key_formatted}: {value}")
        
        # Categories
        categories = product.get("categories", [])
        if categories:
            parts.append(f"\n**Categories:** {', '.join(categories)}")
        
        # SKU
        identifiers = product.get("identifiers", {})
        sku = identifiers.get("sku", "")
        if sku and sku != "N/A":
            parts.append(f"\n**SKU:** {sku}")
        
        return "\n".join(parts)
    
    def get_catalogue_info(self, product_data: Dict, language: str = "en") -> Optional[str]:
        """Extract relevant catalogue information for a product."""
        catalogues = product_data.get("catalogues", {})
        
        # Try requested language, fallback to English
        catalogue = catalogues.get(language) or catalogues.get("en")
        
        if not catalogue:
            return None
        
        if isinstance(catalogue, list) and len(catalogue) > 0:
            # Extract markdown content from catalogue
            first_item = catalogue[0]
            if isinstance(first_item, dict):
                return first_item.get("markdown", str(first_item))
            return str(first_item)[:2000]  # Limit length
        
        return str(catalogue)[:2000]
    
    def get_products_by_category(self, category: str) -> List[Dict]:
        """Get all products in a specific category."""
        self.load_all_products()
        category_lower = category.lower()
        
        matching = []
        for product_data in self._products_cache.values():
            main_info = product_data.get("main_info", {})
            if main_info:
                product = main_info.get("product", main_info)
                categories = product.get("categories", [])
                tags = product.get("tags", [])
                
                all_cats = [c.lower() for c in categories + tags]
                if any(category_lower in c for c in all_cats):
                    matching.append(product_data)
        
        return matching
