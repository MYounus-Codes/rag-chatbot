# Testing Checklist - AM ROBOTS Support Chatbot

## Pre-Flight Checks

- [ ] `.env` file configured with all required variables
  - [ ] `SUPABASE_URL`
  - [ ] `SUPABASE_KEY`
  - [ ] `CHAINLIT_AUTH_SECRET`
  - [ ] `OPENAI_API_KEY`
  
- [ ] Dependencies installed: `uv sync`
- [ ] Supabase `users` table exists and is accessible

---

## Test 1: Application Startup ✅

**Command:**
```bash
chainlit run app.py
```

**Expected Results:**
- [ ] Server starts without errors
- [ ] Console shows: "Chainlit: Your app is available at http://localhost:8000"
- [ ] No port conflicts
- [ ] No import errors

**If this fails:**
- Check console for error messages
- Verify all imports are available
- Run: `python -m py_compile app.py`

---

## Test 2: Guest Access (No Login) 🌐

**Steps:**
1. Visit: `http://localhost:8000`
2. If prompted for login, click "Continue as Guest" or append `?no_auth=true`
3. Send message: "What products do you have?"

**Expected Results:**
- [ ] Welcome message shows "Welcome to AM ROBOTS Support!"
- [ ] Quick action buttons appear
- [ ] Can send messages immediately
- [ ] Receives product information
- [ ] No errors in browser console

**User Session Should Have:**
- `is_authenticated: false`
- `username: "Guest"`
- `user_id: null`

---

## Test 3: Registration Page 📝

**Steps:**
1. Visit: `http://localhost:8000/register`
2. Fill in registration form:
   - Username: `testuser` (or your choice)
   - Email: `test@example.com`
   - Password: `testpass123`
   - Confirm Password: `testpass123`
3. Click "Create Account"

**Expected Results:**
- [ ] Registration page loads with AM ROBOTS branding
- [ ] Form validation works (try mismatched passwords)
- [ ] Success message: "Account created successfully!"
- [ ] Redirects to login page after 2 seconds
- [ ] User created in Supabase `users` table
- [ ] Password is bcrypt hashed in database

**Check Supabase:**
```sql
SELECT user_id, username, email, created_at 
FROM users 
WHERE username = 'testuser';
```

---

## Test 4: Login Flow 🔐

**Steps:**
1. Visit: `http://localhost:8000`
2. Click "Login" (if not automatically shown)
3. Enter credentials from Test 3
4. Click "Sign In"

**Expected Results:**
- [ ] Login successful
- [ ] Welcome message shows "Welcome back, [username]!"
- [ ] User session contains:
  - `is_authenticated: true`
  - `username: "testuser"`
  - `user_id: "USR-XXXXXXXX"`
  - `email: "test@example.com"`

---

## Test 5: Authenticated Product Browsing 🛒

**Steps:**
1. While logged in, send: "Tell me about STORM products"
2. Send: "What accessories do you have?"

**Expected Results:**
- [ ] Receives detailed product information
- [ ] Same functionality as guest mode
- [ ] No authentication errors

---

## Test 6: Support Case Submission (Guest - Should Fail) 🚫

**Steps:**
1. Logout or open incognito window
2. Visit: `http://localhost:8000` as guest
3. Send: "I want to submit a support case"

**Expected Results:**
- [ ] Bot responds with "🔒 Login Required"
- [ ] Message includes link to `/` (login)
- [ ] Message includes link to `/register`
- [ ] Explains why login is needed
- [ ] No support case is actually submitted

---

## Test 7: Support Case Submission (Logged In - Should Work) ✅

**Steps:**
1. Ensure you're logged in (Test 4)
2. Send: "I need to submit a support request"
3. Bot should prepare the request
4. View the prepared case details

**Expected Results:**
- [ ] Bot shows "✅ Support Request Ready for Submission"
- [ ] Shows your username and email
- [ ] Shows case details
- [ ] Asks for confirmation ("Would you like me to submit this case now?")
- [ ] No "Login Required" message

**Session Data Should Include:**
- User's email for support case
- User's ID for tracking
- Username for personalization

---

## Test 8: API Registration Endpoint 🔧

**Using curl or Postman:**
```bash
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "apiuser",
    "email": "api@example.com",
    "password": "password123"
  }'
```

**Expected Results:**
- [ ] Status: 200 OK
- [ ] Response: `{"success": true, "message": "Registration successful", "user_id": "USR-..."}`
- [ ] User created in Supabase

**Error Cases to Test:**
```bash
# Duplicate username
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username": "apiuser", "email": "new@example.com", "password": "pass123"}'
# Expected: 400 - "Username already exists"

# Short password
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username": "newuser", "email": "new@example.com", "password": "123"}'
# Expected: 400 - "Password must be at least 8 characters"
```

---

## Test 9: Session Persistence 🔄

**Steps:**
1. Login to the application
2. Chat for a few messages
3. Refresh the browser page
4. Continue chatting

**Expected Results:**
- [ ] Session maintained after refresh
- [ ] Still shows as logged in
- [ ] Username still displayed
- [ ] Chat history may or may not persist (depends on Chainlit config)

---

## Test 10: Multiple Users 👥

**Steps:**
1. Register two different users
2. Login with User 1 in Chrome
3. Login with User 2 in Firefox/Incognito
4. Both users chat simultaneously

**Expected Results:**
- [ ] Both users can chat independently
- [ ] Sessions don't interfere with each other
- [ ] Each sees their own username
- [ ] Support cases use correct user info

---

## Test 11: Login Errors 🚨

**Test Invalid Credentials:**
1. Try login with wrong password
2. Try login with non-existent username

**Expected Results:**
- [ ] Login fails gracefully
- [ ] Error message shown
- [ ] No system errors/crashes
- [ ] User can try again

---

## Test 12: UI/UX Checks 🎨

**Visit Each Page:**
- [ ] `/` - Main chat interface loads correctly
- [ ] `/register` - Registration page styled properly
- [ ] Mobile responsive (test on phone or resize browser)
- [ ] Quick action buttons work
- [ ] Links are clickable and correct

---

## Test 13: Browser Console 🔍

**Check for Errors:**
1. Open browser DevTools (F12)
2. Go to Console tab
3. Use the application (guest + logged in)

**Expected Results:**
- [ ] No JavaScript errors
- [ ] No 404 errors for resources
- [ ] No CORS errors
- [ ] API calls succeed (Network tab)

---

## Test 14: Environment Configuration 🔧

**Test Missing Config:**
1. Comment out `CHAINLIT_AUTH_SECRET` in `.env`
2. Restart app

**Expected Results:**
- [ ] App should handle gracefully
- [ ] Clear error message if required
- [ ] Or uses default value

---

## Performance Tests 🚀

**Load Testing (Optional):**
- [ ] Can handle multiple simultaneous chats
- [ ] Registration doesn't slow down under load
- [ ] Database queries are efficient

---

## Security Tests 🔒

**Password Security:**
- [ ] Passwords hashed with bcrypt in database
- [ ] No plain text passwords stored
- [ ] Login attempts validate correctly

**SQL Injection:**
- [ ] Try SQL injection in username: `' OR '1'='1`
- [ ] Should be handled safely by Supabase client

**XSS Prevention:**
- [ ] Try HTML/JS in chat: `<script>alert('xss')</script>`
- [ ] Should be sanitized/escaped

---

## Cleanup 🧹

**After Testing:**
- [ ] Remove test users from database (optional)
- [ ] Check logs for any warnings
- [ ] Document any issues found
- [ ] Update `.env.example` if needed

---

## Known Limitations

Document any known issues here:
- [ ] ...
- [ ] ...

---

## Success Criteria ✅

For production readiness, all tests marked with ✅ must pass:
- ✅ Single command startup
- ✅ Guest access works
- ✅ Registration works
- ✅ Login/logout works
- ✅ Auth gate for support cases
- ✅ No security vulnerabilities
- ✅ Error handling is graceful

---

## Test Results

**Date Tested:** _________________  
**Tested By:** _________________  
**Version:** 1.0.0

**Overall Status:** [ ] Pass [ ] Fail [ ] Needs Work

**Notes:**
```
[Add your test results and observations here]
```

---

*For detailed setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md)*
