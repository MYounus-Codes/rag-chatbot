"""
Support Case Service - Handle all support case operations.
Manages case submission, tracking, status checking, and notifications.
"""

import os
import json
import smtplib
import random
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Tuple, List, Dict
from pathlib import Path

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import Client

from ..core.config import Config

logger = logging.getLogger(__name__)


class SupportCaseService:
    """Service for managing support cases."""
    
    def __init__(self, supabase_client: Client):
        """Initialize support case service."""
        self.supabase = supabase_client
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_from_email = os.getenv("SMTP_FROM_EMAIL")
        self.base_url = os.getenv("BASE_URL", "http://localhost:3000")
    
    def save_support_case(
        self, 
        user_id: str, 
        original_case: str, 
        translated_case: str, 
        task_number: str
    ) -> Dict:
        """
        Save support case to database.
        
        Args:
            user_id: User's unique identifier
            original_case: Original case description
            translated_case: Case translated to English
            task_number: Assigned task number from manufacturer
        
        Returns:
            Saved case data
        """
        data = {
            "user_id": user_id,
            "original_case": original_case,
            "translated_case": translated_case,
            "task_number": task_number,
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
        }
        result = self.supabase.table("support_cases").insert(data).execute()
        return result.data[0] if result.data else data
    
    def update_case_status(
        self, 
        task_number: str, 
        status: str, 
        response: str = None
    ) -> None:
        """
        Update support case status.
        
        Args:
            task_number: Task number to update
            status: New status (open, resolved, etc.)
            response: Support team response (if resolved)
        """
        data = {"status": status, "updated_at": datetime.utcnow().isoformat()}
        if response:
            data["support_response"] = response
        
        self.supabase.table("support_cases").update(data).eq("task_number", task_number).execute()
    
    def get_pending_cases(self) -> List[Dict]:
        """
        Get all pending support cases.
        
        Returns:
            List of pending cases with user information
        """
        try:
            result = self.supabase.table("support_cases").select(
                "*, users(email, username)"
            ).eq("status", "open").execute()
            
            cases = result.data or []
            logger.debug(f"Query returned {len(cases)} pending case(s)")
            
            return cases
        except Exception as e:
            logger.error(f"❌ Error fetching pending cases from database: {e}", exc_info=True)
            return []
    
    async def submit_support_case_to_website(
        self, 
        user_id: str, 
        issue_description: str
    ) -> Optional[str]:
        """
        Submit support case to manufacturer website using browser automation.
        
        Args:
            user_id: User's unique identifier
            issue_description: Description of the issue
        
        Returns:
            Task number if successful, None otherwise
        """
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
                await page.goto(self.base_url, wait_until="networkidle")
                await self._human_delay(1000, 2000)
                
                await self._human_type(page, 'input[placeholder*="user ID"]', user_id)
                await self._human_delay(300, 600)
                
                await self._human_type(page, 'textarea[placeholder*="describe"]', issue_description)
                await self._human_delay(500, 1000)
                
                submit_button = await page.wait_for_selector('button[type="submit"], button:has-text("Submit")')
                await submit_button.click()
                await self._human_delay(2000, 3000)
                
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
    
    async def check_case_status(self, task_number: str) -> Tuple[str, Optional[str]]:
        """
        Check the status of a support case on manufacturer website.
        
        Args:
            task_number: Task number to check
        
        Returns:
            Tuple of (status, response_text)
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            )
            page = await context.new_page()
            
            try:
                logger.debug(f"Navigating to status page for {task_number}")
                await page.goto(f"{self.base_url}/status", wait_until="networkidle", timeout=30000)
                await self._human_delay(1000, 2000)
                
                # Enter task number in search field
                logger.debug("Looking for task number input field")
                input_field = await page.query_selector('input[type="text"], input[placeholder*="task"], input[placeholder*="Task"]')
                if input_field:
                    await input_field.fill(task_number)
                    await self._human_delay(300, 600)
                
                # Click search button
                logger.debug("Looking for search button")
                search_button = await page.query_selector('button:has-text("Search"), button[type="submit"]')
                if search_button:
                    await search_button.click()
                    await self._human_delay(3000, 4000)
                
                # Get full page content for debugging
                page_content = await page.content()
                page_text = await page.text_content('body')
                
                logger.debug(f"Page text preview: {page_text[:200]}...")
                
                # Check for resolved status - multiple patterns
                is_resolved = False
                response_text = None
                
                # Pattern 1: Check page text for "Resolved"
                if "resolved" in page_text.lower() or "resolved" in page_content.lower():
                    is_resolved = True
                    logger.debug("Found 'resolved' in page content")
                
                # Pattern 2: Check for specific status badges/labels
                status_badges = await page.query_selector_all('[class*="status"], [class*="badge"], span:has-text("Resolved"), span:has-text("Open")')
                for badge in status_badges:
                    badge_text = await badge.text_content()
                    logger.debug(f"Found status badge: {badge_text}")
                    if badge_text and "resolved" in badge_text.lower():
                        is_resolved = True
                        break
                
                # Pattern 3: Look for h1, h2, h3 headers with status
                headers = await page.query_selector_all('h1, h2, h3, h4')
                for header in headers:
                    header_text = await header.text_content()
                    if header_text and "resolved" in header_text.lower():
                        is_resolved = True
                        logger.debug(f"Found resolved in header: {header_text}")
                        break
                    elif header_text and "open" in header_text.lower():
                        logger.debug(f"Found open status in header: {header_text}")
                
                if is_resolved:
                    # Try to extract response text from the specific HTML structure
                    logger.debug("Case is resolved, extracting response...")
                    
                    # Parse HTML to extract the specific response div
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(page_content, 'html.parser')
                    
                    response_text = None
                    response_date = None
                    
                    # Look for the specific div structure: flex items-start space-x-3
                    response_container = soup.find('div', class_=lambda x: x and 'flex' in x and 'items-start' in x)
                    if response_container:
                        logger.debug("Found response container with flex layout")
                        
                        # Extract date from the purple text
                        date_element = response_container.find('p', class_=lambda x: x and 'text-purple-500' in x)
                        if date_element:
                            response_date = date_element.get_text(strip=True)
                            logger.debug(f"Extracted date: {response_date}")
                        
                        # Extract actual response message from gray text
                        message_element = response_container.find('p', class_=lambda x: x and 'text-gray-800' in x)
                        if message_element:
                            response_text = message_element.get_text(strip=True)
                            logger.debug(f"Extracted message: {response_text[:100]}...")
                    
                    # Fallback: Look for any element with "Support Team Response" nearby
                    if not response_text:
                        logger.debug("Trying fallback extraction methods...")
                        
                        # Find "Support Team Response" header and get next paragraph
                        support_header = soup.find(text=lambda x: x and 'Support Team Response' in x)
                        if support_header:
                            parent = support_header.find_parent()
                            if parent:
                                # Look for sibling or nearby paragraph with the actual message
                                next_p = parent.find_next('p', class_=lambda x: x and 'text-gray' in x)
                                if next_p:
                                    response_text = next_p.get_text(strip=True)
                                    logger.debug("Extracted using fallback method")
                        
                        # Another fallback: look for date pattern and text after it
                        if not response_text:
                            import re
                            date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\s+at\s+\d{1,2}:\d{2}\s+[AP]M'
                            match = re.search(date_pattern + r'\s*([^<]+)', page_text)
                            if match:
                                response_date = match.group(0)[:match.group(0).find(match.group(len(match.groups())))]  
                                response_text = match.group(len(match.groups())).strip()
                                logger.debug("Extracted using date pattern matching")
                    
                    # Format the response nicely
                    if response_text:
                        formatted_parts = []
                        formatted_parts.append("Support Team Response")
                        formatted_parts.append("")  # Empty line
                        if response_date:
                            formatted_parts.append(response_date)
                            formatted_parts.append("")  # Empty line
                        formatted_parts.append(response_text)
                        
                        final_response = "\n".join(formatted_parts)
                        logger.info(f"✓ Case {task_number} detected as RESOLVED")
                        return "resolved", final_response
                    
                    # If still no response found, use page text extraction
                    if not response_text:
                        logger.debug("No structured response found, falling back to text extraction")
                        response_text = page_text.strip()
                    
                    if not response_text:
                        response_text = "Your case has been resolved. Please check the manufacturer website for details."
                    
                    logger.info(f"✓ Case {task_number} detected as RESOLVED")
                    return "resolved", response_text
                
                # Check if explicitly open
                if "open" in page_text.lower() and "resolved" not in page_text.lower():
                    logger.debug("Case appears to be still open")
                    return "open", None
                
                # Check for error messages indicating case not found
                if "not found" in page_text.lower() or "no results" in page_text.lower():
                    logger.warning(f"Case {task_number} not found on website")
                    return "unknown", None
                        
            except Exception as e:
                logger.error(f"Error checking status for {task_number}: {e}", exc_info=True)
            finally:
                await browser.close()
        
        return "unknown", None
    
    async def send_reminder(self, task_number: str) -> bool:
        """
        Send a reminder about a pending support case.
        
        Args:
            task_number: Task number to send reminder for
        
        Returns:
            True if successful, False otherwise
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                await page.goto(f"{self.base_url}/reminder", wait_until="networkidle")
                await self._human_delay(1000, 2000)
                
                await self._human_type(page, 'input[placeholder*="task"], input[type="text"]', task_number)
                await self._human_delay(500, 1000)
                
                send_button = await page.wait_for_selector('button:has-text("Send Reminder"), button[type="submit"]')
                await send_button.click()
                await self._human_delay(2000, 3000)
                
                return True
            except Exception as e:
                print(f"Error sending reminder: {e}")
                return False
            finally:
                await browser.close()
    
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Send email notification.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (HTML)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"📧 Preparing email...")
            logger.info(f"   To: {to_email}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   From: {self.smtp_from_email}")
            logger.info(f"   SMTP Server: {self.smtp_host}:{self.smtp_port}")
            
            msg = MIMEMultipart()
            msg["From"] = self.smtp_from_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))
            
            logger.info(f"   Connecting to SMTP server...")
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                logger.info(f"   Starting TLS...")
                server.starttls()
                
                logger.info(f"   Logging in as {self.smtp_user}...")
                server.login(self.smtp_user, self.smtp_password)
                
                logger.info(f"   Sending message...")
                server.send_message(msg)
                
            logger.info(f"✅ Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP Authentication failed: {e}")
            logger.error(f"   Check SMTP_USER and SMTP_PASSWORD in .env")
            return False
        except smtplib.SMTPConnectError as e:
            logger.error(f"❌ SMTP Connection failed: {e}")
            logger.error(f"   Check SMTP_HOST and SMTP_PORT in .env")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending email: {e}", exc_info=True)
            logger.error(f"   To: {to_email}")
            logger.error(f"   Server: {self.smtp_host}:{self.smtp_port}")
            logger.error(f"   User: {self.smtp_user}")
            return False
    
    def format_resolution_response(self, response: str) -> str:
        """Format the raw response from the website into a clean, readable format.
        
        Args:
            response: Raw response text from the website
        
        Returns:
            Beautifully formatted response string
        """
        # If the response is already well-formatted (contains line breaks), return as-is
        if response.count('\n') >= 2:
            return response.strip()
        
        import re
        
        # Remove common website artifacts (only if text is messy)
        clean_response = response
        
        # Remove navigation items if they appear
        clean_response = re.sub(r'Submit Case\s*Check Status\s*Reminder\s*Admin', '', clean_response)
        clean_response = re.sub(r'Search\s*Current Status\s*Task Number', '', clean_response)
        
        # Remove "TechManufacture" footer
        clean_response = re.sub(r'©.*TechManufacture.*', '', clean_response, flags=re.DOTALL)
        
        # Remove URLs and links
        clean_response = re.sub(r'https?://\S+', '', clean_response)
        
        # Remove excess whitespace
        clean_response = re.sub(r'\s+', ' ', clean_response)
        clean_response = clean_response.strip()
        
        # If response is too short or seems corrupted, provide fallback
        if len(clean_response) < 20:
            return "Your support case has been resolved. Our team has addressed your issue. For detailed information, please check your email or contact us directly."
        
        # Ensure proper capitalization
        if clean_response and clean_response[0].islower():
            clean_response = clean_response[0].upper() + clean_response[1:]
        
        # Ensure it ends with proper punctuation
        if clean_response and clean_response[-1] not in '.!?':
            clean_response += '.'
        
        return clean_response
    
    def send_resolution_email(
        self, 
        user_email: str, 
        username: str, 
        task_number: str, 
        response: str
    ) -> bool:
        """
        Send resolution email to user.
        
        Args:
            user_email: User's email address
            username: User's username
            task_number: Task number that was resolved
            response: Support team response
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"\n📬 Sending resolution email for case {task_number}")
        logger.info(f"   Recipient: {username} <{user_email}>")
        
        # Format response with proper line breaks
        formatted_response = response.replace('\n', '<br>')
        
        subject = f"Your Support Case {task_number} Has Been Resolved"
        body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9fafb;
        }}
        .container {{
            background-color: #ffffff;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 25px;
            text-align: center;
        }}
        .header h2 {{
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .greeting {{
            font-size: 16px;
            margin-bottom: 15px;
            color: #1f2937;
        }}
        .info-box {{
            background-color: #eff6ff;
            border-left: 4px solid #2563eb;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .info-label {{
            font-weight: 600;
            color: #1e40af;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}
        .task-number {{
            font-size: 18px;
            font-weight: 700;
            color: #2563eb;
            font-family: 'Courier New', monospace;
        }}
        .response-box {{
            background-color: #f0fdf4;
            border: 1px solid #86efac;
            border-radius: 8px;
            padding: 20px;
            margin: 25px 0;
        }}
        .response-title {{
            color: #059669;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
        }}
        .response-title::before {{
            content: "✓";
            display: inline-block;
            width: 24px;
            height: 24px;
            background-color: #059669;
            color: white;
            border-radius: 50%;
            text-align: center;
            line-height: 24px;
            margin-right: 10px;
            font-weight: bold;
        }}
        .response-content {{
            color: #1f2937;
            font-size: 15px;
            line-height: 1.8;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
        }}
        .footer-text {{
            color: #6b7280;
            font-size: 14px;
            margin-bottom: 10px;
        }}
        .contact-info {{
            background-color: #f9fafb;
            padding: 15px;
            border-radius: 6px;
            margin-top: 15px;
        }}
        .contact-info p {{
            margin: 8px 0;
            font-size: 14px;
            color: #4b5563;
        }}
        .signature {{
            margin-top: 20px;
            font-weight: 600;
            color: #1f2937;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🎉 Support Case Resolved</h2>
        </div>
        
        <p class="greeting">Dear <strong>{username}</strong>,</p>
        
        <p>We're pleased to inform you that your support case has been successfully resolved by our technical team.</p>
        
        <div class="info-box">
            <div class="info-label">Tracking Number</div>
            <div class="task-number">{task_number}</div>
        </div>
        
        <div class="response-box">
            <div class="response-title">Support Team Response</div>
            <div class="response-content">{formatted_response}</div>
        </div>
        
        <div class="footer">
            <p class="footer-text">If you have any additional questions or need further assistance, please don't hesitate to contact us:</p>
            
            <div class="contact-info">
                <p><strong>📧 Email:</strong> info@am-robots.com</p>
                <p><strong>📞 Phone:</strong> +45 8140 1221</p>
                <p><strong>🌐 Website:</strong> www.am-robots.com</p>
            </div>
            
            <p class="signature">
                Best regards,<br>
                <strong>AM ROBOTS Support Team</strong>
            </p>
        </div>
    </div>
</body>
</html>
        """
        
        result = self.send_email(user_email, subject, body)
        if result:
            logger.info(f"✅ Resolution email sent successfully")
        else:
            logger.error(f"❌ Failed to send resolution email")
        return result
    
    async def _human_delay(self, min_ms: int = 500, max_ms: int = 1500) -> None:
        """Simulate human-like delay."""
        import asyncio
        await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))
    
    async def _human_type(self, page, selector: str, text: str) -> None:
        """Simulate human-like typing."""
        element = await page.wait_for_selector(selector, timeout=10000)
        await element.click()
        await self._human_delay(200, 400)
        
        for char in text:
            await page.keyboard.type(char, delay=random.uniform(50, 150))
            if random.random() < 0.1:
                await self._human_delay(100, 300)
