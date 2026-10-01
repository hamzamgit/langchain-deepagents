"""M1.6 Homework: Connect to a Different MCP Server.

THE IDEA
Lab 1 connected to the LangChain docs MCP server and filtered its tools
down to just search_docs_by_lang_chain. This homework asks you to connect
to a different public MCP server entirely, one that requires no auth
beyond what your labs already use, and put one of its tools to work.

DeepWiki:
  https://mcp.deepwiki.com/mcp

RUN
  cd python
  uv run ./m1/m1.6_homework.py
"""

import asyncio
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from deepagents import create_deep_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from models import model


async def build_tools():
    """Build MCP client, fetch tools, filter them, and return them."""

    client = MultiServerMCPClient(
        {
            "deepwiki": {
                "transport": "http",
                "url": "https://mcp.deepwiki.com/mcp",
            }
        }
    )

    tools = await client.get_tools()

    # Only allow the DeepWiki tool we want the agent to use.
    ALLOWED = {"ask_question"}

    return [tool for tool in tools if tool.name in ALLOWED]


QUESTION = (
    "Using the DeepWiki information for the public GitHub repository "
    "langchain-ai/deepagents, explain what the project is designed to do "
    "and describe its main architecture or components."
)


async def main():
    tools = await build_tools()

    agent = create_deep_agent(
        model=model,
        tools=tools,
    )

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": QUESTION,
                }
            ]
        }
    )

    print(result["messages"][-1].content)


asyncio.run(main())
