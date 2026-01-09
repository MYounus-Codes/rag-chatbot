"""
AM ROBOTS Support Chatbot entrypoint with Chainlit's built-in authentication.
"""

import os
import bcrypt
import asyncio
import logging
from datetime import datetime

import chainlit as cl
from dotenv import load_dotenv
from supabase import Client, create_client
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from agents import Runner
from src.agent.support_agent import create_support_agent
from src.core.config import Config
from src.core.constants import BRAND_NAME
from src.services.brand_service import BrandService
from src.services.product_service import ProductService
from src.services.support_case_service import SupportCaseService
from src.utils.guardrails import InputGuardrail, OutputGuardrail
from src.utils.language import detect_language

load_dotenv()

Config.validate()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in the environment.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize services and agent
product_service = ProductService(Config.PRODUCTS_BASE_PATH)
brand_service = BrandService()
support_agent = create_support_agent()
support_case_service = SupportCaseService(supabase)

# Validate SMTP credentials
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
    logger.error("❌ SMTP credentials missing in .env file!")
    logger.error(f"SMTP_HOST: {'✓' if SMTP_HOST else '✗'}")
    logger.error(f"SMTP_USER: {'✓' if SMTP_USER else '✗'}")
    logger.error(f"SMTP_PASSWORD: {'✓' if SMTP_PASSWORD else '✗'}")
else:
    logger.info(f"✅ SMTP credentials loaded - Server: {SMTP_HOST}, User: {SMTP_USER}")

# Track active monitoring tasks per session
active_monitoring_tasks = {}


async def monitor_case_for_session(session_id: str, task_number: str, user_email: str, username: str):
    """Monitor a specific support case for the current session until resolved.
    
    Args:
        session_id: Unique session identifier
        task_number: Support case tracking number
        user_email: User's email address
        username: User's display name
    """
    logger.info(f"🔍 Starting case monitoring for session {session_id}: {task_number}")
    check_count = 0
    max_checks = 288  # Stop after 24 hours (288 * 5 min)
    
    try:
        while check_count < max_checks:
            check_count += 1
            await asyncio.sleep(300)  # Wait 5 minutes between checks
            
            logger.info(f"\n📋 [Check #{check_count}] Monitoring case {task_number} for session {session_id}")
            
            # Check case status
            status, response = await support_case_service.check_case_status(task_number)
            logger.info(f"   Status: {status}")
            
            if status == "resolved" and response:
                logger.info(f"✅ Case {task_number} is RESOLVED!")
                
                # Update database
                support_case_service.update_case_status(task_number, "resolved", response)
                logger.info(f"   ✓ Database updated")
                
                # Format beautiful response
                clean_response = support_case_service.format_resolution_response(response)
                
                # Send in-app notification if session is still active
                try:
                    resolution_message = (
                        f"✅ **YOUR SUPPORT CASE HAS BEEN RESOLVED!**\n\n"
                        f"📋 **Tracking Number:** `{task_number}`\n\n"
                        f"**Support Team Response:**\n\n"
                        f"{clean_response}\n\n"
                        f"---\n"
                        f"If you have any further questions, feel free to ask!"
                    )
                    await cl.Message(content=resolution_message).send()
                    logger.info(f"   ✓ In-app notification sent")
                except Exception as e:
                    logger.warning(f"   ⚠️ Could not send in-app notification (session may be closed): {e}")
                
                # Send email notification
                logger.info(f"   📧 Sending email to {user_email}...")
                email_sent = support_case_service.send_resolution_email(
                    user_email=user_email,
                    username=username,
                    task_number=task_number,
                    response=clean_response
                )
                if email_sent:
                    logger.info(f"   ✅ Email sent successfully")
                else:
                    logger.error(f"   ❌ Failed to send email")
                
                # Stop monitoring - case is resolved
                logger.info(f"🎉 Monitoring complete for case {task_number}")
                break
            
            elif status == "open":
                logger.info(f"   ⏳ Case still open, will check again in 5 minutes...")
            
            else:
                logger.warning(f"   ⚠️ Unknown status: {status}")
    
    except asyncio.CancelledError:
        logger.info(f"🛑 Monitoring cancelled for case {task_number} (session ended)")
    except Exception as e:
        logger.error(f"❌ Error monitoring case {task_number}: {e}", exc_info=True)
    finally:
        # Clean up tracking
        if session_id in active_monitoring_tasks:
            del active_monitoring_tasks[session_id]
            logger.info(f"🧹 Cleaned up monitoring task for session {session_id}")


# ============================================================================
# Chainlit Password Authentication Callback
# ============================================================================

@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """
    Authenticate user against Supabase database.
    This is Chainlit's built-in password authentication.
    Users will see the default /login page and be redirected there if not authenticated.
    """
    try:
        # Check if identifier is email or username
        lookup_field = 'email' if '@' in username else 'username'
        lookup_value = username.lower() if lookup_field == 'email' else username

        result = supabase.table("users").select("*").eq(lookup_field, lookup_value).execute()
        
        if not result.data:
            return None
        
        user = result.data[0]
        
        # Verify password
        if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            return None
        
        # Return Chainlit User object on successful authentication
        return cl.User(
            identifier=user["user_id"],
            metadata={
                "username": user["username"],
                "email": user["email"],
                "user_id": user["user_id"]
            }
        )
    except Exception as exc:
        print(f"Authentication error: {exc}")
        return None


# ============================================================================
# Quick Action Handlers
# ============================================================================

@cl.action_callback("action_products")
async def on_action_products(action: cl.Action):
    """Handle products action click."""
    await process_user_message("What products do you have?")


@cl.action_callback("action_storm_tech")
async def on_action_storm_tech(action: cl.Action):
    """Handle STORM technology action click."""
    await process_user_message("What technology is used in your STORM robots?")


@cl.action_callback("action_support")
async def on_action_support(action: cl.Action):
    """Handle support request action click."""
    await process_user_message("I want to submit a support case request")


# ============================================================================
# Chainlit Lifecycle Hooks
# ============================================================================

@cl.on_chat_start
async def on_chat_start():
    """Initialize chat session for authenticated user."""
    # Get authenticated user from Chainlit's session
    user = cl.user_session.get("user")
    
    username = user.metadata.get("username", "User") if user else "User"
    user_id = user.identifier if user else None
    email = user.metadata.get("email") if user else None

    cl.user_session.set("user_id", user_id)
    cl.user_session.set("username", username)
    cl.user_session.set("email", email)
    cl.user_session.set("chat_history", [])
    cl.user_session.set("detected_language", "en")
    cl.user_session.set("pending_support_case", None)  # Track pending support submission
    cl.user_session.set("is_authenticated", True)

    actions = [
        cl.Action(
            name="action_products",
            value="products",
            label="🛒 View Products",
            description="Browse our product catalog",
            payload={"query": "products"}
        ),
        cl.Action(
            name="action_storm_tech",
            value="storm",
            label="🤖 STORM Technology",
            description="Learn about LDI technology",
            payload={"query": "storm"}
        ),
        cl.Action(
            name="action_support",
            value="support",
            label="📧 Request Support",
            description="Submit a support case",
            payload={"query": "support"}
        ),
    ]

    welcome_msg = (
        f"👋 Welcome back, **{username}**!\n\n"
        f"I'm your intelligent assistant for robotic lawn mower solutions. I can help you with:\n\n"
        f"- 🛒 Product information and specifications\n"
        f"- 🔧 Technical support and troubleshooting\n"
        f"- 💳 Pricing inquiries\n"
        f"- 📧 Support case submissions\n\n"
        f"**Quick Actions:**"
    )

    await cl.Message(content=welcome_msg, actions=actions).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages."""
    await process_user_message(message.content)


async def process_user_message(user_input: str):
    """Process user message and generate response."""
    is_valid, error_msg = InputGuardrail.validate(user_input)
    if not is_valid:
        await cl.Message(content=error_msg).send()
        return

    if InputGuardrail.is_pricing_query(user_input):
        pricing_response = InputGuardrail.get_pricing_response()
        await cl.Message(content=pricing_response).send()
        return

    # Check if user is confirming a pending support case submission
    pending_case = cl.user_session.get("pending_support_case")
    user_response_lower = user_input.lower().strip()
    
    if pending_case and user_response_lower in ["yes", "y", "confirm", "submit"]:
        await handle_support_case_submission(pending_case)
        cl.user_session.set("pending_support_case", None)
        return
    elif pending_case and user_response_lower in ["no", "n", "cancel", "abort"]:
        await cl.Message(content="✋ **Support case submission cancelled.** How else can I help you?").send()
        cl.user_session.set("pending_support_case", None)
        return

    sanitized_input = InputGuardrail.sanitize(user_input)

    detected_lang = detect_language(sanitized_input)
    cl.user_session.set("detected_language", detected_lang)

    chat_history = cl.user_session.get("chat_history", [])
    chat_history.append({"role": "user", "content": sanitized_input})

    response_message = cl.Message(content="")
    await response_message.send()

    try:
        result = await Runner.run(
            support_agent,
            input=chat_history,
        )

        agent_response = result.final_output

        _, processed_response = OutputGuardrail.validate(agent_response)
        processed_response = OutputGuardrail.format_response(processed_response)

        response_message.content = processed_response
        await response_message.update()

        chat_history.append({"role": "assistant", "content": processed_response})
        cl.user_session.set("chat_history", chat_history)

    except Exception as exc:
        print(f"Agent error: {exc}")
        error_response = (
            "I apologize, but I encountered an issue processing your request. "
            "Please try rephrasing your question or contact support at info@am-robots.com"
        )
        response_message.content = error_response
        await response_message.update()


async def handle_support_case_submission(case_data: dict):
    """
    Handle support case submission to manufacturer.
    
    Args:
        case_data: Dictionary with user_id, original_case, and translated_case
    """
    user_id = case_data.get("user_id")
    original_case = case_data.get("original_case")
    translated_case = case_data.get("translated_case")
    
    # Get user info from session
    user_email = cl.user_session.get("email")
    username = cl.user_session.get("username")
    session_id = cl.user_session.get("id")
    
    if not user_email:
        error_msg = (
            "❌ **ERROR**\n\n"
            "Could not retrieve your email address from the session.\n"
            "Please log out and log back in."
        )
        await cl.Message(content=error_msg).send()
        return
    
    # Show loading message
    loading_msg = await cl.Message(content="⏳ **Submitting your support case to the manufacturer...**\n\nThis may take a moment...").send()
    
    try:
        logger.info(f"📤 Submitting case for user {user_id}")
        logger.info(f"   Email: {user_email}")
        logger.info(f"   Issue: {original_case[:100]}..." if len(original_case) > 100 else f"   Issue: {original_case}")
        
        # Submit to manufacturer website
        task_number = await support_case_service.submit_support_case_to_website(
            user_id, 
            translated_case
        )
        
        if task_number:
            logger.info(f"✅ Case submitted successfully - Task number: {task_number}")
            
            # Save to database
            support_case_service.save_support_case(
                user_id, 
                original_case, 
                translated_case, 
                task_number
            )
            logger.info(f"✓ Case saved to database")
            
            # Send confirmation to user
            confirmation = (
                f"✅ **CASE SUBMITTED SUCCESSFULLY**\n\n"
                f"📋 **Tracking Number:** `{task_number}`\n\n"
                f"**What happens next:**\n"
                f"1. Our support team will review your case\n"
                f"2. You'll receive updates at **{user_email}**\n"
                f"3. I'll monitor the status and notify you in this chat when resolved\n"
                f"4. Average response time: 2-4 business hours\n\n"
                f"🔔 **I'm now monitoring your case in the background...**\n\n"
                f"**Direct Contact:**\n"
                f"- Email: info@am-robots.com\n"
                f"- Phone: +45 8140 1221\n\n"
                f"**Need help with another issue?** Just ask!"
            )
            
            loading_msg.content = confirmation
            await loading_msg.update()
            
            # Start background monitoring for this specific case
            task = asyncio.create_task(
                monitor_case_for_session(
                    session_id=session_id,
                    task_number=task_number,
                    user_email=user_email,
                    username=username
                )
            )
            active_monitoring_tasks[session_id] = task
            logger.info(f"🔍 Started monitoring task for session {session_id}")
            
            # Log the submission
            print(f"✅ Support case {task_number} submitted for user {user_id}")
        else:
            error_msg = (
                "❌ **SUBMISSION FAILED**\n\n"
                "An error occurred while submitting to our support system.\n"
                "**Please try again or contact support directly:**\n\n"
                "- Email: info@am-robots.com\n"
                "- Phone: +45 8140 1221\n\n"
                "I apologize for the inconvenience."
            )
            loading_msg.content = error_msg
            await loading_msg.update()
            print(f"❌ Failed to submit support case for user {user_id}")
            
    except Exception as e:
        error_msg = (
            f"❌ **SUBMISSION ERROR**\n\n"
            f"An unexpected error occurred: {str(e)}\n"
            f"**Please contact support directly:**\n\n"
            f"- Email: info@am-robots.com\n"
            f"- Phone: +45 8140 1221"
        )
        loading_msg.content = error_msg
        await loading_msg.update()
        print(f"❌ Exception during support case submission: {e}")


async def check_case_status_for_user(task_number: str):
    """
    Check and report the status of a support case to the user.
    
    Args:
        task_number: The tracking number to check
    """
    checking_msg = await cl.Message(content="🔍 **Checking case status...**").send()
    
    try:
        status, response = await support_case_service.check_case_status(task_number)
        
        if status == "resolved":
            result = (
                f"✅ **CASE RESOLVED**\n\n"
                f"📋 **Tracking Number:** `{task_number}`\n\n"
                f"**Support Team Response:**\n"
                f"{response}\n\n"
                f"You should also receive a confirmation email shortly."
            )
        elif status == "open":
            result = (
                f"⏳ **CASE STILL OPEN**\n\n"
                f"📋 **Tracking Number:** `{task_number}`\n\n"
                f"Your support case is still being reviewed by our team.\n"
                f"Average response time: 2-4 business hours.\n\n"
                f"We'll send you an email update as soon as there's progress."
            )
        else:
            result = (
                f"❓ **STATUS UNKNOWN**\n\n"
                f"📋 **Tracking Number:** `{task_number}`\n\n"
                f"We couldn't determine the status of your case.\n"
                f"Please contact support directly:\n\n"
                f"- Email: info@am-robots.com\n"
                f"- Phone: +45 8140 1221"
            )
        
        checking_msg.content = result
        await checking_msg.update()
        
    except Exception as e:
        error_msg = (
            f"❌ **ERROR CHECKING STATUS**\n\n"
            f"An error occurred while checking your case status.\n"
            f"**Please try again or contact support:**\n\n"
            f"- Email: info@am-robots.com\n"
            f"- Phone: +45 8140 1221"
        )
        checking_msg.content = error_msg
        await checking_msg.update()
        print(f"Error checking case status: {e}")


@cl.on_chat_end
async def on_chat_end():
    """Handle chat session end and cleanup monitoring tasks."""
    session_id = cl.user_session.get("id")
    if session_id in active_monitoring_tasks:
        task = active_monitoring_tasks[session_id]
        task.cancel()
        logger.info(f"🗑️ Cancelled monitoring task for session {session_id}")


# ============================================================================
# Starters / Quick Actions (shown before first message)
# ============================================================================

@cl.set_starters
async def set_starters():
    """Set quick action starters for the chat."""
    return [
        cl.Starter(
            label="View Products",
            message="What products do you have? List all available AM ROBOTS products.",
            icon="🛒",
        ),
        cl.Starter(
            label="STORM Technology",
            message="What technology is used in your STORM robots? Explain the LDI technology.",
            icon="🤖",
        ),
        cl.Starter(
            label="Support Request",
            message="I want to submit a support case request",
            icon="📋",
        ),
        cl.Starter(
            label="About AM ROBOTS",
            message="Tell me about AM ROBOTS company",
            icon="ℹ️",
        ),
    ]


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info(f"🚀 {BRAND_NAME} Support Chatbot Ready!")
    logger.info(f"📊 Products folder: {Config.PRODUCTS_BASE_PATH}")
    logger.info(f"🤖 Using model: {Config.LLM_MODEL}")
    logger.info("=" * 60)
    
    logger.info("✅ Chatbot initialization complete")
    logger.info(f"📧 SMTP configured: {SMTP_HOST}")
    logger.info(f"🗄️ Database connected: {SUPABASE_URL[:30]}...")
    logger.info("🔍 Per-session case monitoring enabled")
