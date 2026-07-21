import re
import shutil
import textwrap
from pathlib import Path

import anthropic
from anthropic import Anthropic
from dotenv import load_dotenv

from memory import init_db, load_history, save_message
from persona import load_system_prompt

EXIT_COMMANDS = {"/quit", "/exit", "/bye"}
PROJECT_ROOT = Path(__file__).parent
READ_COMMAND = re.compile(r"^/read\s+(.+)$")
BARE_PATH = re.compile(r"^(/\S+)$")


def wrap_lcp(text: str) -> str:
    """Wrap LCP output to a readable width. Only the first non-empty
    line gets the 'LCP: ' prefix; later lines align under it with a
    5-space indent so screen readers parse it as one turn."""
    width = min(72, shutil.get_terminal_size().columns - 2)
    first_wrapper = textwrap.TextWrapper(
        width=width,
        initial_indent="LCP: ",
        subsequent_indent="     ",
    )
    later_wrapper = textwrap.TextWrapper(
        width=width,
        initial_indent="     ",
        subsequent_indent="     ",
    )
    lines = []
    prefix_used = False
    for line in text.split("\n"):
        if not line.strip():
            lines.append("")
        elif not prefix_used:
            lines.append(first_wrapper.fill(line))
            prefix_used = True
        else:
            lines.append(later_wrapper.fill(line))
    return "\n".join(lines)


def handle_read_command(user_input: str, project_root: Path) -> tuple[bool, str | None]:
    """
    Check if user_input is a /read command.

    Returns (is_read_command, message_to_send):
    -Not a /read command: (False, None) - normal flow continues.
    -/read succeeded: (True, formatted_contents) - send to Claude.
    -/read failed: (True, None) - error was printed, skip API call.
    """
    match = READ_COMMAND.match(user_input)
    if not match:
        match = BARE_PATH.match(user_input)
    if not match:
        return False, None

    path_str = match.group(1).strip()

    try:
        path = Path(path_str).expanduser().resolve()
    except (OSError, RuntimeError) as e:
        print(f"\n{wrap_lcp(f'Could not resolve path {path_str!r} - {e}.')}\n")
        return True, None

    if not path.is_relative_to(project_root):
        print(
            f"\n{wrap_lcp(f'I can only read files inside the project. {path} is outside - refusing for safety.')}\n"
        )
        return True, None

    if not path.exists():
        print(f"\n{wrap_lcp(f'File not found: {path}')}\n")
        return True, None

    if not path.is_file():
        print(f"\n{wrap_lcp(f'Not a file (directory?): {path}')}\n")
        return True, None

    try:
        contents = path.read_text()
    except PermissionError:
        print(f"\n{wrap_lcp(f'Permission denied reading {path}.')}\n")
        return True, None
    except UnicodeDecodeError:
        print(f"\n{wrap_lcp(f'Cannot decode {path} as text - is it binary?')}\n")
        return True, None

    message = (
        f"I'm sharing the contents of '{path.name}' for you to review:\n\n"
        f"```\n{contents}\n```"
    )

    return True, message


def chat_loop(client: Anthropic, system_prompt: str) -> None:
    print("LCP is ready. Type your message and press enter.")
    print(
        "Type '/quit', '/exit', or '/bye' to exit the chat. CTRL+C will also exit the chat."
    )

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye Serina. See you next time.")
            break
        if not user_input:
            continue
        if user_input.lower() in EXIT_COMMANDS:
            print("Bye Serina. See you next time.")
            break

        is_read_cmd, message_for_claude = handle_read_command(user_input, PROJECT_ROOT)
        if is_read_cmd and message_for_claude is None:
            continue
        if is_read_cmd:
            user_input = message_for_claude

        history = load_history()
        messages = history + [{"role": "user", "content": user_input}]

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            )

            assistant_reply = response.content[0].text

            save_message("user", user_input)
            save_message("assistant", assistant_reply)

            print(f"\n{wrap_lcp(assistant_reply)}\n")
        except anthropic.AuthenticationError:
            print(
                f"\n{wrap_lcp('The API Key looks invalid. Check your ~/.secrets file.')}\n"
            )
            continue
        except anthropic.RateLimitError:
            print(f"\n{wrap_lcp('Rate Limit hit - wait a moment, then try again.')}\n")
            continue
        except anthropic.APIConnectionError:
            print(
                f"\n{wrap_lcp('API Connection Error - check your internet connection and try again.')}\n"
            )
            continue
        except anthropic.APIError as e:
            message = f"Something went wrong on the API side - {e}. Try again later or type /quit."
            print(f"\n{wrap_lcp(message)}\n")
            continue
        except Exception as e:
            message = f"An unexpected error - {e}. Try again or type /quit."
            print(f"\n{wrap_lcp(message)}\n")
            continue


def main():
    load_dotenv()
    init_db()

    client = Anthropic()
    system_prompt = load_system_prompt()

    chat_loop(client, system_prompt)


if __name__ == "__main__":
    main()
