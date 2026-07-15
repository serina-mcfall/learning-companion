from anthropic import Anthropic
from dotenv import load_dotenv


def main():
    load_dotenv()

    client = Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": "Hi Claude! This is my first call from the LCP project. Please reply with a short Hello and confirm you can hear me.",
            }
        ],
    )

    print(message.content[0].text)


if __name__ == "__main__":
    main()
