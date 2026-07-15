from pathlib import Path

PROMPTS_DIR = Path("prompts")


def load_system_prompt(user: str = "serina") -> str:
    lcp_path = PROMPTS_DIR / "lcp.md"
    user_path = PROMPTS_DIR / f"{user}.md"

    lcp = lcp_path.read_text()
    user_context = user_path.read_text()

    return f"{lcp}\n\n---\n\n{user_context}"
