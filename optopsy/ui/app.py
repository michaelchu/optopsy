import os

import chainlit as cl

from optopsy.ui.agent import OptopsyAgent


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
            "1. Ask me to list available data files\n"
            "2. Load a file and preview it\n"
            "3. Run any of 28 options strategies — just describe what you want in plain English\n\n"
            "**Example prompts:**\n"
            '- *"What files are available?"*\n'
            '- *"Load my file and show me what\'s in it"*\n'
            '- *"Run a long call spread with 60 DTE entry"*\n'
            '- *"Compare iron condors vs iron butterflies"*\n\n'
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
