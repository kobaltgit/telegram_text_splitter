# Telegram Text Splitter

A Python library for splitting long Markdown texts into smaller, Telegram-friendly chunks. It intelligently breaks down text based on Markdown formatting (paragraphs, lines, words) to ensure that each chunk is a valid and readable piece of text, suitable for sending via Telegram bots.

## Features

*   Splits Markdown text into chunks, each respecting Telegram's message length limits.
*   Prioritizes splitting at natural boundaries like paragraph breaks (`\n\n`), line breaks (`\n`), and spaces.
*   Ensures that no Markdown formatting is broken, making subsequent conversion to HTML (e.g., using `chatgpt-md-converter`) reliable.
*   Lightweight and dependency-free (except for standard Python libraries).

## Installation

You can install the library directly from GitHub:

```bash
pip install git+https://github.com/kobaltgit/telegram_text_splitter.git
```

Alternatively, if you have the library cloned locally, you can install it in editable mode:

```bash
cd path/to/your/telegram_text_splitter_lib
pip install -e .
```

## Usage

Here's a simple example of how to use the `split_markdown_into_chunks` function:

```python
from telegram_text_splitter import split_markdown_into_chunks

long_markdown_text = """
# My Awesome Title

This is the first paragraph. It contains some text that needs to be split.
We are aiming for chunks that are less than 4000 characters.

This is the second paragraph. It's separated by a double newline.

### A Subheading

*   Item 1
*   Item 2
    *   Sub-item 2.1
    *   Sub-item 2.2

And a very long word that might cause issues if not handled correctly: Antidisestablishmentarianism.
"""

chunks = split_markdown_into_chunks(long_markdown_text)

for i, chunk in enumerate(chunks):
    print(f"--- Chunk {i+1} (Length: {len(chunk)}) ---")
    print(chunk)
    print("-" * 20)

# Example usage in a Telegram bot handler:
# from aiogram import Bot, types
# from aiogram.enums import ParseMode
# from telegram_text_splitter import split_markdown_into_chunks
# from chatgpt_md_converter import telegram_format # Assuming this is imported elsewhere
# from utils.message_sender import send_long_message

# async def send_ai_response(bot: Bot, chat_id: int, ai_markdown_response: str, i18n):
#     markdown_chunks = split_markdown_into_chunks(ai_markdown_response)
#     for md_chunk in markdown_chunks:
#         html_chunk = telegram_format(md_chunk)
#         await send_long_message(
#             bot=bot,
#             chat_id=chat_id,
#             text_chunks=[html_chunk], # Send each HTML chunk as a single item list
#             keyboard=None, # Add your keyboard here if needed
#             parse_mode=ParseMode.HTML
#         )

```

## Integration with chatgpt-md-converter

This library works especially well in combination with [chatgpt-md-converter](https://github.com/Latand/formatter-chatgpt-telegram) , which converts Markdown into Telegram-compatible HTML. This allows you to safely split and then send formatted text messages via Telegram bots, without breaking Markdown structure or exceeding message length limits.

Using both libraries together ensures:

*   Reliable conversion to HTML understood by the Telegram Bot API
*   Support for advanced Telegram-specific syntax like spoilers (||text||) and expandable blockquotes (**> text)
*   Safe handling of code blocks, lists, nested styles, and more

### ✅ Example Usage

```python
from telegram_text_splitter import split_markdown_into_chunks
from chatgpt_md_converter import telegram_format

# A long Markdown-formatted response from ChatGPT or another source
long_markdown_text = """
# Introduction
This is a **Markdown** example that includes *italic*, __underlined__, and ~~strikethrough~~ text.
||This is a spoiler||
```
Code block inside Markdown
print("Hello, world!")

```
"""
# Step 1: Split the Markdown into chunks suitable for Telegram
chunks = split_markdown_into_chunks(long_markdown_text)

# Step 2: Convert each chunk to Telegram-compatible HTML and send
for chunk in chunks:
    html_chunk = telegram_format(chunk)
    print(html_chunk)  # Replace this with bot.send_message(...) using ParseMode.HTML
```

## Contributing

Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes and add tests.
4.  Ensure your code follows PEP 8 style guidelines.
5.  Submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.