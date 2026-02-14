# NEXUS SDK - Quick Start Guide

Get started with NEXUS Agent SDK in 5 minutes.

## Prerequisites

- Python >= 3.11
- An API key for at least one provider (Claude, OpenAI, or Gemini)

## Installation

### 1. Install the SDK

Choose one based on your AI provider:

```bash
# For Claude (Anthropic)
pip install -e ".[claude]"

# For OpenAI
pip install -e ".[openai]"

# For Gemini
pip install -e ".[gemini]"

# For all providers
pip install -e ".[all]"
```

### 2. Set your API key

```bash
# For Claude
export ANTHROPIC_API_KEY="your-api-key-here"

# For OpenAI
export OPENAI_API_KEY="your-api-key-here"

# For Gemini
export GOOGLE_AI_API_KEY="your-api-key-here"
```

**Make it permanent** (add to `~/.zshrc` or `~/.bashrc`):

```bash
echo 'export ANTHROPIC_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Test the installation

```bash
# Run the basic example
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

## Your First Agent

Create a file `my_first_agent.py`:

```python
import asyncio
import os
from nexus_sdk.providers.claude import ClaudeProvider

async def main():
    # Initialize provider
    provider = ClaudeProvider(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Execute a task
    result = await provider.execute(
        prompt="Explain what NEXUS SDK does in one sentence.",
        model="haiku",
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
python3 my_first_agent.py
```

## Cost Tracking Example

Test budget enforcement:

```bash
python3 examples/cost_tracking.py
```

This will show:
- Automatic cost tracking per call
- Budget warnings when you exceed limits
- Automatic model downgrading to save money

## Troubleshooting

### "ModuleNotFoundError: No module named 'anthropic'"

You forgot to install the provider extras:

```bash
pip install -e ".[claude]"  # or [openai] or [gemini]
```

### "ANTHROPIC_API_KEY environment variable not set"

Set your API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "ImportError: cannot import name 'ClaudeProvider'"

Make sure you installed the SDK:

```bash
cd /path/to/nexus/packages/nexus-sdk
pip install -e ".[claude]"
```

### Type errors with mypy

Install dev dependencies:

```bash
pip install -e ".[dev]"
mypy nexus_sdk/
```

## Next Steps

- 📖 Read the full documentation: [README.md](README.md)
- 🔧 Explore provider options: [nexus_sdk/providers/](nexus_sdk/providers/)
- 💰 Learn about cost tracking: [nexus_sdk/cost/](nexus_sdk/cost/)
- 🧪 Run tests: `pytest tests/` (once test suite is added)

## Getting Help

- Check the examples: `examples/*.py`
- Review provider implementations: `nexus_sdk/providers/*.py`
- Read the plan: See main NEXUS repository for full architecture

## What's Next?

Now that you have the SDK working, you can:

1. **Try different providers** - Swap between Claude, OpenAI, and Gemini
2. **Build multi-agent workflows** - Orchestrate teams of AI agents
3. **Enforce budgets** - Never exceed your cost limits
4. **Track everything** - Built-in cost and performance monitoring

Happy building! 🚀
