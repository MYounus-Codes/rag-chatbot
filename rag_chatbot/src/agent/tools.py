"""
Agent Tools - Function tools for the AM ROBOTS Support Agent.
These tools provide the agent with capabilities to search and retrieve information.
"""

from typing import Optional
from agents import function_tool

from ..services.product_service import ProductService
from ..services.brand_service import BrandService
from ..utils.language import detect_language, get_language_name
from ..core.constants import LOGIN_URL

# Initialize services (singleton pattern)
_product_service: Optional[ProductService] = None
_brand_service: Optional[BrandService] = None


def get_product_service() -> ProductService:
    """Get or create the product service instance."""
    global _product_service
    if _product_service is None:
        _product_service = ProductService()
    return _product_service


def get_brand_service() -> BrandService:
    """Get or create the brand service instance."""
    global _brand_service
    if _brand_service is None:
        _brand_service = BrandService()
    return _brand_service


@function_tool
def search_products(query: str) -> str:
    """
    Search for AM ROBOTS products matching the query.
    Use this tool when users ask about specific products, product features,
    or want to find products for specific use cases.
    
    Args:
        query: The search query describing what product or feature the user is looking for.
    
    Returns:
        Information about matching products from the AM ROBOTS catalog.
    """
    service = get_product_service()
    
    # Search for matching products
    results = service.search_products(query, limit=3)
    
    if not results:
        # Return list of available products
        all_products = service.get_all_product_names()
        if all_products:
            product_list = "\n".join(f"- {name}" for name in all_products[:15])
            return f"""I couldn't find a specific match for "{query}".

Here are our available products:
{product_list}

Please specify which product you'd like to know more about."""
        return f"No products found matching '{query}'. Please try a different search term."
    
    # Format results
    parts = [f"**Search Results for: {query}**\n"]
    
    for idx, product in enumerate(results, 1):
        info = service.get_product_info_formatted(product)
        parts.append(f"### Result {idx}")
        parts.append(info)
        parts.append("")
    
    return "\n".join(parts)


@function_tool
def get_product_details(product_name: str, info_type: str = "overview") -> str:
    """
    Get detailed information about a specific AM ROBOTS product.
    Use this tool when users ask for specifications, features, or details about a known product.
    
    Args:
        product_name: The name of the product (e.g., "STORM 2000", "Basic Cable Tracker", "AM Garage 1").
        info_type: Type of information needed - "overview", "specifications", "features", or "catalogue".
    
    Returns:
        Detailed product information from the AM ROBOTS database.
    """
    service = get_product_service()
    
    # Find the product
    product = service.get_product_by_name(product_name)
    
    if not product:
        return f"Product '{product_name}' not found. Use the search_products tool to find available products."
    
    # Get main info
    main_info = product.get("main_info", {})
    product_data = main_info.get("product", main_info)
    
    parts = []
    
    # Title
    title = product_data.get("title", product_name)
    parts.append(f"**{title}**\n")
    
    if info_type in ["overview", "features"]:
        # Short and long description
        short_desc = product_data.get("short_description", "")
        long_desc = product_data.get("long_description", "")
        
        if short_desc:
            parts.append(short_desc)
        if long_desc:
            parts.append(f"\n{long_desc}")
    
    if info_type in ["overview", "specifications"]:
        # Specifications
        specs = product_data.get("specs", {})
        if specs and isinstance(specs, dict):
            parts.append("\n**Specifications:**")
            for key, value in specs.items():
                if value and str(value) != "N/A":
                    key_formatted = key.replace("_", " ").title()
                    parts.append(f"- {key_formatted}: {value}")
        
        # Variants
        variants = product_data.get("variants", [])
        if variants:
            parts.append("\n**Available Variants:**")
            for v in variants:
                model = v.get("model_name", "Unknown")
                attrs = v.get("attributes", {})
                area = attrs.get("max_mowing_area_m2", "")
                if area:
                    parts.append(f"- {model}: up to {area} m²")
                else:
                    parts.append(f"- {model}")
    
    if info_type == "catalogue":
        # Get catalogue info
        catalogue_info = service.get_catalogue_info(product, "en")
        if catalogue_info:
            # Extract relevant portion (first 1500 chars)
            parts.append("\n**Catalogue Information:**")
            parts.append(catalogue_info[:1500])
    
    # Categories and tags
    categories = product_data.get("categories", [])
    tags = product_data.get("tags", [])
    
    if categories:
        parts.append(f"\n**Category:** {', '.join(categories)}")
    
    # SKU
    identifiers = product_data.get("identifiers", {})
    sku = identifiers.get("sku", "")
    if sku and sku != "N/A":
        parts.append(f"**SKU:** {sku}")
    
    # Brand
    brand = product_data.get("brand", "AM ROBOTS")
    parts.append(f"**Brand:** {brand}")
    
    return "\n".join(parts)


@function_tool
def get_brand_info(topic: str = "about") -> str:
    """
    Get information about AM ROBOTS company and brand.
    Use this tool when users ask about the company, dealer benefits, contact info, shipping, etc.
    
    Args:
        topic: The topic to get info about - "about", "contact", "shipping", "dealer", "vision", or "team".
    
    Returns:
        Information about AM ROBOTS company based on the requested topic.
    """
    service = get_brand_service()
    
    topic_lower = topic.lower()
    
    if topic_lower in ["about", "company", "who"]:
        return service.get_brand_description()
    
    elif topic_lower in ["contact", "team", "support"]:
        return service.get_team_contact()
    
    elif topic_lower in ["shipping", "delivery", "credit", "terms", "commercial"]:
        return service.get_commercial_terms()
    
    elif topic_lower in ["dealer", "retailer", "partner", "benefits"]:
        return service.get_dealer_benefits()
    
    elif topic_lower in ["vision", "mission", "values"]:
        return service.get_vision_mission()
    
    elif topic_lower in ["categories", "products", "sell"]:
        categories = service.get_product_categories()
        return "**AM ROBOTS Product Categories:**\n" + "\n".join(f"- {cat}" for cat in categories)
    
    else:
        # Default to about
        return service.get_brand_description()


@function_tool
def list_all_products() -> str:
    """
    List all available AM ROBOTS products.
    Use this tool when users ask what products are available or want to see the full catalog.
    
    Returns:
        A formatted list of all AM ROBOTS products organized by category.
    """
    service = get_product_service()
    
    products = service.load_all_products()
    
    if not products:
        return "No products found in the catalog."
    
    # Organize by category
    categorized = {}
    uncategorized = []
    
    for folder_name, product_data in products.items():
        main_info = product_data.get("main_info", {})
        if not main_info:
            continue
            
        product = main_info.get("product", main_info)
        title = product.get("title", folder_name)
        categories = product.get("categories", [])
        
        if categories:
            for cat in categories:
                if cat not in categorized:
                    categorized[cat] = []
                if title not in categorized[cat]:
                    categorized[cat].append(title)
        else:
            uncategorized.append(title)
    
    # Format output
    parts = ["**AM ROBOTS Product Catalog**\n"]
    
    for category, items in sorted(categorized.items()):
        parts.append(f"\n**{category}:**")
        for item in items:
            parts.append(f"- {item}")
    
    if uncategorized:
        parts.append("\n**Other Products:**")
        for item in uncategorized:
            parts.append(f"- {item}")
    
    parts.append(f"\n*For pricing information, please log in at: {LOGIN_URL}*")
    
    return "\n".join(parts)


@function_tool
def submit_support_request(issue_description: str, product_name: str = "", user_contact: str = "") -> str:
    """
    Prepare a support request for submission.
    Use this tool when users want to submit a support case or need help that requires human support.
    
    IMPORTANT: This tool requires user authentication. If user is not logged in, 
    prompt them to login first.
    
    Args:
        issue_description: Description of the issue or support request.
        product_name: Name of the product the issue relates to (if applicable).
        user_contact: User's contact information for follow-up.
    
    Returns:
        Confirmation and next steps for the support request OR login requirement message.
    """
    # Import chainlit here to avoid circular dependencies
    try:
        import chainlit as cl
        from deep_translator import GoogleTranslator
        
        # Check if user is authenticated
        is_authenticated = cl.user_session.get("is_authenticated", False)
        
        if not is_authenticated:
            return """**🔒 Login Required**

To submit a support case, you need to be logged in.

**Please choose one of the following:**

1. **[Login to your account](/)** - If you already have an account
2. **[Create a new account](/register)** - Quick and easy registration

**Why login?**
- We need your contact information to follow up on your case
- You can track the status of your support requests
- Secure and personalized support experience

Once logged in, I'll be happy to submit your support case!"""
        
        # User is authenticated - prepare support case
        username = cl.user_session.get("username", "User")
        email = cl.user_session.get("email", "")
        user_id = cl.user_session.get("user_id", "")
        detected_language = cl.user_session.get("detected_language", "en")
        
        # Translate issue to English if needed
        translated_issue = issue_description
        if detected_language != "en":
            try:
                translator = GoogleTranslator(source='auto', target='en')
                translated_issue = translator.translate(issue_description)
            except:
                translated_issue = issue_description
        
        # Store pending case data in session
        case_data = {
            "user_id": user_id,
            "original_case": issue_description,
            "translated_case": translated_issue,
            "product_name": product_name,
            "timestamp": str(cl.user_session.get("detected_language"))
        }
        cl.user_session.set("pending_support_case", case_data)
        
        parts = ["**✅ Support Request Ready for Submission**\n"]
        
        parts.append(f"I've prepared your support case with the following details:\n")
        
        parts.append("**📧 Contact Information (from your account):**")
        parts.append(f"- Name: {username}")
        if email:
            parts.append(f"- Email: {email}")
        else:
            parts.append(f"- User ID: {user_id}")
        
        if product_name:
            parts.append(f"\n**🛠️ Product:** {product_name}")
        
        parts.append(f"\n**📝 Issue Description:**")
        parts.append(f"_{issue_description}_")
        
        parts.append("\n**🔔 What happens next:**")
        parts.append("1. I'll submit your case to our support team")
        parts.append("2. You'll receive a unique tracking number")
        parts.append(f"3. Updates will be sent to **{email}**")
        parts.append("4. I'll monitor the status and notify you in this chat when resolved")
        parts.append("5. Average response time: 2-4 business hours")
        
        parts.append("\n**📞 Alternative Contact Methods:**")
        parts.append("- Email: info@am-robots.com")
        parts.append("- Phone: +45 8140 1221")
        
        parts.append("\n**Ready to submit?** Reply 'Yes' or 'Submit' to proceed, or let me know if you'd like to make any changes.")
        
        return "\n".join(parts)
        
    except Exception as e:
        # Fallback if Chainlit is not available (shouldn't happen in normal operation)
        print(f"Error checking authentication: {e}")
        return f"""**Support Request Prepared**

**Issue:** {issue_description}
{f'**Product:** {product_name}' if product_name else ''}

**Next Steps:**
To submit this case, please ensure you're logged in.
Our team will respond within 2-4 business hours.

**Contact Support:**
- Email: info@am-robots.com
- Phone: +45 8140 1221"""
        
        parts = ["**✅ Support Request Ready for Submission**\n"]
        
        parts.append(f"**Your Account:** {username}")
        if email:
            parts.append(f"**Email:** {email}")
        
        if product_name:
            parts.append(f"\n**Product:** {product_name}")
        
        parts.append(f"\n**Issue Description:**")
        parts.append(issue_description)
        
        parts.append("\n**📋 Your Case Details:**")
        parts.append(f"- Support will be sent to: {email}")
        parts.append(f"- Reference ID: {user_id}")
        
        parts.append("\n**What happens next:**")
        parts.append("1. Your case will be submitted to our support team")
        parts.append("2. You'll receive a tracking number")
        parts.append("3. Updates will be sent to your email")
        parts.append("4. Average response time: 2-4 business hours")
        
        parts.append("\n**Direct Contact Options:**")
        parts.append("- Email: info@am-robots.com")
        parts.append("- Phone: +45 8140 1221")
        parts.append("- Website: https://am-robots.com/")
        
        parts.append("\n**Would you like me to submit this case now?**")
        parts.append("Reply 'Yes' to confirm submission.")
        
        return "\n".join(parts)
        
    except Exception as e:
        # Fallback if Chainlit is not available (shouldn't happen in normal operation)
        print(f"Error checking authentication: {e}")
        return f"""**Support Request Prepared**

**Issue:** {issue_description}
{f'**Product:** {product_name}' if product_name else ''}

**Next Steps:**
To submit this case, please ensure you're logged in.
Our team will respond within 2-4 business hours.

**Contact Support:**
- Email: info@am-robots.com
- Phone: +45 8140 1221"""


@function_tool
def check_pricing_availability(product_name: str = "") -> str:
    """
    Check pricing information availability.
    Use this tool when users ask about prices, costs, or how much products cost.
    
    Args:
        product_name: The product name to check pricing for (optional).
    
    Returns:
        Instructions on how to access pricing information.
    """
    response = f"""**Pricing Information**

To view pricing for AM ROBOTS products, please log in to your dealer account:

**Login:** [{LOGIN_URL}]({LOGIN_URL})

**Not a dealer yet?**
Sign up on our website to become an AM ROBOTS retailer and access:
- Dealer pricing
- Personal account manager
- Free shipping on orders over €1,500 (EU, UK, Norway, Switzerland)
- 14-day credit terms (subject to approval)
- Price guarantee - we match competing offers

**Contact Sales:**
- Email: info@am-robots.com
- Phone: +45 8140 1221"""
    
    if product_name:
        response = f"**Product:** {product_name}\n\n" + response
    
    return response
