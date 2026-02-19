import os

import chainlit as cl

from optopsy.ui.agent import OptopsyAgent
from optopsy.ui.tools import save_uploaded_file


@cl.on_chat_start
async def on_chat_start():
    model = os.environ.get("OPTOPSY_MODEL", "gpt-4o-mini")
    agent = OptopsyAgent(model=model)
    cl.user_session.set("agent", agent)
    cl.user_session.set("messages", [])

    await cl.Message(
        content=(
            "Welcome to **Optopsy Chat** — your options strategy backtesting assistant.\n\n"
            "**Getting started:**\n"
            "1. Upload a CSV file with option chain data (drag & drop or use the attachment button)\n"
            "2. Ask me to load and preview the data\n"
            "3. Run any of 28 options strategies — just describe what you want in plain English\n\n"
            "**Example prompts:**\n"
            '- *"Load my file and show me what\'s in it"*\n'
            '- *"Run a long call spread with 60 DTE entry"*\n'
            '- *"Compare iron condors vs iron butterflies"*\n'
            '- *"Backtest short puts with max 30% OTM"*\n\n'
            f"Using model: `{model}` (set `OPTOPSY_MODEL` env var to change)"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    agent: OptopsyAgent = cl.user_session.get("agent")
    messages: list = cl.user_session.get("messages")

    # Handle file uploads attached to the message
    if message.elements:
        for element in message.elements:
            if hasattr(element, "path") and element.path:
                filename = element.name or os.path.basename(element.path)
                if filename.endswith(".csv"):
                    dest = save_uploaded_file(element.path, filename)
                    await cl.Message(
                        content=f"Saved `{filename}` — I can load it whenever you're ready."
                    ).send()
                else:
                    await cl.Message(
                        content=f"Got `{filename}`, but I only work with CSV files. Please upload a `.csv` file."
                    ).send()

    # Skip LLM call if message is empty and was just a file upload
    if not message.content.strip() and message.elements:
        return

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
