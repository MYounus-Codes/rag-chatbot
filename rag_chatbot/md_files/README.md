# AM ROBOTS Support Chatbot

A production-ready RAG chatbot for AM ROBOTS - Danish manufacturer of robotic lawnmower equipment and accessories.

## 🚀 Quick Start

```bash
# Single command to start everything
chainlit run app.py
```

Visit **http://localhost:8000** - Chat immediately or login for full features!

---

## Tech Stack

- **Chainlit** - Modern chat UI with streaming support
- **OpenAI Agents SDK** - Agent-based interactions with tools
- **Supabase** - User authentication & data storage
- **FastAPI** - Integrated registration endpoints
- **Python 3.12+** - Modern async Python

## Features

- 🎯 **Guest Mode** - Chat without login (browse products, get support)
- 🔐 **Optional Authentication** - Login required only for support case submission
- 📝 **Integrated Registration** - Built-in user registration at `/register`
- 📦 **Product Information** - Retrieval from structured JSON data
- 🌍 **Multi-language Support** - English, French, German, Italian, Spanish, Danish
- 🛡️ **Security Guardrails** - Input/output validation for safe responses
- 💳 **Price Handling** - Redirects to dealer login portal
- ⚡ **Streaming Responses** - Real-time AI responses with fade animations
- 🚀 **Quick Actions** - Pre-configured starter buttons for common queries
- 🧩 **Modular Architecture** - Scalable, maintainable codebase

## Authentication Flow

### Guest Users (No Login)
✅ Browse products  
✅ Get technical support  
✅ Learn about AM ROBOTS  
❌ Submit support cases (login required)

### Registered Users (Logged In)
✅ All guest features  
✅ Submit support case tickets  
✅ Track support requests  
✅ Access user-specific features

## Project Structure

```
rag_chatbot/
├── app.py                    # 🌟 Main application (RUN THIS!)
├── SETUP_GUIDE.md           # 📖 Detailed setup & usage guide
├── chainlit.md              # Chat welcome content
├── pyproject.toml           # Project dependencies
├── .env                     # Environment variables
├── am-robots.json           # Brand information
├── products/                # Product data directory
│   ├── Product Name/
│   │   ├── product.json     # Main product info
│   │   ├── catalogues/      # Multi-language catalogues
│   │   └── manuals/         # Product manuals
│   └── ...
├── .chainlit/
│   └── config.toml          # Chainlit configuration
└── src/                     # Source modules
    ├── core/                # Configuration & constants
    │   ├── config.py
    │   └── constants.py
    ├── services/            # Business logic
    │   ├── product_service.py
    │   └── brand_service.py
    ├── utils/               # Utilities
    │   ├── guardrails.py
    │   └── language.py
    └── agent/               # AI Agent
        ├── tools.py         # Agent tools (with auth checks)
        └── support_agent.py
```

## UI/UX Features

- **Centered Layout:** Welcome message and input box centered for modern feel
- **Quick Starters:** Four action buttons (Browse Products, STORM Tech, Support, Pricing) positioned below input
- **Smooth Animations:** Fade-in effects for messages and hover states for buttons
- **Custom Styling:** Blue/green theme matching AM ROBOTS brand
- **Responsive Design:** Adapts to different screen sizes

## Quick Start

1. **Install dependencies:**
```bash
pip install -e .
# or with uv:
uv sync
```

2. **Set environment variables** (create `.env` file):
```env
OPENROUTER_API_KEY=your_key
PINECONE_API_KEY=your_key
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
```

3. **Run the chatbot:**
```bash
chainlit run app.py
```

4. **Access:** Open http://localhost:8000

## Available Products

- **Robot Mowers:** STORM 2000 | 4000 | 6000 (LDI Technology)
- **Boundary Cable:** Basic (2.7mm), Standard (3.4mm), Premium Safety (3.8mm)
- **Garages:** AM Garage 1, My Robot Home Compact, Navi Home
- **Blades:** For Husqvarna, STIHL, Robomow, Worx, Honda, LUBA, and more
- **Tools:** Cable Tracker, Heat Gun, Wirestripper
- **Connectors & Accessories**

## Key Behaviors

1. **Product Queries:** Returns factual data from `/products` directory
2. **Price Queries:** Redirects to dealer login (https://am-robots.com/login/)
3. **Brand Questions:** Uses `am-robots.json` for company information
4. **Support Requests:** Guides users to submit support cases

## Contact

- **Website:** https://am-robots.com/
- **Email:** info@am-robots.com
- **Phone:** +45 8140 1221
