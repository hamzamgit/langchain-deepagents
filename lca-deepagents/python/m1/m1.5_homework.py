from deepagents import create_deep_agent
from langchain_core.tools import tool

from models import model


FASTAPI_FACTS = {
    "fastapi": "FastAPI is a Python web framework for building APIs using Python type hints.",
    "pydantic": "Pydantic is used for data validation using Python type annotations.",
    "uvicorn": "Uvicorn is an ASGI server used to run FastAPI applications.",
    "dependency injection": "FastAPI provides dependency injection through the Depends function.",
}


@tool
def lookup_python_api_fact(topic: str) -> str:
    """Look up a fact about Python API development."""

    topic = topic.lower().strip()

    fact = FASTAPI_FACTS.get(topic)

    if fact:
        return fact

    return (
        f"No fact found for '{topic}'. "
        f"Available topics: {', '.join(FASTAPI_FACTS.keys())}"
    )


SYSTEM_PROMPT = """
You are a friendly Python API mentor.

Answer questions about Python API development, especially FastAPI,
Pydantic, Uvicorn, and dependency injection.

Before answering a question related to these topics, you MUST call
the lookup_python_api_fact tool first.

Use the information returned by the tool to help formulate your answer.

If the requested topic is not available in the tool, clearly say
that the topic is not available in the lookup.
"""


agent = create_deep_agent(
    model=model,
    tools=[lookup_python_api_fact],
    system_prompt=SYSTEM_PROMPT,
)


result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "What is FastAPI?",
            }
        ]
    }
)

print(result["messages"][-1].content)