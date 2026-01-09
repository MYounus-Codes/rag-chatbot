"""
Custom Registration Server for Chainlit App
============================================
Serves a registration page before redirecting to the main Chainlit app.
"""

import os
import uuid
import bcrypt
from datetime import datetime
from aiohttp import web
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Registration HTML Page
REGISTRATION_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - AM Robots Support</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #1e40af 100%);
            min-height: 100vh;
        }
        .glass {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
        }
        .input-focus:focus {
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
        }
        .btn-primary {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            transition: all 0.3s ease;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3);
        }
        .animate-fade-in {
            animation: fadeIn 0.5s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body class="flex items-center justify-center p-4">
    <div class="w-full max-w-md">
        <!-- Logo/Header -->
        <div class="text-center mb-8 animate-fade-in">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-white rounded-2xl shadow-lg mb-4">
                <svg class="w-10 h-10 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path>
                </svg>
            </div>
            <h1 class="text-3xl font-bold text-white">AM Robots</h1>
            <p class="text-blue-200 mt-2">Support</p>
        </div>

        <!-- Registration Form -->
        <div class="glass rounded-2xl shadow-2xl p-8 animate-fade-in">
            <h2 class="text-2xl font-bold text-gray-800 mb-6 text-center">Create Your Account</h2>
            
            <form id="registerForm" class="space-y-5">
                <!-- Username -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Username</label>
                    <input 
                        type="text" 
                        id="username" 
                        name="username" 
                        required
                        class="w-full px-4 py-3 border border-gray-300 rounded-lg input-focus outline-none transition-all"
                        placeholder="Enter your username"
                    >
                </div>

                <!-- Email -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                    <input 
                        type="email" 
                        id="email" 
                        name="email" 
                        required
                        class="w-full px-4 py-3 border border-gray-300 rounded-lg input-focus outline-none transition-all"
                        placeholder="your.email@example.com"
                    >
                </div>

                <!-- Password -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Password</label>
                    <input 
                        type="password" 
                        id="password" 
                        name="password" 
                        required
                        minlength="8"
                        class="w-full px-4 py-3 border border-gray-300 rounded-lg input-focus outline-none transition-all"
                        placeholder="Minimum 8 characters"
                    >
                </div>

                <!-- Confirm Password -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Confirm Password</label>
                    <input 
                        type="password" 
                        id="confirmPassword" 
                        name="confirmPassword" 
                        required
                        class="w-full px-4 py-3 border border-gray-300 rounded-lg input-focus outline-none transition-all"
                        placeholder="Confirm your password"
                    >
                </div>

                <!-- Error Message -->
                <div id="errorMsg" class="hidden bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg text-sm"></div>

                <!-- Success Message -->
                <div id="successMsg" class="hidden bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg text-sm"></div>

                <!-- Submit Button -->
                <button 
                    type="submit" 
                    id="submitBtn"
                    class="w-full btn-primary text-white font-semibold py-3 px-4 rounded-lg"
                >
                    Create Account
                </button>
            </form>

            <!-- Login Link -->
            <div class="mt-6 text-center">
                <p class="text-gray-600">
                    Already have an account? 
                    <a href="http://localhost:8000/login" class="text-blue-600 hover:text-blue-800 font-medium">Sign In</a>
                </p>
            </div>
        </div>

        <!-- Footer -->
        <p class="text-center text-blue-200 text-sm mt-6">
            © 2025 TechManufacture Pro. All rights reserved.
        </p>
    </div>

    <script>
        document.getElementById('registerForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const username = document.getElementById('username').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            const errorMsg = document.getElementById('errorMsg');
            const successMsg = document.getElementById('successMsg');
            const submitBtn = document.getElementById('submitBtn');
            
            // Hide messages
            errorMsg.classList.add('hidden');
            successMsg.classList.add('hidden');
            
            // Validate passwords match
            if (password !== confirmPassword) {
                errorMsg.textContent = 'Passwords do not match!';
                errorMsg.classList.remove('hidden');
                return;
            }
            
            // Validate password length
            if (password.length < 8) {
                errorMsg.textContent = 'Password must be at least 8 characters!';
                errorMsg.classList.remove('hidden');
                return;
            }
            
            // Disable button and show loading
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating Account...';
            
            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ username, email, password })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    successMsg.textContent = 'Account created successfully! Redirecting to login...';
                    successMsg.classList.remove('hidden');
                    
                    // Redirect to Chainlit login after 2 seconds
                    setTimeout(() => {
                        window.location.href = 'http://localhost:8000/login';
                    }, 2000);
                } else {
                    errorMsg.textContent = data.error || 'Registration failed. Please try again.';
                    errorMsg.classList.remove('hidden');
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Create Account';
                }
            } catch (error) {
                errorMsg.textContent = 'Network error. Please try again.';
                errorMsg.classList.remove('hidden');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Create Account';
            }
        });
    </script>
</body>
</html>
"""


async def handle_register_page(request):
    """Serve the registration HTML page."""
    return web.Response(text=REGISTRATION_HTML, content_type='text/html')


async def handle_register_api(request):
    """Handle registration API request."""
    try:
        data = await request.json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # Validate input
        if not username or not email or not password:
            return web.json_response({'error': 'All fields are required'}, status=400)
        
        if len(password) < 8:
            return web.json_response({'error': 'Password must be at least 8 characters'}, status=400)
        
        # Check if username already exists
        existing_user = supabase.table("users").select("*").eq("username", username).execute()
        if existing_user.data:
            return web.json_response({'error': 'Username already exists'}, status=400)
        
        # Check if email already exists
        existing_email = supabase.table("users").select("*").eq("email", email).execute()
        if existing_email.data:
            return web.json_response({'error': 'Email already registered'}, status=400)
        
        # Generate unique user ID
        user_id = f"USR-{uuid.uuid4().hex[:8].upper()}"
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        # Save user to Supabase
        user_data = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        result = supabase.table("users").insert(user_data).execute()
        
        if result.data:
            return web.json_response({
                'success': True,
                'message': 'Registration successful',
                'user_id': user_id
            })
        else:
            return web.json_response({'error': 'Failed to create account'}, status=500)
            
    except Exception as e:
        print(f"Registration error: {e}")
        return web.json_response({'error': 'An error occurred during registration'}, status=500)


async def handle_redirect_to_chat(request):
    """Redirect root to registration page."""
    raise web.HTTPFound('/register')


def create_registration_app():
    """Create the registration web application."""
    app = web.Application()
    app.router.add_get('/', handle_redirect_to_chat)
    app.router.add_get('/register', handle_register_page)
    app.router.add_post('/api/register', handle_register_api)
    return app


if __name__ == '__main__':
    app = create_registration_app()
    web.run_app(app, host='localhost', port=8001)
