"""
Test script to verify SMTP email functionality
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")

print("=" * 60)
print("🧪 Testing SMTP Email Configuration")
print("=" * 60)
print(f"SMTP Host: {SMTP_HOST}")
print(f"SMTP Port: {SMTP_PORT}")
print(f"SMTP User: {SMTP_USER}")
print(f"From Email: {SMTP_FROM_EMAIL}")
print("=" * 60)

# Test email
test_recipient = SMTP_USER  # Send to self for testing

try:
    print("\n📧 Creating test email...")
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM_EMAIL or SMTP_USER
    msg["To"] = test_recipient
    msg["Subject"] = "🧪 Test Email - Support Case System"
    
    body = """
    <html><body style="font-family: Arial, sans-serif;">
        <h2 style="color: #2563eb;">Test Email - Support Case System</h2>
        <p>This is a test email from the AM ROBOTS support case system.</p>
        <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px;">
            <h3 style="color: #059669;">System Status:</h3>
            <p>✅ SMTP configuration is working correctly!</p>
        </div>
        <p>Best regards,<br>AM ROBOTS Support Team</p>
    </body></html>
    """
    
    msg.attach(MIMEText(body, "html"))
    
    print("🔌 Connecting to SMTP server...")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        print("🔐 Starting TLS...")
        server.starttls()
        
        print(f"🔑 Logging in as {SMTP_USER}...")
        server.login(SMTP_USER, SMTP_PASSWORD)
        
        print(f"📤 Sending test email to {test_recipient}...")
        server.send_message(msg)
    
    print("\n" + "=" * 60)
    print("✅ SUCCESS! Email sent successfully!")
    print("=" * 60)
    print(f"📬 Check your inbox: {test_recipient}")
    print("=" * 60)
    
except smtplib.SMTPAuthenticationError as e:
    print("\n" + "=" * 60)
    print("❌ AUTHENTICATION FAILED!")
    print("=" * 60)
    print(f"Error: {e}")
    print("\n💡 Troubleshooting:")
    print("   1. Check SMTP_USER and SMTP_PASSWORD in .env")
    print("   2. For Gmail, enable 2FA and use App Password")
    print("   3. Check 'Less secure app access' settings")
    print("=" * 60)
    
except smtplib.SMTPConnectError as e:
    print("\n" + "=" * 60)
    print("❌ CONNECTION FAILED!")
    print("=" * 60)
    print(f"Error: {e}")
    print("\n💡 Troubleshooting:")
    print("   1. Check SMTP_HOST and SMTP_PORT in .env")
    print("   2. Verify internet connection")
    print("   3. Check firewall settings")
    print("=" * 60)
    
except Exception as e:
    print("\n" + "=" * 60)
    print("❌ ERROR!")
    print("=" * 60)
    print(f"Error: {e}")
    print("=" * 60)
