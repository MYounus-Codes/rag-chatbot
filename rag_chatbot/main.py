"""
Support RAG Chatbot with Dynamic Document Loading
==================================================
Enhanced with:
- Dynamic language detection
- Runtime document loading from product folders
- Multi-language support (English, French, German, Italian, Spanish, Danish)
- Intelligent product documentation retrieval
"""

import os
import json
import asyncio
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

import chainlit as cl
from dotenv import load_dotenv
from pinecone import Pinecone 
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException
from agents import Agent, Runner, function_tool
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from playwright.async_api import async_playwright

from config import (
    get_model, 
    validate_config,
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    SUPABASE_URL,
    SUPABASE_KEY,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM_EMAIL, 
    BASE_URL,
)

load_dotenv()
validate_config()

# ============================================================================
# Initialize Clients
# ============================================================================

pc = Pinecone(api_key=PINECONE_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Loading embedding model (all-mpnet-base-v2)...")
embedding_model = SentenceTransformer('all-mpnet-base-v2')
print("Embedding model loaded successfully!")

scheduler = AsyncIOScheduler()

# ============================================================================
# Product Documentation Paths
# ============================================================================

PRODUCTS_BASE_PATH = Path("products")

LANGUAGE_MAP = {
    "en": "English",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "es": "Spanish",
    "da": "Danish"
}

SUPPORTED_PRODUCTS = {
    "storm_2000": {
        "id": "storm-001",
        "path": PRODUCTS_BASE_PATH / "Storm 2000",
        "names": ["storm", "storm 2000", "storm2000", "storm-2000"],
        "area_m2": 2000
    },
    "storm_4000": {
        "id": "storm-002",
        "path": PRODUCTS_BASE_PATH / "Storm 4000",
        "names": ["storm 4000", "storm4000", "storm-4000"],
        "area_m2": 4000
    },
    "storm_6000": {
        "id": "storm-003",
        "path": PRODUCTS_BASE_PATH / "storm_6000",
        "names": ["storm 6000", "storm6000", "storm-6000"],
        "area_m2": 6000
    }
}



# ============================================================================
# Language Detection
# ============================================================================

def detect_language(text: str) -> str:
    """
    Detect the language of the input text.
    Returns ISO 639-1 code (en, fr, de, it, es, da)
    """
    try:
        lang = detect(text)
        # Map detected language to supported languages
        if lang in LANGUAGE_MAP:
            return lang
        return "en"  # Default to English
    except LangDetectException:
        return "en"


def get_language_name(lang_code: str) -> str:
    """Get full language name from code."""
    return LANGUAGE_MAP.get(lang_code, "English")


# ============================================================================
# Dynamic Document Loading
# ============================================================================

def identify_product(query: str) -> Optional[Dict]:
    """
    Identify which product the user is asking about.
    Returns product info dict or None.
    """
    query_lower = query.lower()

    # First check the predefined SUPPORTED_PRODUCTS (STORM models)
    for product_key, product_info in SUPPORTED_PRODUCTS.items():
        for name in product_info["names"]:
            if name in query_lower:
                return {
                    "key": product_key,
                    **product_info
                }

    # If not found there, try to discover products dynamically from the products folder
    try:
        if PRODUCTS_BASE_PATH.exists() and PRODUCTS_BASE_PATH.is_dir():
            for child in PRODUCTS_BASE_PATH.iterdir():
                if not child.is_dir():
                    continue
                folder_name = child.name.lower()

                # match by folder name tokens
                if folder_name in query_lower or any(tok in query_lower for tok in folder_name.replace(',', ' ').split()):
                    return {
                        "key": folder_name.replace(' ', '_'),
                        "id": folder_name,
                        "path": child,
                        "names": [child.name]
                    }

                # try to load main product json and match title or product name inside
                main_json = load_product_json(child)
                if main_json:
                    # try common locations for title
                    title = None
                    if isinstance(main_json, dict):
                        title = main_json.get('title') or main_json.get('name') or main_json.get('product', {}).get('title')
                    if title and title.lower() in query_lower:
                        return {
                            "key": folder_name.replace(' ', '_'),
                            "id": folder_name,
                            "path": child,
                            "names": [child.name, title]
                        }
    except Exception:
        pass

    # Default fallback: if the query mentions 'storm' but no specific model
    if "storm" in query_lower:
        return {
            "key": "storm_2000",
            **SUPPORTED_PRODUCTS["storm_2000"]
        }

    return None


def load_product_json(product_path: Path) -> Optional[Dict]:
    """
    Load the main product JSON file (e.g., storm2000.json).
    """
    try:
        # Look for JSON file in the product folder
        json_files = list(product_path.glob("*.json"))
        if json_files:
            with open(json_files[0], 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"Error loading product JSON: {e}")
        return None


def load_manual(product_path: Path, language: str) -> Optional[Dict]:
    """
    Load manual JSON for specific language.
    """
    try:
        manual_path = product_path / "manuals" / f"Manual_{get_language_name(language)}.json"
        if manual_path.exists():
            with open(manual_path, 'r', encoding='utf-8') as f:
                return {"data": json.load(f), "lang": get_language_name(language)}
        # Fallback to English
        manual_path = product_path / "manuals" / "Manual_English.json"
        if manual_path.exists():
            with open(manual_path, 'r', encoding='utf-8') as f:
                return {"data": json.load(f), "lang": "English"}
        return None
    except Exception as e:
        print(f"Error loading manual: {e}")
        return None


def load_catalogue(product_path: Path, language: str) -> Optional[Dict]:
    """
    Load catalogue JSON for specific language.
    """
    try:
        catalogue_path = product_path / "catalogues" / f"Catalogue_{get_language_name(language)}.json"
        if catalogue_path.exists():
            with open(catalogue_path, 'r', encoding='utf-8') as f:
                return {"data": json.load(f), "lang": get_language_name(language)}
        # Fallback to English
        catalogue_path = product_path / "catalogues" / "Catalogue_English.json"
        if catalogue_path.exists():
            with open(catalogue_path, 'r', encoding='utf-8') as f:
                return {"data": json.load(f), "lang": "English"}
        return None
    except Exception as e:
        print(f"Error loading catalogue: {e}")
        return None


def extract_relevant_info(data: Dict, query: str, doc_type: str) -> str:
    """
    Extract relevant information from loaded document based on query.
    """
    query_lower = query.lower()
    result_parts = []
    
    if doc_type == "product":
        # Extract product overview
        product = data.get("product", {})
        result_parts.append(f"**{product.get('title', 'Product')}**")
        result_parts.append(product.get('long_description', ''))
        
        # Specs
        specs = product.get('specs', {})
        if specs:
            result_parts.append("\n**Specifications:**")
            for key, value in specs.items():
                result_parts.append(f"• {key.replace('_', ' ').title()}: {value}")
        
        # Variants
        variants = product.get('variants', [])
        if variants:
            result_parts.append("\n**Available Models:**")
            for v in variants:
                result_parts.append(f"• {v.get('model_name')}: {v.get('attributes', {}).get('max_mowing_area_m2', 'N/A')} m²")
    
    elif doc_type == "manual":
        # Search through manual pages
        documents = data.get("documents", [])
        for doc in documents:
            pages = doc.get("pages", [])
            for page in pages:
                page_text = page.get("text", "")
                heading = page.get("heading", "")
                
                # Check if page is relevant to query
                if any(keyword in page_text.lower() or keyword in heading.lower() 
                       for keyword in ["setup", "install", "troubleshoot", "maintenance", "map", "app"]
                       if keyword in query_lower):
                    result_parts.append(f"\n**{heading}**")
                    result_parts.append(page_text[:500])
                    
                    if len(result_parts) > 5:  # Limit to 5 sections
                        break
            if len(result_parts) > 5:
                break
    
    elif doc_type == "catalogue":
        # Search through catalogue
        documents = data.get("documents", [])
        for doc in documents:
            pages = doc.get("pages", [])
            for page in pages:
                page_text = page.get("text", "")
                heading = page.get("heading", "")
                
                # Check relevance
                if any(keyword in page_text.lower() or keyword in heading.lower() 
                       for keyword in ["garage", "cable", "blade", "accessory", "kit"]
                       if keyword in query_lower):
                    result_parts.append(f"\n**{heading}**")
                    result_parts.append(page_text[:400])
                    
                    if len(result_parts) > 4:
                        break
            if len(result_parts) > 4:
                break
    
    return "\n".join(result_parts) if result_parts else "No specific information found."


# ============================================================================
# Database Operations (unchanged)
# ============================================================================

def get_user_by_id(user_id: str) -> Optional[dict]:
    result = supabase.table("users").select("*").eq("user_id", user_id).execute()
    return result.data[0] if result.data else None


def save_support_case(user_id: str, original_case: str, translated_case: str, task_number: str) -> dict:
    data = {
        "user_id": user_id,
        "original_case": original_case,
        "translated_case": translated_case,
        "task_number": task_number,
        "status": "open",
        "created_at": datetime.utcnow().isoformat(),
    }
    result = supabase.table("support_cases").insert(data).execute()
    return result.data[0] if result.data else data


def update_case_status(task_number: str, status: str, response: str = None) -> None:
    data = {"status": status, "updated_at": datetime.utcnow().isoformat()}
    if response:
        data["support_response"] = response
    supabase.table("support_cases").update(data).eq("task_number", task_number).execute()


def get_pending_cases() -> list:
    result = supabase.table("support_cases").select("*, users(email, username)").eq("status", "open").execute()
    return result.data or []


# ============================================================================
# Embedding & RAG (kept for backward compatibility)
# ============================================================================

def get_embedding(text: str) -> list:
    embedding = embedding_model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


# ============================================================================
# Translation Function
# ============================================================================

def translate_to_english(text: str) -> str:
    try:
        translator = GoogleTranslator(source='auto', target='en')
        translated = translator.translate(text)
        return translated if translated else text
    except Exception as e:
        print(f"Translation error: {e}")
        return text


def translate_to_language(text: str, target_lang: str) -> str:
    """Translate text to target language."""
    try:
        if target_lang == "en":
            return text
        translator = GoogleTranslator(source='auto', target=target_lang)
        translated = translator.translate(text)
        return translated if translated else text
    except Exception as e:
        print(f"Translation error: {e}")
        return text


# ============================================================================
# Browser Automation (unchanged)
# ============================================================================

async def human_delay(min_ms: int = 500, max_ms: int = 1500) -> None:
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def human_type(page, selector: str, text: str) -> None:
    element = await page.wait_for_selector(selector, timeout=10000)
    await element.click()
    await human_delay(200, 400)
    
    for char in text:
        await page.keyboard.type(char, delay=random.uniform(50, 150))
        if random.random() < 0.1:
            await human_delay(100, 300)


async def submit_support_case_to_website(user_id: str, issue_description: str) -> Optional[str]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        
        page = await context.new_page()
        
        try:
            await page.goto(BASE_URL, wait_until="networkidle")
            await human_delay(1000, 2000)
            
            await human_type(page, 'input[placeholder*="user ID"]', user_id)
            await human_delay(300, 600)
            
            await human_type(page, 'textarea[placeholder*="describe"]', issue_description)
            await human_delay(500, 1000)
            
            submit_button = await page.wait_for_selector('button[type="submit"], button:has-text("Submit")')
            await submit_button.click()
            await human_delay(2000, 3000)
            
            await page.wait_for_selector('text=Successfully', timeout=15000)
            
            import re
            page_content = await page.content()
            match = re.search(r'SUP-[A-Z0-9]+', page_content)
            if match:
                return match.group(0)
                
        except Exception as e:
            print(f"Error submitting support case: {e}")
            return None
        finally:
            await browser.close()
    
    return None


async def check_case_status(task_number: str) -> tuple[str, Optional[str]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        
        try:
            await page.goto(f"{BASE_URL}/status?taskNumber={task_number}", wait_until="networkidle")
            await human_delay(1000, 2000)
            
            search_button = await page.query_selector('button:has-text("Search")')
            if search_button:
                await search_button.click()
                await human_delay(2000, 3000)
            
            status_element = await page.query_selector('[class*="status"], h2:has-text("Open"), h2:has-text("Resolved")')
            if status_element:
                status_text = await status_element.text_content()
                
                if "Resolved" in status_text:
                    response_element = await page.query_selector('[class*="response"], div:has-text("Support Team Response")')
                    response_text = await response_element.text_content() if response_element else None
                    return "resolved", response_text
                else:
                    return "open", None
                    
        except Exception as e:
            print(f"Error checking status: {e}")
        finally:
            await browser.close()
    
    return "unknown", None


async def send_reminder(task_number: str) -> bool:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(f"{BASE_URL}/reminder", wait_until="networkidle")
            await human_delay(1000, 2000)
            
            await human_type(page, 'input[placeholder*="task"], input[type="text"]', task_number)
            await human_delay(500, 1000)
            
            send_button = await page.wait_for_selector('button:has-text("Send Reminder"), button[type="submit"]')
            await send_button.click()
            await human_delay(2000, 3000)
            
            return True
        except Exception as e:
            print(f"Error sending reminder: {e}")
            return False
        finally:
            await browser.close()


# ============================================================================
# Email Functions (unchanged)
# ============================================================================

def send_email(to_email: str, subject: str, body: str) -> bool:
    try: 
        msg = MIMEMultipart()
        msg["From"] = SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_resolution_email(user_email: str, username: str, task_number: str, response: str) -> bool:
    subject = f"Your Support Case {task_number} Has Been Resolved"
    body = f"""
    <html><body style="font-family: Arial, sans-serif;">
        <h2 style="color: #2563eb;">Support Case Resolved</h2>
        <p>Dear {username},</p>
        <p>Your support case <strong>{task_number}</strong> has been resolved.</p>
        <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px;">
            <h3 style="color: #059669;">Support Team Response:</h3>
            <p>{response}</p>
        </div>
        <p>Best regards,<br>AM ROBOTS Support Team</p>
    </body></html>
    """
    return send_email(user_email, subject, body)


# ============================================================================
# Scheduler Tasks (unchanged)
# ============================================================================

async def check_pending_cases():
    print(f"[{datetime.now()}] Checking pending support cases...")
    
    pending_cases = get_pending_cases()
    
    for case in pending_cases:
        task_number = case["task_number"]
        created_at = datetime.fromisoformat(case["created_at"].replace("Z", "+00:00"))
        hours_since_created = (datetime.utcnow() - created_at.replace(tzinfo=None)).total_seconds() / 3600
        
        status, response = await check_case_status(task_number)
        
        if status == "resolved" and response:
            update_case_status(task_number, "resolved", response)
            user_data = case.get("users", {})
            if user_data:
                send_resolution_email(
                    user_email=user_data.get("email"),
                    username=user_data.get("username"),
                    task_number=task_number,
                    response=response
                )
            print(f"Case {task_number} resolved and user notified.")
            
        elif status == "open" and hours_since_created >= 24:
            await send_reminder(task_number)
            print(f"Reminder sent for case {task_number}")


# ============================================================================
# Enhanced Agent Tools with Dynamic Document Loading
# ============================================================================

@function_tool
def search_product_documentation(user_query: str, detected_language: str = "en") -> str:
    """
    Search and retrieve product documentation dynamically based on user query.
    Automatically detects product, document type, and loads appropriate files.
    
    Args:
        user_query: The user's question or issue description
        detected_language: ISO language code (en, fr, de, it, es, da)
    
    Returns:
        Relevant documentation in the user's language
    """
    # Detect language if not provided
    if not detected_language or detected_language == "en":
        detected_language = detect_language(user_query)
    
    language_name = get_language_name(detected_language)
    
    # Identify product
    product = identify_product(user_query)
    
    if not product:
        # Build a dynamic list of available product folders
        available = []
        try:
            if PRODUCTS_BASE_PATH.exists():
                for child in PRODUCTS_BASE_PATH.iterdir():
                    if child.is_dir():
                        available.append(child.name)
        except Exception:
            pass

        avail_text = "\n".join(f"• {name}" for name in available) if available else "• STORM 2000\n• STORM 4000\n• STORM 6000"

        return f"""❌ **Product Not Identified**

I couldn't determine which product you're asking about.

**Available Products:**
{avail_text}

Please specify which product (use the full product name if possible)."""
    
    product_path = product["path"]
    query_lower = user_query.lower()
    
    result = f"🤖 **Product Documentation** ({language_name})\n\n"
    result += f"📦 **Product:** {product['key'].upper().replace('_', ' ')}\n\n"
    
    # Determine document type needed
    is_catalogue_query = any(word in query_lower for word in ["garage", "cable", "blade", "accessory", "kit", "catalogue", "catalog", "parts"])
    is_manual_query = any(word in query_lower for word in ["manual", "setup", "install", "troubleshoot", "maintain", "map", "app", "guide", "how to"])
    
    sections_added = 0
    
    # Always load product info (specs, overview) and include metadata
    product_data = load_product_json(product_path)
    if product_data:
        info = extract_relevant_info(product_data, user_query, "product")
        result += f"### Product Overview\n{info}\n\n"
        sections_added += 1
    
    # Load manual if query relates to usage/setup
    if is_manual_query or sections_added == 0:
        manual_result = load_manual(product_path, detected_language)
        if manual_result:
            manual_data = manual_result.get('data')
            manual_lang = manual_result.get('lang', 'English')
            info = extract_relevant_info(manual_data, user_query, "manual")
            # If loaded manual language differs from user language, translate the extracted info
            if manual_lang.lower() != get_language_name(detected_language).lower():
                info = translate_to_language(info, detected_language)
                result += f"### User Manual Information (translated from {manual_lang})\n{info}\n\n"
            else:
                result += f"### User Manual Information\n{info}\n\n"
            sections_added += 1
    
    # Load catalogue if query relates to accessories
    if is_catalogue_query:
        catalogue_result = load_catalogue(product_path, detected_language)
        if catalogue_result:
            catalogue_data = catalogue_result.get('data')
            catalogue_lang = catalogue_result.get('lang', 'English')
            info = extract_relevant_info(catalogue_data, user_query, "catalogue")
            if catalogue_lang.lower() != get_language_name(detected_language).lower():
                info = translate_to_language(info, detected_language)
                result += f"### Catalogue & Accessories (translated from {catalogue_lang})\n{info}\n\n"
            else:
                result += f"### Catalogue & Accessories\n{info}\n\n"
            sections_added += 1
    
    if sections_added == 0:
        result += "⚠️ No specific documentation found for your query. Please rephrase or ask about:\n"
        result += "• Product specifications\n• Installation and setup\n• Troubleshooting\n• Accessories and parts\n"
    else:
        result += "\n💡 **What to do next:**\n"
        result += "• If this answers your question, great!\n"
        result += "• Need more details? Ask a follow-up question\n"
        result += "• Still need help? I can submit a support case\n"
    
    return result


@function_tool
def translate_to_english_tool(text: str) -> str:
    """
    Translate text to English for support case submission.
    
    Args:
        text: The text to translate
    
    Returns:
        Translation result
    """
    translated = translate_to_english(text)
    
    result = f"🌐 **Translation Complete**\n\n"
    result += f"**Original:** {text}\n\n"
    result += f"**English:** {translated}\n\n"
    
    if text.lower() != translated.lower():
        result += "**NEXT STEP:** Show user both versions and ask for confirmation to submit."
    else:
        result += "**NEXT STEP:** Text is already in English. Ask for confirmation to submit."
    
    return result


@function_tool  
async def submit_support_case(user_id: str, translated_case: str, original_case: str) -> str:
    """
    Submit support case to AM ROBOTS support system.
    ⚠️ ONLY use AFTER user explicitly confirms submission.
    
    Args:
        user_id: User's unique identifier
        translated_case: Support case in English
        original_case: Original user description
    
    Returns:
        Tracking number or error message
    """
    task_number = await submit_support_case_to_website(user_id, translated_case)
    
    if task_number:
        save_support_case(user_id, original_case, translated_case, task_number)
        
        result = f"✅ **CASE SUBMITTED SUCCESSFULLY**\n\n"
        result += f"📋 **Tracking Number:** `{task_number}`\n\n"
        result += f"**What happens next:**\n"
        result += f"1. Our support team will review your case\n"
        result += f"2. You'll receive email updates\n"
        result += f"3. Automatic status checks every 5 minutes\n"
        result += f"4. Average response time: 2-4 hours\n\n"
        result += f"**Need help with another issue?** Just ask!"
        
        return result
    else:
        result = "❌ **SUBMISSION FAILED**\n\n"
        result += "Error submitting to support system.\n"
        result += "**Please try again or contact support directly.**"
        return result


from recursive_product_reader import read_all_product_files

@function_tool
def answer_from_all_product_files(user_query: str) -> str:
    """
    Search and answer using information from all files in the products folder.
    Args:
        user_query: The user's question
    Returns:
        Relevant answer from any product file
    """
    all_files = read_all_product_files()
    user_query_lower = user_query.lower()
    relevant_answers = []
    for path, content in all_files.items():
        try:
            if not content:
                continue

            # Try to detect JSON content and parse it for structured product info
            if isinstance(content, str) and content.strip().startswith('{'):
                try:
                    parsed = json.loads(content)
                except Exception:
                    parsed = None

                if isinstance(parsed, dict):
                    # If this looks like a main product JSON, extract key fields
                    product_section = parsed.get('product') or parsed
                    title = product_section.get('title') or product_section.get('name')
                    specs = product_section.get('specs') if isinstance(product_section.get('specs'), dict) else {}
                    variants = product_section.get('variants') or []

                    combined_text = ' '.join([str(title or ''), ' '.join(list(specs.keys())), ' '.join([v.get('model_name','') for v in variants])])
                    if user_query_lower in combined_text.lower() or user_query_lower in (title or '').lower():
                        entry = f"**Product File:** {path}\n"
                        if title:
                            entry += f"**Full Name:** {title}\n"
                        if specs:
                            entry += "Specifications:\n"
                            for k, v in specs.items():
                                entry += f" - {k}: {v}\n"
                        if variants:
                            entry += f"Variants ({len(variants)}):\n"
                            for v in variants:
                                entry += f" - {v.get('model_name', 'Unnamed')}\n"
                        relevant_answers.append(entry)
                        continue

            # Fallback: plain text search inside file content
            if isinstance(content, str) and user_query_lower in content.lower():
                snippet = content[:500].replace('\n', ' ')
                relevant_answers.append(f"**File:** {path}\n{snippet}")
        except Exception:
            continue

    if relevant_answers:
        return "\n---\n".join(relevant_answers)
    return "No relevant information found in any product file."


# ============================================================================
# Create Enhanced Support Agent
# ============================================================================

support_agent = Agent(
    name="AM ROBOTS Support Assistant",
    instructions="""You are an intelligent multilingual support assistant for AM ROBOTS, specializing in STORM robot mowers.

🎯 **YOUR ENHANCED CAPABILITIES:**
• **Dynamic Document Loading**: Access product manuals, catalogues, and specs in real-time
• **Multi-language Support**: Automatically detect and respond in user's language (English, French, German, Italian, Spanish, Danish)
• **Intelligent Product Recognition**: Identify which STORM model user needs help with
• **Context-Aware Responses**: Provide relevant information from manuals, catalogues, or specifications

🌍 **LANGUAGE HANDLING (CRITICAL):**
1. **ALWAYS detect the user's language** from their message
2. **Respond in the SAME language** the user is using
3. When loading documentation, use the detected language code
4. Pass the detected language code to `search_product_documentation`
5. If documentation isn't available in user's language, mention you're providing English version

Language codes: en=English, fr=French, de=German, it=Italian, es=Spanish, da=Danish

📋 **STEP-BY-STEP WORKFLOW:**

**STEP 1: DETECT LANGUAGE & UNDERSTAND**
• Detect user's language from their message
• Greet warmly in their language
• Understand their issue - which product (STORM 2000/4000/6000)?
• What type of help needed? (specs, setup, troubleshooting, accessories)

**STEP 2: SEARCH DOCUMENTATION DYNAMICALLY**
• Use `search_product_documentation(user_query, detected_language)`
• The tool will:
  - Identify the STORM model
  - Determine if they need manual, catalogue, or specs
  - Load the appropriate files in their language
  - Extract relevant sections

**STEP 3: PROVIDE ANSWER IN USER'S LANGUAGE**
• Present the information clearly
• Use the documentation retrieved
• Format nicely with headers and bullet points
• If documentation is in English but user speaks another language, translate key points

**STEP 4: DETERMINE NEXT ACTION**
Can the issue be resolved with documentation?
  ✅ YES → Help them solve it, offer follow-up questions
  ❌ NO → Prepare for support case submission

**STEP 5: SUBMISSION (if needed)**
• Summarize issue clearly
• Use `translate_to_english_tool` for non-English text
• Ask: "Would you like me to submit this support case? (Yes/No)"
• Wait for explicit confirmation
• Use `submit_support_case` only after "Yes"

🎨 **COMMUNICATION STYLE:**
• **Match the user's language** - this is CRITICAL
• Be friendly, professional, empathetic
• Use emojis occasionally for engagement
• Break down technical info into simple steps
• Acknowledge frustration if present
• Celebrate successful resolutions

📚 **DOCUMENT TYPES YOU CAN ACCESS:**
• **Product Specs**: Overview, dimensions, cutting specifications
• **User Manuals**: Setup, app usage, mapping, troubleshooting
• **Catalogues**: Garages, cables, blades, accessories, kits

⚠️ **CRITICAL RULES:**
1. **ALWAYS respond in user's detected language**
2. **NEVER submit without explicit confirmation**
3. **ALWAYS search documentation first**
4. **Quote relevant sections** from loaded documents
5. **Be transparent** about what you found
6. **If documentation not available**, clearly state it

🔍 **WHEN TO USE EACH TOOL:**
• `search_product_documentation` → PRIMARY tool, always use first with detected language
• `translate_to_english_tool` → When preparing non-English case for submission
• `submit_support_case` → LAST, only after user confirms "Yes"

💡 **EXAMPLE FLOWS:**

**English User:**
User: "My STORM 4000 won't map properly"
You: Detect language=en, call search_product_documentation("STORM 4000 mapping issues", "en")
→ Get mapping instructions from Manual_English.json
You: Provide troubleshooting steps in English

**French User:**
User: "Mon STORM 2000 ne charge pas"
You: Detect language=fr, call search_product_documentation("STORM 2000 charging issues", "fr")
→ Get charging info from Manual_French.json
You: Répondre en français avec les instructions

**German User asking about accessories:**
User: "Welche Garage passt für STORM 6000?"
You: Detect language=de, call search_product_documentation("STORM 6000 garage accessories", "de")
→ Get garage info from Catalogue_German.json
You: Antworten auf Deutsch mit Garage-Optionen

Remember: Your superpower is **dynamic multilingual document access**. Use it wisely!""",
    tools=[search_product_documentation, translate_to_english_tool, submit_support_case, answer_from_all_product_files],
    model=get_model(),
)


# ============================================================================
# Chainlit Authentication
# ============================================================================

@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """Authenticate user with Supabase."""
    try:
        result = supabase.table("users").select("*").eq("username", username).execute()
        
        if result.data:
            user = result.data[0]
            import bcrypt
            if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                return cl.User(
                    identifier=user["user_id"],
                    metadata={
                        "username": user["username"],
                        "email": user["email"],
                        "provider": "credentials"
                    }
                )
        return None
    except Exception as e:
        print(f"Auth error: {e}")
        return None


# ============================================================================
# Chainlit Lifecycle Hooks
# ============================================================================

scheduler_started = False

@cl.on_chat_start
async def on_chat_start():
    """Initialize chat session with the agent."""
    global scheduler_started
    
    if not scheduler_started:
        start_scheduler()
        scheduler_started = True
    
    user = cl.user_session.get("user")
    user_id = user.identifier
    username = user.metadata.get("username", "User")
    email = user.metadata.get("email", "")
    
    cl.user_session.set("user_id", user_id)
    cl.user_session.set("username", username)
    cl.user_session.set("email", email)
    cl.user_session.set("chat_history", [])
    
    initial_message = f"""👋 **Welcome to AM ROBOTS Support, {username}!**

I'm your AI support assistant with access to complete product documentation in multiple languages.

**🌍 Supported Languages:**
• English • Français • Deutsch • Italiano • Español • Dansk

**🤖 STORM Robot Mowers:**
• **STORM 2000** - Up to 2000 m²
• **STORM 4000** - Up to 4000 m²
• **STORM 6000** - Up to 6000 m²

**💡 I can help you with:**
✅ Product specifications and features
✅ Installation and setup guides
✅ App configuration and mapping
✅ Troubleshooting and maintenance
✅ Accessories (garages, cables, blades)
✅ Submit and track support cases

**📝 To get started:**
Simply describe your issue in **any supported language**. Include:
• Which STORM model you have
• What problem you're experiencing
• Any error messages you see

**Example questions:**
• "My STORM 4000 won't connect to the app"
• "Comment installer le STORM 2000?" (French)
• "Welche Garage brauche ich für STORM 6000?" (German)"""

    await cl.Message(content=initial_message).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages using the Support Agent with language detection."""
    user_id = cl.user_session.get("user_id")
    username = cl.user_session.get("username")
    chat_history = cl.user_session.get("chat_history", [])
    
    # Detect user's language
    detected_lang = detect_language(message.content)
    language_name = get_language_name(detected_lang)
    
    # Store detected language in session
    cl.user_session.set("detected_language", detected_lang)
    
    # Build enhanced context for agent
    user_message = f"[User ID: {user_id}, Username: {username}, Language: {detected_lang}]\n{message.content}"
    
    # Add to chat history
    chat_history.append({"role": "user", "content": user_message})
    
    # Show thinking indicator with language info
    thinking_msg = cl.Message(content=f"🔍 Searching documentation ({language_name})...")
    await thinking_msg.send()
    
    try:
        # Run the agent with context
        result = await Runner.run(
            support_agent,
            input=chat_history,
        )
        
        # Get agent's response
        agent_response = result.final_output
        
        # Update thinking message with actual response
        thinking_msg.content = agent_response
        await thinking_msg.update()
        
        # Add to history
        chat_history.append({"role": "assistant", "content": agent_response})
        cl.user_session.set("chat_history", chat_history)
        
    except Exception as e:
        print(f"Agent error: {e}")
        
        # Error messages in detected language
        error_messages = {
            "en": f"❌ **Sorry, I encountered an error:** {str(e)}\n\nPlease try again or rephrase your question.",
            "fr": f"❌ **Désolé, j'ai rencontré une erreur:** {str(e)}\n\nVeuillez réessayer ou reformuler votre question.",
            "de": f"❌ **Entschuldigung, es ist ein Fehler aufgetreten:** {str(e)}\n\nBitte versuchen Sie es erneut.",
            "it": f"❌ **Scusa, ho riscontrato un errore:** {str(e)}\n\nRiprova o riformula la tua domanda.",
            "es": f"❌ **Lo siento, encontré un error:** {str(e)}\n\nIntenta de nuevo o reformula tu pregunta.",
            "da": f"❌ **Beklager, jeg stødte på en fejl:** {str(e)}\n\nPrøv igen eller omformulér dit spørgsmål."
        }
        
        error_msg = error_messages.get(detected_lang, error_messages["en"])
        thinking_msg.content = error_msg
        await thinking_msg.update()


@cl.on_chat_end
async def on_chat_end():
    """Handle chat end."""
    pass


# ============================================================================
# Application Startup
# ============================================================================

def start_scheduler():
    """Initialize and start the background scheduler."""
    if not scheduler.running:
        scheduler.add_job(
            check_pending_cases,
            "interval",
            minutes=5,
            id="check_pending_cases",
            replace_existing=True
        )
        scheduler.start()
        print("✅ Scheduler started - checking cases every 5 minutes")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("🚀 AM ROBOTS Support Chatbot Ready!")
    print(f"📊 Products folder: {PRODUCTS_BASE_PATH}")
    print(f"🔐 Supabase authentication enabled")
    print(f"🤖 Using model: {get_model()}")
    print(f"🌍 Supported languages: {', '.join(LANGUAGE_MAP.values())}")
    print("\n📁 Available products:")
    for product_key, info in SUPPORTED_PRODUCTS.items():
        print(f"   • {product_key}: {info['path']}")
    print("\n✨ Dynamic document loading enabled!")
    print("=" * 60)
