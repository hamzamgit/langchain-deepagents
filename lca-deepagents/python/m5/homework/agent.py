# python/m5/homework/agent.py
"""M5.2 Homework: Deploy Your Own Agent.

THE IDEA
The lab deployed a fairly bare-bones agent (no tools, no persona, just
create_deep_agent(model=model)) and you only ever talked to it through
Studio's chat panel. This homework has two parts: first, deploy an agent
with your personal touch; second, talk to it the way any other client
would, straight over the Agent Server API this lesson covers, instead of
through Studio.

WHAT YOU FILL IN
  TODO 1: write your own @tool-decorated function on a topic of your
    choosing. A plain Python dict lookup is enough, no external API or
    key required.
  TODO 2: write a system_prompt that gives the agent a persona of your
    choosing and tells it to call your tool before answering.
  Then open call_agent_api.py in this same folder for TODO 3, which talks
  to this deployed agent over HTTP instead of through Studio.

RUN
  cd python/m5/homework
  uv run langgraph dev
Then chat with your agent in the Studio window that opens, or see
call_agent_api.py to talk to it over the API instead.
"""

from langchain_core.tools import tool

from deepagents import create_deep_agent
from models import model


# TODO 1: replace this with your own @tool-decorated function.
COFFEE_BREW_FACTS = {
    "espresso": (
        "Espresso uses a fine grind and ~18–20g of coffee for a double shot, "
        "pulled in about 25–30 seconds at ~9 bars of pressure."
    ),
    "pour-over": (
        "Pour-over (V60) typically uses a medium-fine grind and a 1:16 "
        "coffee-to-water ratio, with a total brew time around 2.5–3.5 minutes."
    ),
    "french-press": (
        "French press uses a coarse grind and about 1:15 ratio; steep 4 minutes "
        "before plunging so fines don't over-extract."
    ),
    "cold-brew": (
        "Cold brew uses a coarse grind and a strong concentrate ratio (often "
        "1:5 to 1:8), steeped 12–18 hours in the fridge, then diluted to taste."
    ),
}


@tool
def lookup_coffee_brew(method: str) -> str:
    """Look up a coffee brewing fact. method is one of: espresso, pour-over, french-press, cold-brew."""
    key = method.lower().strip().replace(" ", "-").replace("_", "-")
    return COFFEE_BREW_FACTS.get(
        key,
        f"No brew guide on file for '{method}'. Try espresso, pour-over, french-press, or cold-brew.",
    )


# TODO 2: replace this with your own persona system prompt.
SYSTEM_PROMPT = """You are Bean, a calm specialty-coffee barista who talks \
like you're behind the bar on a quiet morning. For any question about how \
to brew coffee, ALWAYS call lookup_coffee_brew first with the matching \
method, then answer using that fact in plain friendly language. Never invent \
ratios or times when the tool can provide them."""

# `langgraph.json` points at this module-level variable: "./agent.py:graph".
graph = create_deep_agent(model=model, tools=[lookup_coffee_brew], system_prompt=SYSTEM_PROMPT)
