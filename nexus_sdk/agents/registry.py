"""Agent registry for managing and executing tasks with multiple agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nexus_sdk.types import TaskResult

if TYPE_CHECKING:
    from nexus_sdk.providers.base import ModelProvider


class AgentRegistry:
    """Registry for managing agents and routing tasks to providers.

    Example:
        >>> from nexus_sdk import AgentRegistry
        >>> from nexus_sdk.providers.claude import ClaudeProvider
        >>>
        >>> registry = AgentRegistry(provider=ClaudeProvider(api_key="..."))
        >>> agent = registry.register(
        ...     id="engineer",
        ...     name="Alex Kim",
        ...     role="Senior Engineer",
        ...     model="sonnet"
        ... )
        >>> result = await agent.execute("Implement user auth")
    """

    def __init__(self, provider: ModelProvider, cost_tracking: bool = True):
        """Initialize agent registry.

        Args:
            provider: Model provider (Claude, OpenAI, Gemini, etc.)
            cost_tracking: Enable cost tracking (default: True)
        """
        self.provider = provider
        self.cost_tracking = cost_tracking
        self._agents: dict[str, Agent] = {}

    def register(
        self,
        id: str,
        name: str,
        role: str,
        model: str = "sonnet",
        system_prompt: str = "",
        tools: list[str] | None = None,
    ) -> Agent:
        """Register a new agent.

        Args:
            id: Unique agent identifier
            name: Agent's name (use get_agent_name() for diverse names)
            role: Agent's role description
            model: Model tier (opus/sonnet/haiku or provider-specific)
            system_prompt: Optional system prompt for agent
            tools: Optional list of tool names agent can use

        Returns:
            Agent instance
        """
        agent = Agent(
            id=id,
            name=name,
            role=role,
            model=model,
            system_prompt=system_prompt,
            tools=tools or [],
            provider=self.provider,
        )
        self._agents[id] = agent
        return agent

    def get(self, agent_id: str) -> Agent | None:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    async def execute(self, agent_id: str, task: str) -> TaskResult:
        """Execute a task with a specific agent.

        Args:
            agent_id: ID of agent to execute task
            task: Task description

        Returns:
            TaskResult with execution details and cost
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return TaskResult(
                status="error",
                output=f"Agent '{agent_id}' not found",
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
            )
        return await agent.execute(task)


class Agent:
    """Individual agent that can execute tasks using a model provider."""

    def __init__(
        self,
        id: str,
        name: str,
        role: str,
        model: str,
        system_prompt: str,
        tools: list[str],
        provider: ModelProvider,
    ):
        self.id = id
        self.name = name
        self.role = role
        self.model = model
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.tools = tools
        self.provider = provider

    def _default_system_prompt(self) -> str:
        """Generate default system prompt from role."""
        return (
            f"You are {self.name}, a {self.role}. "
            "Execute tasks with high quality and attention to detail."
        )

    async def execute(self, task: str) -> TaskResult:
        """Execute a task using the configured provider.

        Args:
            task: Task description to execute

        Returns:
            TaskResult with execution details
        """
        return await self.provider.execute(
            prompt=task,
            model=self.model,
            system_prompt=self.system_prompt,
        )
