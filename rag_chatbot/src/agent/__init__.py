# Agent module - main agent and tools
from .tools import (
    search_products,
    get_product_details,
    get_brand_info,
    list_all_products,
    submit_support_request
)
from .support_agent import create_support_agent

__all__ = [
    "search_products",
    "get_product_details",
    "get_brand_info",
    "list_all_products",
    "submit_support_request",
    "create_support_agent"
]
