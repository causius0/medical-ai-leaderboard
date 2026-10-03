# Mobile Setup Guide

## Quick Start for Claude Code Mobile

To use this repo on mobile, you need to create a `.env` file with your API credentials.

### Step 1: Create .env file

In the repo root, create `.env` with:

```bash
# Required for OpenRouter API
OPENROUTER_API_KEY=your_key_here

# Optional: Email credentials (if using email features)
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
SESSION_SECRET=development_secret_change_in_production

# Optional: Supabase (if using database)
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### Step 2: Get your API Keys

**OpenRouter API Key:**
1. Go to https://openrouter.ai/
2. Sign up/login
3. Get your API key from settings
4. Add to `.env`

**Supabase (Optional):**
1. Go to https://supabase.com/
2. Create project
3. Get credentials from project settings

### Step 3: Verify Setup

Run this command to verify:
```bash
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✓ .env loaded' if os.getenv('OPENROUTER_API_KEY') else '✗ Missing OPENROUTER_API_KEY')"
```

## Important Notes

- **NEVER commit .env** - It's in .gitignore for security
- **Repo is PRIVATE** - But still don't commit secrets
- **Copy .env manually** - When setting up on new devices

## Data Files

The following data files are NOT in git (security):
- `data/ssm_questions_with_solution.json` - Contains correct answers

You'll need to copy these manually from your development machine to mobile if needed for evaluation.

## Troubleshooting

**Error: OPENROUTER_API_KEY not found**
→ Create `.env` file in repo root with your key

**Error: Module 'dotenv' not found**
→ Install: `pip install python-dotenv`
