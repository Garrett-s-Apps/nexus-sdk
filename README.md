# NEXUS Agent SDK

Multi-agent orchestration SDK with swappable AI model providers.

## Features

- **Provider-agnostic**: Use Claude, OpenAI, Gemini, or local models
- **Cost tracking**: Built-in budget enforcement and cost monitoring
- **Agent orchestration**: Hierarchical agent teams with autonomous execution
- **Type-safe**: Full type hints and runtime validation
- **Lightweight**: Zero dependencies for core SDK

## Installation

```bash
# Core SDK (no provider dependencies)
pip install nexus-agent-sdk

# With Claude support
pip install nexus-agent-sdk[claude]

# With OpenAI support
pip install nexus-agent-sdk[openai]

# With Gemini support
pip install nexus-agent-sdk[gemini]

# With all providers
pip install nexus-agent-sdk[all]
```

## Quick Start

```python
from nexus_sdk import AgentRegistry, get_agent_name
from nexus_sdk.providers.claude import ClaudeProvider

# Initialize provider and registry
provider = ClaudeProvider(api_key="your-api-key")
registry = AgentRegistry(provider=provider)

# Get a diverse agent name (balanced gender distribution)
agent_info = get_agent_name("senior_engineer")

# Register an agent
agent = registry.register(
    id="engineer",
    name=agent_info["name"],
    role="Senior Software Engineer",
    model="sonnet",
)

# Execute a task
result = await agent.execute("Implement user authentication")
print(f"{agent_info['name']} ({agent_info['pronouns']}):")
print(f"  Status: {result.status}")
print(f"  Cost: ${result.cost_usd:.6f}")
print(f"  Output: {result.output}")
```

## Examples

See `examples/` directory for:
- `basic_usage.py` - Single agent, single task
- `multi_agent.py` - Full org chart orchestration
- `custom_provider.py` - Implementing custom providers
- `cost_tracking.py` - Budget enforcement
- `provider_swap.py` - Comparing different providers

## API Reference

### Core Classes

#### `AgentRegistry`

Manages agents and routes tasks to model providers.

```python
registry = AgentRegistry(provider=provider, cost_tracking=True)

# Register agents
agent = registry.register(
    id="engineer",
    name="Alex Kim",
    role="Senior Engineer",
    model="sonnet",
    system_prompt="You are a senior engineer...",  # Optional
    tools=["Read", "Write", "Bash"]  # Optional
)

# Execute tasks
result = await registry.execute("engineer", "Build feature X")
```

#### `Agent`

Individual agent that executes tasks using a model provider.

```python
# Created via registry.register()
agent = registry.get("engineer")
result = await agent.execute("Write a function to validate emails")
```

#### `TaskResult`

Unified result type across all providers.

```python
@dataclass
class TaskResult:
    status: str          # "success" or "error"
    output: str          # Model's response
    tokens_in: int       # Input tokens consumed
    tokens_out: int      # Output tokens generated
    cost_usd: float      # Cost in USD
    model: str           # Model used (e.g., "claude-sonnet-4-20250514")
    elapsed_seconds: float  # Execution time
```

### Provider Classes

#### `ClaudeProvider`

Anthropic Claude models (Opus, Sonnet, Haiku).

```python
from nexus_sdk.providers.claude import ClaudeProvider

provider = ClaudeProvider(api_key="sk-ant-...")

# Model tiers
result = await provider.execute(prompt, model="opus")    # Most capable
result = await provider.execute(prompt, model="sonnet")  # Balanced
result = await provider.execute(prompt, model="haiku")   # Fastest/cheapest
```

#### `OpenAIProvider`

OpenAI models (GPT-4, GPT-3.5, o1, etc.).

```python
from nexus_sdk.providers.openai_provider import OpenAIProvider

provider = OpenAIProvider(api_key="sk-...")
result = await provider.execute(prompt, model="gpt-4")
```

#### `GeminiProvider`

Google Gemini models.

```python
from nexus_sdk.providers.gemini import GeminiProvider

provider = GeminiProvider(api_key="...")
result = await provider.execute(prompt, model="gemini-2.5-pro")
```

#### Custom Providers

Implement `ModelProvider` ABC for any AI service:

```python
from nexus_sdk.providers.base import ModelProvider

class MyProvider(ModelProvider):
    async def execute(self, prompt: str, model: str = "default", **kwargs) -> TaskResult:
        # Your implementation
        pass

    def get_pricing(self, model: str) -> dict[str, float]:
        return {"input_per_million": 1.0, "output_per_million": 3.0}

    def list_models(self) -> list[str]:
        return ["model-1", "model-2"]
```

### Helper Functions

#### `get_agent_name(role, seed=None)`

Get a random agent name with diverse representation.

```python
from nexus_sdk import get_agent_name

# Random selection
agent = get_agent_name("senior_engineer")
# {'name': 'Maya Thompson', 'pronouns': 'she/her'}

# Reproducible (with seed)
agent = get_agent_name("senior_engineer", seed=42)
# {'name': 'Lisa Zhang', 'pronouns': 'she/her'}

# Available roles
roles = [
    "vp_engineering",
    "senior_engineer",
    "frontend_engineer",
    "backend_engineer",
    "qa_lead",
    "security_engineer",
    "architect",
    "product_manager",
    "designer"
]
```

**Diversity stats:** 41.7% she/her, 33.3% he/him, 25.0% they/them. Culturally diverse names.

#### `get_team_names(roles, seed=None)`

Get a full team of diverse agent names.

```python
from nexus_sdk import get_team_names

team = get_team_names(["vp_engineering", "senior_engineer", "qa_lead"])
# {
#     "vp_engineering": {"name": "Marcus Johnson", "pronouns": "he/him"},
#     "senior_engineer": {"name": "Alex Kim", "pronouns": "they/them"},
#     "qa_lead": {"name": "Priya Gupta", "pronouns": "she/her"}
# }
```

### Cost Tracking

#### `CostTracker`

Track and enforce budgets.

```python
from nexus_sdk.cost import CostTracker, SQLiteStorage

# In-memory tracking
tracker = CostTracker()

# Persistent tracking
storage = SQLiteStorage("~/.nexus/cost.db")
tracker = CostTracker(storage=storage)

# Set budgets
tracker.set_budget(
    hourly_target=1.00,      # Soft limit per hour
    hourly_hard_cap=2.50,    # Hard limit per hour
    monthly_target=160.00    # Monthly target
)

# Track costs
tracker.record("sonnet", "my_agent", tokens_in=1000, tokens_out=500)

# Check status
if tracker.should_downgrade():
    print(f"⚠️ Approaching budget limit, downgrading to cheaper model")
```

## Environment Variables

```bash
# Model configuration (when using NEXUS server)
export NEXUS_CONVERSATION_MODEL=sonnet      # Default: sonnet
export NEXUS_PLANNING_MODEL=opus            # Default: sonnet
export NEXUS_IMPLEMENTATION_MODEL=sonnet    # Default: sonnet
export NEXUS_QA_MODEL=haiku                 # Default: haiku

# SDK provider toggle (NEXUS server only)
export NEXUS_USE_SDK_PROVIDERS=1            # 1=SDK, 0=legacy (default: 0)

# Provider API keys
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GOOGLE_API_KEY=...
```

## Testing

```bash
# Install dev dependencies
pip install nexus-agent-sdk[dev]

# Run tests
pytest tests/

# Type checking
mypy nexus_sdk/

# Linting
ruff check nexus_sdk/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and type checking
5. Submit a pull request

## License

MIT
