"""
Brand Service - Handles AM ROBOTS brand information from am-robots.json.
"""

import json
from pathlib import Path
from typing import Dict, Optional, List


class BrandService:
    """Service for managing and retrieving AM ROBOTS brand information."""
    
    def __init__(self, brand_file_path: str = "am-robots.json"):
        self.brand_file_path = Path(brand_file_path)
        self._brand_data: Optional[Dict] = None
    
    def load_brand_data(self) -> Dict:
        """Load brand data from the JSON file."""
        if self._brand_data:
            return self._brand_data
        
        try:
            with open(self.brand_file_path, 'r', encoding='utf-8') as f:
                self._brand_data = json.load(f)
        except Exception as e:
            print(f"Error loading brand data: {e}")
            self._brand_data = {}
        
        return self._brand_data
    
    def get_brand_info(self) -> Dict:
        """Get basic brand information."""
        data = self.load_brand_data()
        return data.get("brand", {})
    
    def get_brand_description(self) -> str:
        """Get formatted brand description."""
        brand = self.get_brand_info()
        
        parts = [
            f"**{brand.get('name', 'AM ROBOTS')}**",
            f"\n{brand.get('description', '')}",
            f"\n**Headquarters:** {brand.get('headquarters_country', 'Denmark')}",
            f"**Founded:** {brand.get('founded_year', 2019)}",
            f"**Industry:** {brand.get('industry', 'Robotic lawnmower equipment')}",
            f"**Website:** {brand.get('website', 'https://am-robots.com/')}"
        ]
        
        return "\n".join(parts)
    
    def get_positioning(self) -> Dict:
        """Get brand positioning information."""
        data = self.load_brand_data()
        return data.get("positioning", {})
    
    def get_vision_mission(self) -> str:
        """Get formatted vision and mission statement."""
        positioning = self.get_positioning()
        
        parts = []
        
        vision = positioning.get("vision", "")
        if vision:
            parts.append(f"**Vision:** {vision}")
        
        mission = positioning.get("mission", "")
        if mission:
            parts.append(f"\n**Mission:** {mission}")
        
        values = positioning.get("values", [])
        if values:
            parts.append(f"\n**Values:** {', '.join(values)}")
        
        return "\n".join(parts)
    
    def get_product_categories(self) -> List[str]:
        """Get list of product categories."""
        data = self.load_brand_data()
        products_services = data.get("products_and_services", {})
        return products_services.get("categories", [])
    
    def get_commercial_terms(self) -> str:
        """Get formatted commercial terms information."""
        data = self.load_brand_data()
        terms = data.get("commercial_terms", {})
        
        parts = ["**Commercial Terms:**\n"]
        
        # Shipping
        shipping = terms.get("shipping", {})
        threshold = shipping.get("free_shipping_threshold_eur", 1500)
        regions = shipping.get("free_shipping_regions", [])
        parts.append(f"**Free Shipping:** Orders over €{threshold} in {', '.join(regions)}")
        
        # Credit
        credit = terms.get("credit_terms", {})
        credit_days = credit.get("standard_credit_days", 14)
        parts.append(f"\n**Credit Terms:** {credit_days} days (subject to credit validation)")
        
        # Price policy
        price_policy = terms.get("price_policy", {})
        if price_policy.get("price_match"):
            parts.append(f"\n**Price Guarantee:** We match competing offers and can offer up to 10% below on quality products for dealers")
        
        return "\n".join(parts)
    
    def get_team_contact(self, region: str = None) -> str:
        """Get team contact information, optionally filtered by region."""
        data = self.load_brand_data()
        team = data.get("company_team", {}).get("sales_and_marketing", [])
        
        if not team:
            contact = data.get("contact", {})
            return f"**Contact:** {contact.get('general_email', 'info@am-robots.com')}"
        
        parts = ["**Sales & Support Team:**\n"]
        
        for member in team:
            name = member.get("name", "")
            role = member.get("role", "")
            regions = member.get("regions", [])
            email = member.get("email", "")
            phone = member.get("phone", "")
            
            # Filter by region if specified
            if region:
                region_lower = region.lower()
                if not any(region_lower in r.lower() for r in regions):
                    continue
            
            parts.append(f"**{name}** - {role}")
            parts.append(f"  Regions: {', '.join(regions)}")
            if email:
                parts.append(f"  Email: {email}")
            if phone:
                parts.append(f"  Phone: {phone}")
            parts.append("")
        
        return "\n".join(parts)
    
    def get_faq_answer(self, question_key: str) -> Optional[str]:
        """Get FAQ answer by key."""
        data = self.load_brand_data()
        faq = data.get("faq_like_knowledge", {})
        return faq.get(question_key)
    
    def get_dealer_benefits(self) -> str:
        """Get formatted dealer benefits information."""
        data = self.load_brand_data()
        terms = data.get("commercial_terms", {})
        dealer_model = terms.get("dealer_model", {})
        
        benefits = dealer_model.get("dealer_benefits", [])
        
        if not benefits:
            return "Contact us to learn about dealer benefits."
        
        parts = ["**Dealer Benefits:**"]
        for benefit in benefits:
            parts.append(f"- {benefit}")
        
        parts.append(f"\n**Become a Retailer:** Visit {data.get('brand', {}).get('website', 'https://am-robots.com/')} to sign up")
        
        return "\n".join(parts)
    
    def answer_brand_query(self, query: str) -> str:
        """
        Answer a query about the brand/company.
        Analyzes the query and returns relevant information.
        """
        query_lower = query.lower()
        
        # About the company
        if any(word in query_lower for word in ["who", "about", "what is", "company", "am robots"]):
            return self.get_brand_description()
        
        # Vision/Mission
        if any(word in query_lower for word in ["vision", "mission", "values", "goal"]):
            return self.get_vision_mission()
        
        # Products/Categories
        if any(word in query_lower for word in ["categories", "what do you sell", "products", "product line"]):
            categories = self.get_product_categories()
            return f"**Product Categories:**\n" + "\n".join(f"- {cat}" for cat in categories)
        
        # Commercial terms
        if any(word in query_lower for word in ["shipping", "credit", "terms", "delivery", "payment"]):
            return self.get_commercial_terms()
        
        # Dealer/Retailer
        if any(word in query_lower for word in ["dealer", "retailer", "become", "partner", "benefits"]):
            return self.get_dealer_benefits()
        
        # Contact/Team
        if any(word in query_lower for word in ["contact", "team", "support", "email", "phone", "manager"]):
            return self.get_team_contact()
        
        # Default: return general info
        return self.get_brand_description()
