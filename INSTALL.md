# Installation Instructions

## Step-by-Step Terminal Commands

Copy and paste these commands into your terminal to get NEXUS SDK working.

### For Mac/Linux Users

```bash
# 1. Navigate to the SDK directory
cd /Users/garretteaglin/Projects/nexus/packages/nexus-sdk

# 2. Install the SDK with Claude support (most common)
python3 -m pip install -e ".[claude]"

# 3. Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# 4. Test the installation
python3 examples/basic_usage.py
```

### Alternative: Install with All Providers

```bash
# Install with Claude, OpenAI, and Gemini support
python3 -m pip install -e ".[all]"

# Set all API keys
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_AI_API_KEY="..."
```

### Make API Keys Permanent

Add to your shell config so you don't have to set them every time:

```bash
# For zsh (macOS default)
echo 'export ANTHROPIC_API_KEY="sk-ant-your-key-here"' >> ~/.zshrc
source ~/.zshrc

# For bash
echo 'export ANTHROPIC_API_KEY="sk-ant-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

## Quick Verification

Run this command to verify everything works:

```bash
python3 -c "from nexus_sdk import TaskResult; print('✅ NEXUS SDK installed successfully!')"
```

## Get Your API Keys

### Claude (Anthropic)
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Go to "API Keys" section
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-`)

### OpenAI
1. Go to https://platform.openai.com/
2. Sign up or log in
3. Go to "API Keys"
4. Click "Create new secret key"
5. Copy the key (starts with `sk-`)

### Google Gemini
1. Go to https://ai.google.dev/
2. Sign up or log in
3. Click "Get API Key"
4. Copy the key

## What Each Install Option Does

```bash
# Minimal (no AI provider dependencies)
pip install -e .

# Claude only
pip install -e ".[claude]"
# Installs: anthropic>=0.40.0

# OpenAI only
pip install -e ".[openai]"
# Installs: openai>=1.0.0

# Gemini only
pip install -e ".[gemini]"
# Installs: langchain>=0.1.0, langchain-google-genai>=1.0.0

# Everything
pip install -e ".[all]"
# Installs: all of the above

# Development (includes testing tools)
pip install -e ".[dev]"
# Installs: pytest, mypy, ruff
```

## Troubleshooting

### "No module named 'pip'"
```bash
# Install pip first
python3 -m ensurepip --upgrade
```

### "Permission denied"
```bash
# Use --user flag
python3 -m pip install --user -e ".[claude]"
```

### "Command not found: python3"
```bash
# Try python instead
python -m pip install -e ".[claude]"
```

### "ModuleNotFoundError: No module named 'anthropic'"
```bash
# You installed the base SDK without provider extras
# Reinstall with the provider you want:
python3 -m pip install -e ".[claude]"
```

### API Key Not Found
```bash
# Check if it's set
echo $ANTHROPIC_API_KEY

# If empty, set it again
export ANTHROPIC_API_KEY="sk-ant-your-actual-key"
```

## Next Steps

Once installed, try:

1. **Run the basic example:**
   ```bash
   python3 examples/basic_usage.py
   ```

2. **Run the cost tracking example:**
   ```bash
   python3 examples/cost_tracking.py
   ```

3. **Read the quick start guide:**
   ```bash
   cat QUICKSTART.md
   ```

4. **Explore the code:**
   ```bash
   # View provider implementations
   ls -la nexus_sdk/providers/

   # View cost tracking
   ls -la nexus_sdk/cost/
   ```

## Uninstall

If you need to uninstall:

```bash
pip uninstall nexus-agent-sdk
```

## Full Development Setup

For contributors who want to develop the SDK:

```bash
# 1. Install with all extras including dev tools
python3 -m pip install -e ".[all,dev]"

# 2. Run type checking
python3 -m mypy nexus_sdk/

# 3. Run linting
python3 -m ruff check nexus_sdk/

# 4. Run tests (once test suite exists)
python3 -m pytest tests/
```

## System Requirements

- **Python:** 3.11 or higher
- **OS:** macOS, Linux, or Windows (WSL recommended)
- **RAM:** 2GB minimum
- **Disk:** 100MB for SDK + dependencies

## Getting Help

- Issues: https://github.com/nexus/nexus-sdk/issues
- Docs: See README.md and QUICKSTART.md
- Examples: Browse `examples/` directory
