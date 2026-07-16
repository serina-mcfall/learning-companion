import shutil
import textwrap

import anthropic
from anthropic import Anthropic
from dotenv import load_dotenv

from memory import init_db, load_history, save_message
from persona import load_system_prompt

EXIT_COMMANDS = {"/quit", "/exit", "/bye"}


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
            print(f"\n{wrap_lcp('The API Key looks invalid. Check your ~/.secrets file.')}\n")
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
