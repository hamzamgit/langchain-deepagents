# python/m1/m1.7_homework.py
"""M1.7 Homework: Design Your Own Multi-Thread Scenario."""

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

from models import model

agent = create_deep_agent(
    model=model,
    checkpointer=MemorySaver(),
)


# TODO 1: Pick your own topic and set up two or more thread configs.

thread_a = {
    "configurable": {
        "thread_id": "programming-thread-a"
    }
}

thread_b = {
    "configurable": {
        "thread_id": "programming-thread-b"
    }
}


# TODO 2: Run the turns that demonstrate persistence, isolation,
# and checkpointer scope.

def run_scenario():
    """Run the multi-turn, multi-thread scenario."""

    # ---------------------------------------------------------
    # 1. THREAD A - Give the agent a fact
    # ---------------------------------------------------------

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "My favorite programming language is Python.",
                }
            ]
        },
        config=thread_a,
    )

    print("\n--- Thread A: First Turn ---")
    print(result["messages"][-1].content)

    # ---------------------------------------------------------
    # 2. THREAD A - Ask about the fact
    # ---------------------------------------------------------

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "What is my favorite programming language?",
                }
            ]
        },
        config=thread_a,
    )

    print("\n--- Thread A: Second Turn ---")
    print(result["messages"][-1].content)

    # ---------------------------------------------------------
    # 3. THREAD B - Same question, different thread
    # ---------------------------------------------------------

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "What is my favorite programming language?",
                }
            ]
        },
        config=thread_b,
    )

    print("\n--- Thread B: New Thread ---")
    print(result["messages"][-1].content)

    # ---------------------------------------------------------
    # 4. NEW AGENT + NEW MEMORY SAVER
    #    Same thread_id as thread_a
    # ---------------------------------------------------------

    fresh_agent = create_deep_agent(
        model=model,
        checkpointer=MemorySaver(),
    )

    result = fresh_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "What is my favorite programming language?",
                }
            ]
        },
        config=thread_a,
    )

    print("\n--- Fresh Agent: Same Thread ID ---")
    print(result["messages"][-1].content)

    print(
        "\nWhy doesn't the fresh agent know the answer?"
        "\nBecause the memory is stored in the MemorySaver instance."
        "\nThe thread_id is only an identifier for the conversation state."
        "\nThe fresh agent has a new MemorySaver, so it has no previous memory."
    )


run_scenario()
