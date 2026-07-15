from anthropic import Anthropic
from dotenv import load_dotenv

from memory import init_db, load_history, save_message
from persona import load_system_prompt


def main():
    load_dotenv()
    init_db()

    client = Anthropic()

    system_prompt = load_system_prompt()

    user_input = "Hi Claude! Do you remeber me from earlier?"

    history = load_history()
    messages = history + [{"role": "user", "content": user_input}]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )

    assistant_reply = response.content[0].text

    save_message("user", user_input)
    save_message("assistant", assistant_reply)

    print(assistant_reply)


if __name__ == "__main__":
    main()
