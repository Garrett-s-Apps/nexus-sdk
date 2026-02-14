# 🚀 START HERE - NEXUS SDK

## Copy These Commands Into Your Terminal

### Step 1: Install the SDK

```bash
cd /Users/garretteaglin/Projects/nexus/packages/nexus-sdk
python3 -m pip install -e ".[claude]"
```

**What this does:** Installs NEXUS SDK with Claude (Anthropic) support.

---

### Step 2: Get Your API Key

1. Go to **https://console.anthropic.com/**
2. Sign up or log in
3. Click **"API Keys"** in the left sidebar
4. Click **"Create Key"**
5. Copy the key (starts with `sk-ant-`)

---

### Step 3: Set Your API Key

```bash
export ANTHROPIC_API_KEY="sk-ant-paste-your-key-here"
```

**Make it permanent** (so you don't have to set it every time):

```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-paste-your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

---

### Step 4: Test It Works

```bash
python3 -c "from nexus_sdk import TaskResult; print('✅ NEXUS SDK installed!')"
```

**Expected output:**
```
✅ NEXUS SDK installed!
```

---

### Step 5: Run Your First Example

```bash
python3 examples/basic_usage.py
```

**Expected output:**
```
Executing task with Claude...

Status: success
Model: claude-haiku-4-5-20251001
Tokens: 45 in, 234 out
Cost: $0.000304
Time: 1.23s

Output:
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True
```

---

### Step 6: Try Cost Tracking

```bash
python3 examples/cost_tracking.py
```

This will show you:
- ✅ Automatic cost tracking per API call
- 💰 Budget warnings when you exceed limits
- ⚠️ Automatic model downgrading to save money
- 📊 Session cost summary

---

## 🎯 That's It!

You now have NEXUS SDK working. Here's what you can do:

### Create Your First Agent

Create a file called `my_agent.py`:

```python
import asyncio
import os
from nexus_sdk.providers.claude import ClaudeProvider

async def main():
    # Initialize provider
    provider = ClaudeProvider(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Execute a task
    result = await provider.execute(
        prompt="Explain NEXUS SDK in one sentence.",
        model="haiku",  # Fast and cheap!
    )

    # Display result
    if result.succeeded:
        print(f"✅ {result.output}")
        print(f"💰 Cost: ${result.cost_usd:.6f}")
    else:
        print(f"❌ Error: {result.error_detail}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python3 my_agent.py
```

---

## 🔄 Want to Try Different AI Providers?

### OpenAI (GPT-4, o3)

```bash
# Install OpenAI support
python3 -m pip install -e ".[openai]"

# Set API key
export OPENAI_API_KEY="sk-your-openai-key"

# Use in code
from nexus_sdk.providers.openai_provider import OpenAIProvider
provider = OpenAIProvider(api_key=os.environ["OPENAI_API_KEY"])
```

### Google Gemini

```bash
# Install Gemini support
python3 -m pip install -e ".[gemini]"

# Set API key
export GOOGLE_AI_API_KEY="your-gemini-key"

# Use in code
from nexus_sdk.providers.gemini import GeminiProvider
provider = GeminiProvider(api_key=os.environ["GOOGLE_AI_API_KEY"])
```

### All Providers

```bash
# Install everything at once
python3 -m pip install -e ".[all]"
```

---

## 🆘 Troubleshooting

### "ModuleNotFoundError: No module named 'anthropic'"

You forgot the `[claude]` part. Run:
```bash
python3 -m pip install -e ".[claude]"
```

### "ANTHROPIC_API_KEY environment variable not set"

Run:
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

### "Command not found: python3"

Try `python` instead:
```bash
python -m pip install -e ".[claude]"
```

### Still having issues?

1. Check `INSTALL.md` for detailed troubleshooting
2. Read `QUICKSTART.md` for more examples
3. Browse `examples/` directory

---

## 📚 Documentation

- **START_HERE.md** ← You are here
- **QUICKSTART.md** - 5-minute getting started guide
- **INSTALL.md** - Detailed installation troubleshooting
- **README.md** - Full project documentation
- **SETUP_COMPLETE.md** - Phase 1 completion summary (for developers)

---

## ✅ Quick Verification Checklist

Run these commands to verify everything works:

```bash
# 1. Check SDK imports
python3 -c "from nexus_sdk import TaskResult; print('✅ Imports work')"

# 2. Check API key is set
echo $ANTHROPIC_API_KEY
# Should print: sk-ant-...

# 3. Run basic example
python3 examples/basic_usage.py
# Should execute successfully and show output

# 4. Run cost tracking
python3 examples/cost_tracking.py
# Should show cost enforcement in action
```

If all 4 pass: **🎉 You're ready to build with NEXUS SDK!**

---

## 🚀 Next Steps

1. **Explore examples:** Browse `examples/` directory
2. **Read the docs:** Check out `README.md` and `QUICKSTART.md`
3. **Build something:** Create your own multi-agent workflow
4. **Swap providers:** Try Claude, OpenAI, and Gemini
5. **Track costs:** Never exceed your budget with built-in enforcement

---

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| Install SDK | `python3 -m pip install -e ".[claude]"` |
| Set API key | `export ANTHROPIC_API_KEY="sk-ant-..."` |
| Test install | `python3 -c "from nexus_sdk import TaskResult; print('✅')"` |
| Run example | `python3 examples/basic_usage.py` |
| Uninstall | `pip uninstall nexus-agent-sdk` |

---

**Need help?** Check `INSTALL.md` for detailed troubleshooting.

**Want to learn more?** Read `QUICKSTART.md` for a 5-minute tutorial.

**Ready to build?** Start with `examples/basic_usage.py` and modify it!
