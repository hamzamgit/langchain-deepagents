import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from deepagents import create_deep_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from models import model


# TODO 1: Define your own action tool
@tool
def book_meeting_room(room: str) -> str:
    """Book the specified meeting room."""
    return f"Meeting room {room!r} has been booked successfully."


# TODO 2: Configure the agent
SYSTEM_PROMPT = """
You are a meeting room booking assistant.

When the user asks to book a meeting room, use the book_meeting_room tool.
Do not book a room unless the user explicitly asks you to book one.
"""

INITIAL_REQUEST = "Please book the meeting room called Conference Room A."

INTERRUPT_ON = {
    "book_meeting_room": {
        "allowed_decisions": ["approve", "edit", "reject"]
    }
}


if "TODO 1" in book_meeting_room.description:
    raise NotImplementedError("TODO 1: see the comment block above")
if "TODO 2" in SYSTEM_PROMPT or "TODO 2" in INITIAL_REQUEST:
    raise NotImplementedError("TODO 2: see the comment block above")


agent = create_deep_agent(
    model=model,
    tools=[book_meeting_room],
    system_prompt=SYSTEM_PROMPT,
    interrupt_on=INTERRUPT_ON,
    checkpointer=MemorySaver(),
)

config = {"configurable": {"thread_id": "m1-8-homework-demo"}}

result = agent.invoke(
    {"messages": [{"role": "user", "content": INITIAL_REQUEST}]},
    config=config,
    version="v2",
)


while result.interrupts:
    pending = result.interrupts[0].value
    decisions = []

    for req in pending["action_requests"]:
        print(f"\nApproval required for {req['name']}:")
        print(req["args"])

        choice = input(
            "\nApprove, edit, or reject? (approve/edit/reject): "
        ).strip().lower()

        if choice in ("approve", "yes", "y"):
            decisions.append({"type": "approve"})

        elif choice in ("edit", "e"):
            edited_args = dict(req["args"])
            key = next(iter(edited_args))

            edited_args[key] = input(
                f"New value for '{key}': "
            )

            decisions.append(
                {
                    "type": "edit",
                    "edited_action": {
                        "name": req["name"],
                        "args": edited_args,
                    },
                }
            )

        else:
            decisions.append(
                {
                    "type": "reject",
                    "message": "User rejected this action.",
                }
            )

    result = agent.invoke(
        Command(resume={"decisions": decisions}),
        config=config,
        version="v2",
    )


for msg in result.value["messages"]:
    if hasattr(msg, "name") and msg.name == "book_meeting_room":
        print(msg.content)
        break