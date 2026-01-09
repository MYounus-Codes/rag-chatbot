# Quick Reference - AM ROBOTS Chatbot

## 🚀 One-Line Commands

```bash
# Start the application
chainlit run app.py

# Install dependencies
uv sync

# Check syntax
python -m py_compile app.py
```

---

## 🌐 URLs

| URL | Purpose |
|-----|---------|
| `http://localhost:8000` | Main chat interface |
| `http://localhost:8000/register` | Registration page |
| `http://localhost:8000/signin` | Custom AM Robots login page |
| `http://localhost:8000/api/register` | Registration API (POST) |
| `http://localhost:8000/api/login` | Login API (POST) |
| `http://localhost:8000/api/logout` | Logout API (POST) |
| `http://localhost:8000/api/session` | Session status (GET) |

---

## 🔑 Environment Variables

```env
# Required
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx...
OPENAI_API_KEY=sk-xxx...

# Product paths (auto-configured)
PRODUCTS_BASE_PATH=products

# Optional cookie tuning
# SESSION_TTL_DAYS=7
# COOKIE_SECURE=true
```

---

## 👤 Session Variables

Access in tools with `cl.user_session.get()`:

```python
is_authenticated  # bool - True if logged in
username         # str  - Username or "Guest"
user_id          # str  - "USR-XXXXXXXX" or None
email            # str  - User email or None
chat_history     # list - Conversation history
detected_language # str - "en", "fr", "de", etc.
```

---

## 🔐 Authentication Check Pattern

```python
import chainlit as cl

@function_tool
def protected_feature():
    is_auth = cl.user_session.get("is_authenticated", False)
    
    if not is_auth:
        return """🔒 Login required!

        [Login](/signin) | [Register](/register)"""
    
    user_id = cl.user_session.get("user_id")
    # Your protected logic here
```

---

## 📊 Database Schema

```sql
-- users table
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,        -- USR-XXXXXXXX
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,     -- bcrypt
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🛠️ Common Tasks

### Add New Protected Feature
1. Create tool in `src/agent/tools.py`
2. Add authentication check (see pattern above)
3. Add tool to agent in `src/agent/support_agent.py`

### Add New FastAPI Route
Add directly in `app.py` after importing the app:
```python
from chainlit.server import app

@app.get("/your-route")
async def your_handler():
    return {"message": "Hello"}
```

### Change Login Requirement
Edit `.chainlit/config.toml`:
```toml
[project.authentication]
require_login = false  # true to require for ALL features
```

### Add New User Field
1. Update Supabase `users` table
2. Update registration in `app.py` (line ~130)
3. Update auth_callback in `app.py` (line ~250)
4. Access via `cl.user_session.get("field_name")`

---

## 🐛 Debugging

### Enable Verbose Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Session Data
```python
# In any Chainlit handler
print(cl.user_session)  # See all session data
```

### Test Auth Without UI
```python
# In Python shell
import bcrypt
from supabase import create_client

supabase = create_client(url, key)
result = supabase.table("users").select("*").eq("username", "test").execute()
print(result.data)
```

---

## 📝 File Roles

| File | Purpose | Run It? |
|------|---------|---------|
| `app.py` | Main application | ✅ Yes |
| `src/agent/support_agent.py` | Agent definition | No |
| `src/agent/tools.py` | Agent tools | No |
| `src/services/*.py` | Business logic | No |
| `registration.py` | ⚠️ Deprecated | No |
| `run_server.py` | ⚠️ Deprecated | No |

---

## 🎯 Testing Quick Reference

```bash
# Test registration API
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"pass1234"}'

# Check if server is running
curl http://localhost:8000/

# View Supabase users
# (Use Supabase dashboard or SQL editor)
```

---

## ⚡ Performance Tips

1. **Lazy Load Products**: Products loaded on-demand by services
2. **Session Timeout**: 3600s (1 hour) - configurable in `.chainlit/config.toml`
3. **Database Indexing**: Ensure `username` and `email` are indexed
4. **Caching**: Consider caching product data for frequently accessed items

---

## 🔄 Update Workflow

```bash
# 1. Pull changes
git pull

# 2. Update dependencies
uv sync

# 3. Check for migrations
# (Check Supabase for schema changes)

# 4. Restart app
chainlit run app.py
```

---

## 📞 Support

**Email:** info@am-robots.com  
**Phone:** +45 8140 1221  
**Docs:** [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## 🎨 Customization

### Change Theme Colors
Edit `.chainlit/config.toml`:
```toml
[UI.theme.light.primary]
main = "#2563eb"  # Your color here
```

### Update Welcome Message
Edit `app.py` → `on_chat_start()` function

### Modify Registration Page
Edit `REGISTRATION_HTML` constant in `app.py`

---

## ✅ Pre-Deployment Checklist

- [ ] Change `CHAINLIT_AUTH_SECRET` to secure value
- [ ] Set `enable_telemetry = false` in config
- [ ] Update `.env` with production credentials
- [ ] Test all authentication flows
- [ ] Enable HTTPS in production
- [ ] Set up proper error logging
- [ ] Configure CORS in `config.toml`
- [ ] Review Supabase RLS policies

---

*Version: 1.0.0 | Last Updated: January 2, 2026*
