# AM ROBOTS Support Chatbot - Setup & Usage Guide

## 🚀 Quick Start

### Single Command Startup

```bash
chainlit run app.py
```

That's it! The entire application (chatbot + registration) runs on **http://localhost:8000**

---

## 📋 Features

### ✅ What's New

1. **Unified Application**: No need to run separate servers
   - Previously: `python registration.py` + `chainlit run app.py`
   - Now: Just `chainlit run app.py`

2. **Guest Access**: Users can chat without logging in
   - Browse products
   - Get technical support
   - Learn about AM ROBOTS

3. **Authentication Gate**: Login required ONLY for:
   - Submitting support case tickets
   - Accessing pricing information
   - Tracking support requests

4. **Integrated Registration**: Registration page built into the main app
   - Access at: **http://localhost:8000/register**
   - Secure password hashing with bcrypt
   - Stored in Supabase database

---

## 🔐 Authentication Flow

### Guest Users (No Login Required)
```
User visits http://localhost:8000
    ↓
Can immediately chat with bot
    ↓
Browse products, get support info
    ↓
When trying to submit support case
    ↓
Bot prompts: "Login Required"
    ↓
Provides links to /login or /register
```

### Registered Users
```
User visits http://localhost:8000
    ↓
Clicks "Login" or already has session
    ↓
Enters username & password
    ↓
Full access to all features:
  - Product browsing
  - Technical support
  - Support case submission
  - Case tracking
```

---

## 🌐 Available Routes

| Route | Description | Authentication |
|-------|-------------|----------------|
| `/` | Main chatbot interface | Optional |
| `/signin` | Custom AM Robots login page (with guest CTA) | No (public) |
| `/login` / `/login1` | Back-compat routes that redirect to `/signin` | No (public) |
| `/register` | Registration page | No (public) |
| `/api/register` | Registration API endpoint | No (public) |
| `/api/login` | Login API (returns JSON + sets `amr_session` cookie) | No (public) |
| `/api/logout` | Clears `amr_session` cookie | Needs existing cookie |
| `/api/session` | Returns `{ authenticated: bool, ... }` | Needs existing cookie |

---

## 🛠️ Configuration

### Environment Variables

Ensure your `.env` file contains:

```env
# Supabase Configuration (for user authentication)
SUPABASE_URL=your-supabase-project-url
SUPABASE_KEY=your-supabase-anon-key

# OpenAI API
OPENAI_API_KEY=your-openai-api-key

# Optional cookie settings
# SESSION_TTL_DAYS=7
# COOKIE_SECURE=true

# Other configurations...
```

### Chainlit Config

No additional configuration is required to keep guest access enabled—the built-in Chainlit login is disabled in `app.py` by clearing `CHAINLIT_AUTH_SECRET`. If you decide to re-enable Chainlit's own password wall, remove that line and set `require_login = true` inside `.chainlit/config.toml` (not recommended because it blocks guest chat).

---

## 📊 Database Schema

The system uses Supabase with the following `users` table:

```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,           -- Format: USR-XXXXXXXX
    username TEXT UNIQUE NOT NULL,      -- User's chosen username
    email TEXT UNIQUE NOT NULL,         -- User's email
    password_hash TEXT NOT NULL,        -- Bcrypt hashed password
    created_at TIMESTAMP DEFAULT NOW()  -- Registration timestamp
);
```

---

## 🔒 Security Features

1. **Password Hashing**: 
   - Uses bcrypt with automatic salt generation
   - Passwords never stored in plain text

2. **Input Validation**:
   - Username/email uniqueness checks
   - Minimum 8 character passwords
   - Email format validation

3. **Session Management**:
    - Custom `amr_session` httpOnly cookie created on login
    - In-memory TTL refreshes on every request/message
    - Chainlit receives user context via cookies (no more `__AUTH__` hack)

4. **SQL Injection Protection**:
   - Uses Supabase client (parameterized queries)
   - No raw SQL in registration

---

## 🧪 Testing the Flow

### Test 1: Guest Access
```bash
1. Start app: chainlit run app.py
2. Visit: http://localhost:8000
3. Start chatting immediately (no login required)
4. Ask: "What products do you have?"
5. ✅ Should receive product information
```

### Test 2: Registration
```bash
1. Visit: http://localhost:8000/register
2. Fill in:
   - Username: testuser
   - Email: test@example.com
   - Password: password123
3. Click "Create Account"
4. ✅ Should redirect to login page
```

### Test 3: Login & Support Case
```bash
1. Visit: http://localhost:8000
2. Click "Login"
3. Enter credentials from Test 2
4. Ask: "I want to submit a support case"
5. ✅ Should show support case form with your email pre-filled
```

### Test 4: Guest Support Case Attempt
```bash
1. Open a fresh private/incognito window and visit http://localhost:8000
2. Ask: "I need to submit a support request"
3. ✅ Should show message: "Login Required" with links to /signin and /register
```

---

## 🐛 Troubleshooting

### Issue: Browser keeps redirecting to `/signin`
**Solution**: Clear cookies for `localhost`. The new flow relies on the `amr_session` cookie—stale cookies from older builds can confuse the session resolver.

### Issue: Registration fails with "User already exists"
**Solution**: Use a different username/email or check Supabase database

### Issue: Can't access /register page
**Solution**: 
- Ensure app is running: `chainlit run app.py`
- Visit full URL: `http://localhost:8000/register`
- Check console for FastAPI mount errors

### Issue: Support case submission not working
**Solution**:
- Verify user is logged in (check username in welcome message)
- Check `is_authenticated` session variable
- Review browser console for errors

---

## 📁 Project Structure

```
rag_chatbot/
├── app.py                      # Main application (run this!)
├── registration.py             # ⚠️ DEPRECATED - Use app.py instead
├── run_server.py              # ⚠️ DEPRECATED - Use app.py instead
├── main.py                     # Legacy main file (agents)
├── .chainlit/
│   └── config.toml            # Chainlit configuration
├── src/
│   ├── agent/
│   │   ├── support_agent.py   # Agent definition
│   │   └── tools.py           # Agent tools (includes auth checks)
│   ├── services/
│   │   ├── product_service.py
│   │   └── brand_service.py
│   └── utils/
│       ├── guardrails.py
│       └── language.py
└── products/                   # Product data
```

---

## 🔄 Migration from Old Setup

### Before (Multiple Commands)
```bash
# Terminal 1
python registration.py

# Terminal 2
chainlit run app.py

# Terminal 3 (optional)
python run_server.py
```

### After (Single Command)
```bash
chainlit run app.py
```

**Benefits:**
- ✅ Single command
- ✅ No port conflicts
- ✅ Consistent authentication
- ✅ Professional user experience

---

## 📞 Support

For issues or questions:
- **Email**: info@am-robots.com
- **Phone**: +45 8140 1221
- **Website**: https://am-robots.com

---

## 📝 Development Notes

### How FastAPI Routes Are Integrated

The registration routes are mounted directly in `app.py`:

```python
from chainlit.server import app

@app.get("/register")
async def register_page():
    return HTMLResponse(content=REGISTRATION_HTML)

@app.post("/api/register")
async def register_api(request: Request):
    # Registration logic
```

Routes are added at module level and automatically available when Chainlit starts.

### Server-Side Sessions

- `/api/login` issues an httpOnly `amr_session` cookie for authenticated users.
- `/api/logout` clears that cookie and removes the corresponding in-memory session entry.
- `app.py` hydrates `cl.user_session` by reading the cookie from `chainlit.context`, so tools can keep using `cl.user_session.get()` with no client-side hacks.
- If you add new authenticated routes, always validate the cookie server-side instead of posting special messages back into the chat.

### Adding New Features Requiring Auth

To require authentication for a new feature:

1. In your tool function:
```python
import chainlit as cl

@function_tool
def my_protected_feature():
    is_authenticated = cl.user_session.get("is_authenticated", False)
    
    if not is_authenticated:
        return "Login required message with links to /login and /register"
    
    # Your feature logic here
    user_id = cl.user_session.get("user_id")
    username = cl.user_session.get("username")
    email = cl.user_session.get("email")
```

### Accessing User Data in Session

```python
# Check authentication status
is_authenticated = cl.user_session.get("is_authenticated", False)

# Get user information
user_id = cl.user_session.get("user_id")      # e.g., "USR-A1B2C3D4"
username = cl.user_session.get("username")     # e.g., "john_doe"
email = cl.user_session.get("email")           # e.g., "john@example.com"
```

---

## ✨ Best Practices

1. **Always use `chainlit run app.py`** for startup
2. **Don't run registration.py separately** - it's integrated
3. **Test guest mode** to ensure features work without login
4. **Check authentication** before accessing user-specific data
5. **Provide clear login prompts** when auth is required

---

*Last Updated: January 2, 2026*
