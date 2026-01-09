# Support Case System - Quick Reference Guide

## For Developers

### File Structure
```
rag_chatbot/
├── app.py                                      # Main chatbot with support case integration
├── src/
│   ├── services/
│   │   └── support_case_service.py            # NEW: Support case operations
│   └── agent/
│       └── tools.py                           # Updated: submit_support_request tool
└── SUPPORT_CASE_IMPLEMENTATION.md             # Full documentation
```

---

## Key Functions Quick Reference

### SupportCaseService Methods

```python
from src.services.support_case_service import SupportCaseService

# Initialize
service = SupportCaseService(supabase_client)

# Save case to database
case = service.save_support_case(
    user_id="user-123",
    original_case="My robot isn't working",
    translated_case="My robot is not working",  # English version
    task_number="SUP-12345678"
)

# Update case status
service.update_case_status(
    task_number="SUP-12345678",
    status="resolved",
    response="We've fixed the issue..."
)

# Get all open cases
pending = service.get_pending_cases()

# Check case status (async)
status, response = await service.check_case_status("SUP-12345678")

# Submit to manufacturer (async)
task_number = await service.submit_support_case_to_website(
    user_id="user-123",
    issue_description="My robot has an issue"
)

# Send email
service.send_email(
    to_email="user@email.com",
    subject="Your case is resolved",
    body="<html>...</html>"
)

# Send resolution email
service.send_resolution_email(
    user_email="user@email.com",
    username="john_doe",
    task_number="SUP-12345678",
    response="We fixed it..."
)
```

---

## App.py Integration Points

### 1. Background Scheduler
```python
# Starts automatically on first chat
await start_scheduler()

# Runs every 5 minutes
async def check_pending_cases():
    pending_cases = support_case_service.get_pending_cases()
    for case in pending_cases:
        status, response = await support_case_service.check_case_status(task_number)
        if status == "resolved":
            support_case_service.update_case_status(task_number, "resolved", response)
            support_case_service.send_resolution_email(...)
```

### 2. Message Processing
```python
# In process_user_message()
pending_case = cl.user_session.get("pending_support_case")
if pending_case and user_response_lower in ["yes", "y"]:
    await handle_support_case_submission(pending_case)
```

### 3. Case Submission
```python
# Called when user confirms "Yes"
async def handle_support_case_submission(case_data):
    task_number = await support_case_service.submit_support_case_to_website(...)
    support_case_service.save_support_case(...)
    # Show confirmation to user
```

### 4. Status Checking
```python
# Can be called manually or automatically
async def check_case_status_for_user(task_number):
    status, response = await support_case_service.check_case_status(task_number)
    # Show result to user
```

---

## Session Variables

```python
# Set in on_chat_start()
cl.user_session.set("user_id", user_id)
cl.user_session.set("username", username)
cl.user_session.set("email", email)
cl.user_session.set("is_authenticated", True)
cl.user_session.set("pending_support_case", None)  # Stores case data

# Pending case structure
pending_case = {
    "user_id": "user-123",
    "original_case": "User's issue in original language",
    "translated_case": "User's issue in English",
    "product_name": "STORM 2000",
    "timestamp": "2024-01-05T10:30:00"
}
```

---

## User Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ User: "I need support with my robot"                        │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────────┐
    │ submit_support_request() tool      │
    │ - Validates authentication         │
    │ - Translates to English            │
    │ - Stores in pending_support_case   │
    └───────────────┬─────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────────────┐
    │ Agent: "Ready to submit? Say 'Yes'"  │
    └───────────────┬──────────────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
         ▼                     ▼
    "Yes"              "No" / "Cancel"
         │                     │
         ▼                     ▼
    ┌──────────────────┐  "OK, cancelled"
    │ Confirmation     │
    │ flow triggered   │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────────────────────┐
    │ handle_support_case_submission()  │
    │ - Call Playwright submission      │
    │ - Save to database               │
    │ - Show tracking number           │
    └────────┬─────────────────────────┘
             │
             ▼
    ┌──────────────────────────────────┐
    │ Background Scheduler              │
    │ (Every 5 minutes)                │
    │ - Check case status              │
    │ - Send email if resolved         │
    │ - Send reminder after 24h        │
    └──────────────────────────────────┘
```

---

## Common Tasks

### Add Support Case Checking to Agent
The agent can ask: "What's the status of SUP-12345678?"
This triggers `check_case_status_for_user()` automatically if added to tool list.

### Change Status Check Interval
```python
# In start_scheduler()
scheduler.add_job(
    check_pending_cases,
    "interval",
    minutes=5,  # Change this number
    id="check_support_cases"
)
```

### Modify Email Template
```python
# In SupportCaseService.send_resolution_email()
subject = f"Your Support Case {task_number} Has Been Resolved"
body = f"""
<html><body>
    <!-- Modify HTML here -->
</body></html>
"""
```

### Handle Failed Submissions
Currently shows error and contact info. To add retry logic:
```python
# In handle_support_case_submission()
retries = 0
while retries < 3:
    task_number = await support_case_service.submit_support_case_to_website(...)
    if task_number:
        break
    retries += 1
    await asyncio.sleep(2)
```

---

## Testing Checklist

- [ ] User can submit a support case
- [ ] Tracking number is generated and displayed
- [ ] Case appears in database
- [ ] Background scheduler is running (check logs)
- [ ] Status checks are happening (check logs every 5 min)
- [ ] Email notifications work (check inbox)
- [ ] User can check case status anytime
- [ ] Canceling case works ("No" response)
- [ ] Multiple concurrent cases work
- [ ] Error handling shows user-friendly messages

---

## Troubleshooting

### Scheduler not running
```python
# Check if it's already running
if scheduler.running:
    print("Scheduler is already running")
# Or restart it
scheduler.shutdown()
await start_scheduler()
```

### Email not sending
```
1. Check SMTP credentials in .env
2. Check SMTP_HOST and SMTP_PORT
3. Check if sender email is authorized
4. Check firewalls/network access to SMTP server
5. Add logging to send_email() method
```

### Playwright submission failing
```
1. Check BASE_URL is correct
2. Check selectors match the website
3. Add delays if page is slow
4. Enable headed mode: headless=False for debugging
5. Check console output for specific errors
```

### Pending case not submitting
```python
# Check if case data is stored
case = cl.user_session.get("pending_support_case")
print(f"Pending case: {case}")

# Check user authentication
is_auth = cl.user_session.get("is_authenticated")
print(f"Is authenticated: {is_auth}")
```

---

## Database Queries

### Find all cases for a user
```sql
SELECT * FROM support_cases 
WHERE user_id = 'user-123' 
ORDER BY created_at DESC;
```

### Find all open cases
```sql
SELECT * FROM support_cases 
WHERE status = 'open' 
ORDER BY created_at DESC;
```

### Find resolved cases
```sql
SELECT * FROM support_cases 
WHERE status = 'resolved' 
ORDER BY updated_at DESC;
```

### Update a case manually
```sql
UPDATE support_cases 
SET status = 'resolved', support_response = 'Response text'
WHERE task_number = 'SUP-12345678';
```

---

## Key Design Decisions

1. **Service Layer**: Separated concerns for cleaner code
2. **Session Storage**: Pending cases stored in Chainlit session, not database
3. **Background Monitoring**: Automatic checks provide better UX
4. **Email Notifications**: Async operations don't block user chat
5. **Browser Automation**: Playwright for integration with existing website
6. **Confirmation Flow**: "Yes" confirmation prevents accidental submissions

---

## Performance Considerations

- **Scheduler**: Runs every 5 minutes for all users
- **Database Queries**: Only fetches open cases
- **Email Sending**: Async, doesn't block chat
- **Browser Automation**: Runs in background, headless
- **Session Storage**: In-memory, cleared on chat end

---

## Security Notes

- Environment variables protect credentials
- Supabase handles user authentication
- Email addresses from database only
- Browser automation uses headless mode
- User isolation via user_id in database
- Chat session isolation in Chainlit

