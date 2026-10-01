# python/m4/m4.2_homework.py
"""M4.2 Homework: Give Each Subagent Its Own Scoped Scratch Folder.

THE IDEA
The lab's genre-researcher subagents each wrote raw search notes to their own
assigned /research/<genre>/ folder, kept out of the editor's context by
FilesystemPermission scoping: researchers could write under /research/**, the
editor could not. 

This homework asks you to build a small team of 2 subagent types for 
a domain YOU pick (e.g., trip planning, home renovation), each with 
its own private, permission-scoped folder under /scratch/<name>/ to
stash raw notes in before answering. The harness below wires up the scratch
folder, the permissions, and the write-before-answering instruction for you;
you just decide who your two subagents are.

WHAT YOU FILL IN
  TODO 1: for each of the two entries in SUBAGENT_SPECS, fill in "name",
    "description" (when the main agent should call it), and "role_prompt"
    (who this subagent is and what its job is). Everything else -- the
    scratch folder, the permissions, the instruction to save raw notes
    before answering -- is handled for you.
  TODO 2: write the main agent's system prompt, telling it which subagent
    to call for which part of the job, and a user request that should
    trigger delegation to BOTH subagents.

RUN
  cd python
  uv run ./m4/m4.2_homework.py
"""

from deepagents import FilesystemPermission, create_deep_agent

from models import model, strong_model

SCRATCH_ROOT = "/scratch"


def scratch_path(subagent_name: str) -> str:
    return f"{SCRATCH_ROOT}/{subagent_name}/notes.md"


def scratch_permissions(subagent_name: str) -> list:
    """Scope a subagent to write only under its own scratch folder -- the same
    first-match-wins allow-then-deny pattern the lab used for
    research_permissions/editor_permissions."""
    return [
        FilesystemPermission(operations=["read", "write"], paths=[f"{SCRATCH_ROOT}/{subagent_name}/**"], mode="allow"),
        FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
    ]


def scratch_instruction(subagent_name: str) -> str:
    return (
        f'Before you answer, call write_file on "{scratch_path(subagent_name)}" '
        "with your raw notes or reasoning. Then give your final answer using "
        "only the polished result -- do not repeat those raw notes in your reply."
    )


def build_subagents(specs: list[dict]) -> list[dict]:
    team = []
    for spec in specs:
        name = spec["name"]
        team.append(
            {
                "name": name,
                "description": spec["description"],
                "system_prompt": spec["role_prompt"] + "\n\n" + scratch_instruction(name),
                "permissions": scratch_permissions(name),
            }
        )
    return team


# ════════════════════════════════════════════════════════════════════════
# TODO 1: Fill in your two subagents.
#
# For each entry: "name" is the handle the main agent calls it by, kebab-
# case (e.g. "flight-finder"). "description" is how the main agent decides
# which one to use. "role_prompt" is that subagent's own job description --
# don't mention scratch files or write_file here, that's added for you.
# ════════════════════════════════════════════════════════════════════════

SUBAGENT_SPECS = [
    {
        "name": "itinerary-planner",
        "description": (
            "Build a day-by-day trip itinerary for a destination, dates, "
            "and travel style (pace, interests, budget)."
        ),
        "role_prompt": (
            "You are a travel itinerary planner. Given a destination, trip "
            "length, and interests, propose a realistic day-by-day plan: "
            "morning/afternoon/evening blocks, travel time between stops, "
            "and one backup indoor option per day. Keep the pace doable."
        ),
    },
    {
        "name": "budget-estimator",
        "description": (
            "Estimate trip costs by category (lodging, food, transport, "
            "activities) for a stated destination, duration, and budget level."
        ),
        "role_prompt": (
            "You are a travel budget estimator. Given destination, number of "
            "days, travelers, and budget level (shoestring / mid-range / "
            "comfort), produce a rough cost breakdown by category with a "
            "daily total and a trip total. Use round numbers; state "
            "assumptions clearly."
        ),
    },
]


# ════════════════════════════════════════════════════════════════════════
# TODO 2: Write the main agent's system prompt and a triggering request.
#
# MAIN_PROMPT should tell the main agent about each subagent by name and
# when to call it (mirror how EDITOR_PROMPT in the lab named
# genre-researcher and explained the job).
# USER_REQUEST should be a task that should make the main agent delegate to
# BOTH of your subagents.
# ════════════════════════════════════════════════════════════════════════

MAIN_PROMPT = """You are Atlas, lead of a small trip-planning team.
For any trip request, delegate to your specialists using the task tool:
- itinerary-planner for the day-by-day schedule and activities
- budget-estimator for cost breakdowns and totals

If the request needs both a plan and costs, call BOTH specialists.
Collect their replies and present one clear trip brief to the traveler."""

USER_REQUEST = (
    "Plan a 4-day mid-range trip to Lisbon for two adults in May. We like "
    "food markets, walkable neighborhoods, and one day trip outside the city. "
    "Give us a day-by-day itinerary plus a rough budget breakdown."
)

for _spec in SUBAGENT_SPECS:
    if _spec["name"].startswith("TODO-1"):
        raise NotImplementedError("TODO 1: see the comment block above")
if MAIN_PROMPT.startswith("TODO 2") or USER_REQUEST.startswith("TODO 2"):
    raise NotImplementedError("TODO 2: see the comment block above")

_team = build_subagents(SUBAGENT_SPECS)

# The main agent must never write into any subagent's scratch folder either.
MAIN_PERMISSIONS = [
    FilesystemPermission(operations=["write"], paths=[f"{SCRATCH_ROOT}/**"], mode="deny"),
]

agent = create_deep_agent(
    model=strong_model,
    name="Homework_Team_Agent",
    system_prompt=MAIN_PROMPT,
    subagents=_team,
    permissions=MAIN_PERMISSIONS,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": USER_REQUEST}]},
    config={"recursion_limit": 50},
)
print(result["messages"][-1].content)

files = result.get("files", {})
print("\n--- Scratch folder isolation check ---")
for spec in SUBAGENT_SPECS:
    path = scratch_path(spec["name"])
    print(f"  {path}: {'found' if path in files else 'not written (subagent may not have been called)'}")

scratch_files = [p for p in files if p.startswith(SCRATCH_ROOT + "/")]
expected = {scratch_path(spec["name"]) for spec in SUBAGENT_SPECS}
stray = [p for p in scratch_files if p not in expected]
if stray:
    print(f"  Unexpected scratch files (isolation may have failed): {stray}")
else:
    print("  No stray scratch files -- each subagent wrote only to its own folder.")
