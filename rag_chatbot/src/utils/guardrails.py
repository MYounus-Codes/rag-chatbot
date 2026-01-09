"""
Guardrails for input validation and output safety.
Ensures secure and appropriate responses.
"""

import re
from typing import Tuple, Optional
from ..core.constants import HARMFUL_PATTERNS, PRICE_KEYWORDS, LOGIN_URL, MAX_RESPONSE_LENGTH


class InputGuardrail:
    """Validates and sanitizes user input for security and appropriateness."""
    
    @staticmethod
    def validate(user_input: str) -> Tuple[bool, Optional[str]]:
        """
        Validate user input.
        Returns (is_valid, error_message).
        If is_valid is False, error_message contains the reason.
        """
        if not user_input or not user_input.strip():
            return False, "Please provide a message."
        
        # Check for excessively long input
        if len(user_input) > 5000:
            return False, "Your message is too long. Please keep it under 5000 characters."
        
        # Check for harmful patterns (injection attempts, etc.)
        user_lower = user_input.lower()
        for pattern in HARMFUL_PATTERNS:
            if pattern.lower() in user_lower:
                return False, "I can only help with questions about AM ROBOTS products and services."
        
        # Check for potential prompt injection
        injection_patterns = [
            r"ignore\s+(all\s+)?(previous|above|prior)",
            r"disregard\s+(all\s+)?(previous|above|prior)",
            r"new\s+instructions?:",
            r"system\s*:",
            r"<\s*system\s*>",
            r"\[\s*SYSTEM\s*\]"
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return False, "I can only help with questions about AM ROBOTS products and services."
        
        return True, None
    
    @staticmethod
    def is_pricing_query(user_input: str) -> bool:
        """Check if the user is asking about pricing."""
        user_lower = user_input.lower()
        return any(keyword in user_lower for keyword in PRICE_KEYWORDS)
    
    @staticmethod
    def get_pricing_response() -> str:
        """Get the standard response for pricing queries."""
        return f"""To view pricing information, please log in to your dealer account.

**Login here:** [{LOGIN_URL}]({LOGIN_URL})

If you don't have a dealer account yet, you can sign up on our website to become an AM ROBOTS retailer and access dealer pricing.

**Benefits of becoming a dealer:**
- Access to dealer pricing
- Personal account manager
- Free shipping on orders over €1,500
- 14-day credit terms (subject to approval)
- Price guarantee

For more information, contact us at info@am-robots.com"""
    
    @staticmethod
    def sanitize(user_input: str) -> str:
        """Sanitize user input by removing potentially harmful content."""
        # Remove any HTML/script tags
        sanitized = re.sub(r'<[^>]+>', '', user_input)
        # Remove excessive whitespace
        sanitized = ' '.join(sanitized.split())
        return sanitized.strip()


class OutputGuardrail:
    """Validates and sanitizes bot output for safety and quality."""
    
    @staticmethod
    def validate(response: str) -> Tuple[bool, str]:
        """
        Validate and potentially modify the response.
        Returns (is_valid, processed_response).
        """
        if not response:
            return True, "I apologize, but I couldn't generate a response. Please try rephrasing your question."
        
        # Truncate if too long
        if len(response) > MAX_RESPONSE_LENGTH:
            response = response[:MAX_RESPONSE_LENGTH] + "\n\n[Response truncated for length]"
        
        # Check for hallucination indicators (making up specific prices, dates, etc.)
        response = OutputGuardrail._remove_hallucinations(response)
        
        return True, response
    
    @staticmethod
    def _remove_hallucinations(response: str) -> str:
        """Remove or flag potential hallucinations in the response."""
        # Check for fabricated prices (we don't provide prices)
        price_patterns = [
            r'€\s*\d+[\d,\.]*',
            r'\$\s*\d+[\d,\.]*',
            r'\d+[\d,\.]*\s*(?:EUR|USD|euro|dollar)',
        ]
        
        for pattern in price_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                # Replace with pricing redirect
                response = re.sub(
                    pattern, 
                    f"[Login to see pricing]({LOGIN_URL})", 
                    response, 
                    flags=re.IGNORECASE
                )
        
        return response
    
    @staticmethod
    def add_disclaimer_if_needed(response: str, query_type: str) -> str:
        """Add appropriate disclaimers based on the query type."""
        if query_type == "technical":
            if "disclaimer" not in response.lower():
                response += "\n\n*For technical issues, please consult the product manual or contact our support team if the problem persists.*"
        
        return response
    
    @staticmethod
    def format_response(response: str) -> str:
        """Format the response for better readability and proper markdown."""
        # Fix malformed bold text (** without closing)
        # Count asterisks and fix unclosed bold markers
        response = re.sub(r'\*\*([^*\n]+)\*\*\s*\|\s*\*\*', r'**\1** | ', response)
        
        # Convert malformed tables to simple lists
        # Detect table-like patterns with | and convert to bullet points
        lines = response.split('\n')
        cleaned_lines = []
        in_table = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip separator lines (|---|---|)
            if re.match(r'^[\|\-\s]+$', stripped) and '|' in stripped:
                in_table = True
                continue
            
            # Convert table rows to bullet points or plain text
            if '|' in stripped and stripped.startswith('|'):
                in_table = True
                # Extract cell contents
                cells = [c.strip().strip('*').strip() for c in stripped.split('|') if c.strip()]
                if cells:
                    # If it looks like a header row, make it bold
                    if len(cells) > 1:
                        cleaned_lines.append('- ' + ' | '.join(cells))
                    else:
                        cleaned_lines.append('- ' + cells[0])
            elif in_table and '|' in stripped:
                # Still processing table
                cells = [c.strip().strip('*').strip() for c in stripped.split('|') if c.strip()]
                if cells:
                    cleaned_lines.append('- ' + ': '.join(cells[:2]) if len(cells) >= 2 else '- ' + cells[0])
            else:
                in_table = False
                cleaned_lines.append(line)
        
        response = '\n'.join(cleaned_lines)
        
        # Fix standalone ** markers
        response = re.sub(r'^\s*\*\*\s*$', '', response, flags=re.MULTILINE)
        
        # Fix **text** | **text** patterns (convert to proper list)
        response = re.sub(r'\*\*([^*]+)\*\*\s*\|\s*\*\*([^*]+)\*\*', r'**\1** - \2', response)
        
        # Ensure proper spacing after headers
        response = re.sub(r'(\*\*[^*]+\*\*)([^\n\s])', r'\1 \2', response)
        
        # Remove excessive newlines
        response = re.sub(r'\n{3,}', '\n\n', response)
        
        # Remove excessive emojis (keep max 3)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", 
            flags=re.UNICODE
        )
        
        emojis = emoji_pattern.findall(response)
        if len(emojis) > 3:
            # Keep only first 3 emoji occurrences
            count = 0
            def replace_emoji(match):
                nonlocal count
                count += 1
                return match.group() if count <= 3 else ''
            
            response = emoji_pattern.sub(replace_emoji, response)
        
        return response.strip()
