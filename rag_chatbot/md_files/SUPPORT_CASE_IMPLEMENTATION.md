# Support Case Management System Implementation

## Overview
Complete support case management functionality has been implemented in the app.py chatbot, mirroring and extending the functionality from main.py. This includes:
- **Case Submission**: Submit support cases to the manufacturer
- **Status Checking**: Check case status with automatic background monitoring
- **Email Notifications**: Send resolution emails to users
- **Background Scheduler**: Automatic case status checks every 5 minutes

---

## Architecture

### 1. New Service Layer: `SupportCaseService`
**File**: `src/services/support_case_service.py`

This is a new dedicated service class that handles all support case operations:

#### Core Methods:

##### `save_support_case(user_id, original_case, translated_case, task_number)`
- Saves support case to Supabase database
- Stores original and translated versions for language support
- Records case creation timestamp
- Sets initial status as "open"

##### `update_case_status(task_number, status, response=None)`
- Updates case status in database (open, resolved, etc.)
- Optionally stores support team response
- Records update timestamp

##### `get_pending_cases()`
- Retrieves all open cases with user information
- Used by background scheduler for status monitoring
- Includes user email and username for notifications

##### `async submit_support_case_to_website(user_id, issue_description)`
- Submits case to manufacturer website using Playwright browser automation
- Performs human-like interactions (delays, typing simulation)
- Extracts task number from submission response
- Returns task number if successful, None if failed

##### `async check_case_status(task_number)`
- Checks case status on manufacturer website
- Navigates to status page and searches for case
- Returns tuple: (status, response_text)
- Possible statuses: "open", "resolved", "unknown"

##### `async send_reminder(task_number)`
- Sends reminder about pending case via website automation
- Used after 24 hours of no response
- Helps track cases that might be stuck

##### `send_email(to_email, subject, body)` & `send_resolution_email(...)`
- Sends SMTP emails to users
- HTML-formatted responses
- Resolution emails include support team response

---

## App.py Integration

### 1. Imports & Initialization
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.services.support_case_service import SupportCaseService

support_case_service = SupportCaseService(supabase)
scheduler = AsyncIOScheduler()
```

### 2. Background Scheduler Setup
**Functions**: `start_scheduler()`, `check_pending_cases()`

- Starts AsyncIOScheduler on first chat start
- Schedules `check_pending_cases()` to run every 5 minutes
- Monitors all open support cases
- Auto-detects case resolutions
- Sends resolution emails when cases are resolved
- Sends reminders after 24 hours of inactivity

**Key Features**:
- Automatic status checking without user intervention
- Instant notification when case is resolved
- Email notifications with support team responses
- Logging of all status changes

### 3. Session State Management
**On Chat Start** (`on_chat_start()`):
```python
cl.user_session.set("pending_support_case", None)  # Track pending submission
cl.user_session.set("is_authenticated", True)      # Authentication flag
```

### 4. Message Processing Flow
**Function**: `process_user_message(user_input)`

**NEW LOGIC**: Detects and handles support case confirmation:
```
1. Check if user has pending support case
2. If "yes"/"confirm" → Submit case to manufacturer
3. If "no"/"cancel" → Discard and continue chatting
4. Otherwise → Process normally through support agent
```

This allows for a natural two-step flow:
1. Agent prepares case details
2. User confirms "Yes" to submit

### 5. Support Case Submission Handler
**Function**: `async handle_support_case_submission(case_data)`

**Flow**:
```
1. Show "Submitting..." loading message
2. Call SupportCaseService.submit_support_case_to_website()
3. If successful:
   - Save case to database
   - Show confirmation with tracking number
   - Display next steps
   - Log submission
4. If failed:
   - Show error message
   - Provide manual contact options
   - Log failure
```

**Response Format**:
```
✅ CASE SUBMITTED SUCCESSFULLY

📋 Tracking Number: SUP-12345678

What happens next:
1. Our support team will review your case
2. You'll receive email updates at user@email.com
3. Automatic status checks every 5 minutes
4. Average response time: 2-4 business hours
```

### 6. Case Status Checking
**Function**: `async check_case_status_for_user(task_number)`

- Can be called manually or automatically
- Checks manufacturer website for updates
- Provides clear status messages to user
- Three possible states:
  - ✅ **RESOLVED**: Shows team response
  - ⏳ **OPEN**: Shows it's being reviewed
  - ❓ **UNKNOWN**: Shows contact options

---

## Tools Integration

### Updated: `submit_support_request()` in `src/agent/tools.py`

**NEW FUNCTIONALITY**:
- Stores pending case data in session: `pending_support_case`
- Translates issue to English automatically
- Prepares case details for display
- Asks user to confirm with "Yes"
- Handles authentication checking

**Flow**:
```
submit_support_request() → Prepares case → Stores in session → 
Asks for confirmation → User says "Yes" → handle_support_case_submission() → 
Submits to manufacturer
```

---

## Complete User Journey

### 1. User Requests Support
```
User: "I need help with my STORM robot"
Agent: Uses submit_support_request tool
```

### 2. Case Preparation
```
Agent Response:
"✅ Support Request Ready for Submission

Your Account: username
Email: user@email.com

Issue Description: [user's issue]

Would you like me to submit this case now?
Reply 'Yes' to confirm submission."
```

### 3. User Confirms
```
User: "Yes"
System: Detects "yes" in pending_support_case
System: Calls handle_support_case_submission()
```

### 4. Submission Process
```
⏳ Submitting your support case to the manufacturer...
This may take a moment...

[After submission]

✅ CASE SUBMITTED SUCCESSFULLY
📋 Tracking Number: SUP-12345678
[Next steps and contact info]
```

### 5. Background Monitoring
```
Every 5 minutes:
- Check pending cases
- Query manufacturer website
- If resolved: Send email to user
- If 24+ hours: Send reminder

User receives email:
"Your Support Case SUP-12345678 Has Been Resolved
[Support team response]"
```

### 6. User Can Check Status Anytime
```
User: "What's the status of SUP-12345678?"
System: Calls check_case_status_for_user()
System: Shows current status to user
```

---

## Database Schema

### Support Cases Table (`support_cases`)
```
- id: UUID (primary key)
- user_id: UUID (foreign key)
- task_number: TEXT (tracking number from manufacturer)
- original_case: TEXT (user's original language)
- translated_case: TEXT (English translation)
- status: TEXT (open, resolved, etc.)
- support_response: TEXT (optional, from support team)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

### Related Users Table (existing)
```
- user_id: UUID
- username: TEXT
- email: TEXT
- password_hash: TEXT
```

---

## Key Features

### 1. Multi-Language Support
- Original case stored in user's language
- Automatically translated to English for manufacturer
- Responses can be translated back if needed

### 2. Automatic Status Monitoring
- Background scheduler checks every 5 minutes
- No user intervention needed
- Instant notifications when resolved

### 3. Email Notifications
- HTML-formatted emails
- Includes support team response
- Sent to user's registered email
- Professional branding

### 4. Browser Automation
- Uses Playwright for website interaction
- Human-like delays and typing simulation
- Anti-detection measures
- Handles both submission and status checking

### 5. Error Handling
- Graceful fallbacks for submission failures
- User-friendly error messages
- Direct contact information provided
- Logging for debugging

### 6. Security
- User authentication required
- Session-based pending case storage
- SMTP credentials from environment
- Supabase authentication

---

## Environment Variables Required

```bash
# Existing
SUPABASE_URL=
SUPABASE_KEY=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=

# Optional (for browser automation)
BASE_URL=http://localhost:3000  # Manufacturer website URL
```

---

## Testing the Implementation

### 1. Test Case Submission
```
1. Login to chatbot
2. Say: "I need support with..."
3. Agent prepares case
4. Respond: "Yes"
5. System submits and shows tracking number
6. Check database for saved case
```

### 2. Test Background Monitoring
```
1. Submit a case
2. Keep chat window open
3. Watch logs for status checks
4. When resolved, receive email
```

### 3. Test Status Checking
```
1. Ask about a case: "What's the status of SUP-xxx?"
2. System checks website
3. Shows current status
```

### 4. Test Multiple Cases
```
1. Submit multiple cases
2. Let scheduler monitor all
3. They all get checked and notified independently
```

---

## Differences from main.py

| Feature | main.py | app.py |
|---------|---------|--------|
| Service Layer | Functions in main file | Dedicated SupportCaseService class |
| Session Management | Not applicable | Chainlit user_session |
| Message Handling | Directly in handlers | Added confirmation flow |
| Scheduler | AsyncIOScheduler | AsyncIOScheduler (integrated with chat) |
| Email | Direct SMTP | Via SupportCaseService |
| Authentication | Chainlit auth callback | Built-in to flow |
| Tools | Agent function tools | Integrated with session storage |

---

## Future Enhancements

1. **Webhook Support**: Receive updates via webhook instead of polling
2. **Case Reassignment**: Allow users to change assigned support team
3. **Priority Levels**: Support for urgent/high priority cases
4. **Chat History**: Store case details in chat for reference
5. **Multi-Language Responses**: Auto-translate support team responses back to user language
6. **Analytics**: Track support case metrics and trends
7. **Custom Templates**: Pre-filled case templates for common issues
8. **Escalation**: Auto-escalate cases after X hours

---

## Summary

All support case functionality from main.py has been successfully implemented in app.py with:
- ✅ Service layer architecture
- ✅ Background scheduling
- ✅ Email notifications  
- ✅ Session-based state management
- ✅ Natural conversation flow
- ✅ Comprehensive error handling
- ✅ Multi-language support
- ✅ Browser automation for submission and status checking
