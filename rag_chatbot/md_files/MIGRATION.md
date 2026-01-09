# Migration Notice

## ⚠️ DEPRECATED FILES

The following files are **no longer needed** and have been replaced by the integrated `app.py`:

### Deprecated Files:
- ❌ `registration.py` - Registration now integrated into `app.py`
- ❌ `run_server.py` - No longer needed (single app startup)
- ⚠️ `main.py` - Legacy file, use `app.py` instead

---

## ✅ NEW WORKFLOW

### Old Way (3 separate processes):
```bash
# Terminal 1
python registration.py

# Terminal 2  
chainlit run main.py

# Terminal 3
python run_server.py
```

### New Way (1 command):
```bash
chainlit run app.py
```

---

## What Changed?

1. **Registration Routes**: Now FastAPI routes in `app.py`
   - `/register` - Registration page
   - `/api/register` - Registration API

2. **Authentication**: Integrated with Chainlit's auth system
   - `@cl.password_auth_callback` handles login
   - `@cl.on_mount` mounts FastAPI routes

3. **Guest Mode**: Users can chat without logging in
   - Login required only for support case submission
   - Configurable via `.chainlit/config.toml`

---

## File Purpose Reference

| File | Status | Purpose |
|------|--------|---------|
| `app.py` | ✅ **USE THIS** | Main application with integrated auth |
| `registration.py` | ❌ Deprecated | Standalone registration server |
| `run_server.py` | ❌ Deprecated | Combined server runner |
| `main.py` | ⚠️ Legacy | Old main file with agents |

---

## Migration Steps

If you were using the old files:

1. **Stop all running processes**
2. **Update dependencies**: `uv sync`
3. **Use new startup command**: `chainlit run app.py`
4. **Update any scripts** that reference old files
5. **(Optional)** Archive old files:
   ```bash
   mkdir archive
   mv registration.py run_server.py archive/
   ```

---

## Benefits of New System

✅ **Single command startup** - No more juggling multiple terminals  
✅ **Port management** - No port conflicts or multiple servers  
✅ **Integrated authentication** - Seamless login/register flow  
✅ **Guest access** - Chat works without login  
✅ **Professional UX** - Consistent user experience  
✅ **Easy deployment** - One app to deploy  

---

## Questions?

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed documentation.

*Last Updated: January 2, 2026*
