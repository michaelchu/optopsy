import os
from pathlib import Path

from dotenv import load_dotenv, find_dotenv

# .env takes priority over shell env so there's no conflict with
# unrelated exports (e.g. work credentials in .zshrc).
_env_path = find_dotenv() or str(Path(__file__).resolve().parent.parent.parent / ".env")
load_dotenv(_env_path, override=True)

import chainlit as cl

from optopsy.ui.agent import OptopsyAgent
from optopsy.ui.providers import get_provider_names


@cl.on_chat_start
async def on_chat_start():
    model = os.environ.get("OPTOPSY_MODEL", "gpt-4o-mini")
    agent = OptopsyAgent(model=model)
    cl.user_session.set("agent", agent)
    cl.user_session.set("messages", [])

    # Detect configured data providers
    providers = get_provider_names()

    provider_line = ""
    if providers:
        provider_line = f"Data providers: {', '.join(providers)}\n"
    else:
        provider_line = (
            "No data providers configured. "
            "Add API keys to your `.env` file to enable live data.\n"
        )

    await cl.Message(
        content=(
            "Welcome to **Optopsy Chat** — your options strategy backtesting assistant.\n\n"
            "**Getting started:**\n"
            "1. Fetch options data or load an existing file\n"
            "2. Preview the data\n"
            "3. Run any of 28 options strategies — just describe what you want\n\n"
            "**Example prompts:**\n"
            '- *"Fetch AAPL options data from the last 6 months"*\n'
            '- *"Load my file and show me what\'s in it"*\n'
            '- *"Run a long call spread with 60 DTE entry"*\n'
            '- *"Compare iron condors vs iron butterflies"*\n\n'
            f"{provider_line}"
            f"Using model: `{model}` (set `OPTOPSY_MODEL` env var to change)"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    agent: OptopsyAgent = cl.user_session.get("agent")
    messages: list = cl.user_session.get("messages")

    messages.append({"role": "user", "content": message.content})

    # Callback to show tool calls as steps in the UI
    async def on_tool_call(tool_name, arguments, result):
        async with cl.Step(name=tool_name, type="tool") as step:
            step.input = str(arguments)
            step.output = result

    response_msg = cl.Message(content="")
    await response_msg.send()

    try:
        result_text, updated_messages = await agent.chat(
            messages, on_tool_call=on_tool_call
        )
        response_msg.content = result_text
        await response_msg.update()
        cl.user_session.set("messages", updated_messages)
    except Exception as e:
        response_msg.content = f"Error: {e}"
        await response_msg.update()


def main():
    from chainlit.cli import run_chainlit

    run_chainlit(os.path.abspath(__file__))
