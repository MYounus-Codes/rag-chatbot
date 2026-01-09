"""
Combined Server Runner
======================
Runs both the registration server and Chainlit app with a reverse proxy.
"""

import os
import asyncio
import subprocess
import sys
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

# Import registration app
from registration import create_registration_app, REGISTRATION_HTML

CHAINLIT_PORT = 8000
REGISTRATION_PORT = 8001
MAIN_PORT = 8080


async def proxy_to_chainlit(request):
    """Proxy requests to Chainlit."""
    import aiohttp
    
    target_url = f"http://localhost:{CHAINLIT_PORT}{request.path_qs}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(
                method=request.method,
                url=target_url,
                headers=dict(request.headers),
                data=await request.read() if request.can_read_body else None,
            ) as resp:
                body = await resp.read()
                return web.Response(
                    body=body,
                    status=resp.status,
                    headers=dict(resp.headers),
                )
        except Exception as e:
            return web.Response(text=f"Error: {e}", status=502)


async def handle_root(request):
    """Redirect root to registration."""
    raise web.HTTPFound('/register')


async def handle_register_page(request):
    """Serve registration page."""
    return web.Response(text=REGISTRATION_HTML, content_type='text/html')


async def handle_register_api(request):
    """Handle registration API."""
    from registration import handle_register_api as reg_handler
    return await reg_handler(request)


def create_combined_app():
    """Create combined web application."""
    app = web.Application()
    
    # Registration routes
    app.router.add_get('/', handle_root)
    app.router.add_get('/register', handle_register_page)
    app.router.add_post('/api/register', handle_register_api)
    
    # Proxy everything else to Chainlit
    app.router.add_route('*', '/chat{path:.*}', proxy_to_chainlit)
    app.router.add_route('*', '/{path:.*}', proxy_to_chainlit)
    
    return app


def run_servers():
    """Run all servers."""
    print("="*50)
    print("TechManufacture Pro Support - Starting Services")
    print("="*50)
    print()
    
    # Start Chainlit in background
    print(f"Starting Chainlit on port {CHAINLIT_PORT}...")
    chainlit_process = subprocess.Popen(
        [sys.executable, "-m", "chainlit", "run", "app.py", "--port", str(CHAINLIT_PORT)],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    print(f"Starting combined server on port {MAIN_PORT}...")
    print()
    print(f"🌐 Open http://localhost:{MAIN_PORT} in your browser")
    print(f"   - /register - User registration")
    print(f"   - /chat - Chainlit chat interface")
    print()
    
    try:
        # Run combined app
        app = create_combined_app()
        web.run_app(app, host='0.0.0.0', port=MAIN_PORT)
    finally:
        chainlit_process.terminate()


if __name__ == '__main__':
    run_servers()
