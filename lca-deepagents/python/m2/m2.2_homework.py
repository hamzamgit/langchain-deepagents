from pathlib import Path

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend

from models import model


# ════════════════════════════════════════════════════════════════════════
# TODO 1: Configure a backend
# ════════════════════════════════════════════════════════════════════════

my_dir = Path(__file__).parent / "meeting_files"
my_dir.mkdir(exist_ok=True)

notes_file = my_dir / "meeting_notes.md"

notes_file.write_text(
    """# Meeting Notes

## Current Topics
- Project planning
- Backend development
- Testing

## Action Items
- Review API changes
- Prepare test cases
""",
    encoding="utf-8",
)

backend = FilesystemBackend(
    root_dir=str(my_dir),
    virtual_mode=True,
)


# ════════════════════════════════════════════════════════════════════════
# TODO 2: Write the task and permission rules
# ════════════════════════════════════════════════════════════════════════

TASK = """
Read the file /meeting_notes.md.

Then update the meeting notes by adding this new action item:

- Prepare deployment documentation

Save the updated file.
"""

permissions: list[FilesystemPermission] = []


if backend is None:
    raise NotImplementedError("TODO 1: see the comment block above")
if TASK is None:
    raise NotImplementedError("TODO 2: see the comment block above")


agent = create_deep_agent(
    model=model,
    backend=backend,
    permissions=permissions,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": TASK}]},
    config={"configurable": {"thread_id": "homework-m2.2"}},
)

print(result["messages"][-1].content)