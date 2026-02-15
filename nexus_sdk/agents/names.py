"""
Diverse agent names for NEXUS SDK.

Balanced gender distribution and culturally diverse names.
"""

import random

# Agent names organized by role
AGENT_NAMES = {
    "vp_engineering": [
        {"name": "Marcus Johnson", "pronouns": "he/him"},
        {"name": "Priya Patel", "pronouns": "she/her"},
        {"name": "James Rodriguez", "pronouns": "he/him"},
        {"name": "Sarah Chen", "pronouns": "she/her"},
    ],
    "senior_engineer": [
        {"name": "Alex Kim", "pronouns": "they/them"},
        {"name": "Maya Thompson", "pronouns": "she/her"},
        {"name": "David Okonkwo", "pronouns": "he/him"},
        {"name": "Elena Popov", "pronouns": "she/her"},
        {"name": "Jordan Martinez", "pronouns": "they/them"},
        {"name": "Lisa Zhang", "pronouns": "she/her"},
    ],
    "frontend_engineer": [
        {"name": "Derek Williams", "pronouns": "he/him"},
        {"name": "Aisha Hassan", "pronouns": "she/her"},
        {"name": "Chris Anderson", "pronouns": "they/them"},
        {"name": "Nina Kowalski", "pronouns": "she/her"},
    ],
    "backend_engineer": [
        {"name": "Marcus Johnson", "pronouns": "he/him"},
        {"name": "Fatima Al-Rashid", "pronouns": "she/her"},
        {"name": "Raj Sharma", "pronouns": "he/him"},
        {"name": "Taylor Chen", "pronouns": "they/them"},
    ],
    "qa_lead": [
        {"name": "Priya Gupta", "pronouns": "she/her"},
        {"name": "Michael O'Brien", "pronouns": "he/him"},
        {"name": "Sam Rivera", "pronouns": "they/them"},
        {"name": "Kenji Tanaka", "pronouns": "he/him"},
    ],
    "security_engineer": [
        {"name": "Sofia Andersson", "pronouns": "she/her"},
        {"name": "Jamal Washington", "pronouns": "he/him"},
        {"name": "Riley Park", "pronouns": "they/them"},
        {"name": "Yuki Nakamura", "pronouns": "she/her"},
    ],
    "architect": [
        {"name": "Dr. Maria Santos", "pronouns": "she/her"},
        {"name": "Dr. Ahmed Hassan", "pronouns": "he/him"},
        {"name": "Dr. Sam Lee", "pronouns": "they/them"},
    ],
    "product_manager": [
        {"name": "Jessica Wright", "pronouns": "she/her"},
        {"name": "Omar Khan", "pronouns": "he/him"},
        {"name": "Casey Thompson", "pronouns": "they/them"},
    ],
    "designer": [
        {"name": "Luna Morales", "pronouns": "she/her"},
        {"name": "Ethan Park", "pronouns": "he/him"},
        {"name": "Alex Zhang", "pronouns": "they/them"},
        {"name": "Sophia Nguyen", "pronouns": "she/her"},
    ],
}


def get_agent_name(role: str, seed: int | None = None) -> dict[str, str]:
    """Get a random agent name for a role.

    Args:
        role: Agent role (e.g., "senior_engineer", "qa_lead")
        seed: Optional seed for reproducible randomness

    Returns:
        Dict with 'name' and 'pronouns' keys

    Example:
        >>> get_agent_name("senior_engineer")
        {'name': 'Maya Thompson', 'pronouns': 'she/her'}
    """
    if seed is not None:
        random.seed(seed)

    role_names = AGENT_NAMES.get(role, AGENT_NAMES["senior_engineer"])
    return random.choice(role_names)


def get_team_names(roles: list[str], seed: int | None = None) -> dict[str, dict[str, str]]:
    """Get a full team of diverse agent names.

    Args:
        roles: List of role names
        seed: Optional seed for reproducible randomness

    Returns:
        Dict mapping role to agent info

    Example:
        >>> get_team_names(["vp_engineering", "senior_engineer", "qa_lead"])
        {
            "vp_engineering": {"name": "Marcus Johnson", "pronouns": "he/him"},
            "senior_engineer": {"name": "Alex Kim", "pronouns": "they/them"},
            "qa_lead": {"name": "Priya Gupta", "pronouns": "she/her"}
        }
    """
    if seed is not None:
        random.seed(seed)

    return {role: get_agent_name(role) for role in roles}
