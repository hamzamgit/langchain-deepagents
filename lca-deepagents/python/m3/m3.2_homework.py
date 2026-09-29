# python/m3/m3.2_homework.py
"""M3.2 Homework: Bundle a Reference File Into Your Skill.

THE IDEA
The lab's two skills (qualify-lead and draft-pitch) are each a single flat
SKILL.md file with everything inline. But the lesson also covered a third
stage of progressive disclosure: a skill can point to supporting files (a
reference doc, a template, a script) that live alongside SKILL.md and that
the agent only reads when it actually needs them, instead of stuffing
everything into the system prompt up front. This homework asks you to write
a skill for a topic or workflow YOU pick (not sales) that bundles a SECOND
file with details the agent needs but that aren't in SKILL.md itself, then
confirm from the trace that the agent actually called `read_file` on that
second file before answering, rather than guessing.

WHAT YOU FILL IN
  TODO 1: write your own SKILL.md content. It must instruct the agent to
    read a `reference.md` file (in the same skill directory) for specific
    details it needs, and must NOT restate those details inline. The `name`
    field in your frontmatter must exactly match SKILL_NAME below.
  TODO 2: write reference.md's content: the specific facts, numbers, or
    template your skill's instructions point to and depend on.
  TODO 3: write a system prompt and a user question that should activate
    your skill.

RUN
  cd python
  uv run ./m3/m3.2_homework.py
"""

import tempfile
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

from models import model

# This name becomes the skill's directory name. It must exactly match the
# `name:` field you write in the frontmatter inside build_skill_md() below.
SKILL_NAME = "triage-bug-report"
REFERENCE_PATH = f"/skills/{SKILL_NAME}/reference.md"


# ════════════════════════════════════════════════════════════════════════
# TODO 1: Write your own SKILL.md content.
#
# Requirements:
#   - YAML frontmatter with `name` (must equal SKILL_NAME above) and
#     `description` (a specific sentence describing WHEN to use this skill).
#   - Steps that tell the agent to open `reference.md` (in this same skill
#     directory) for the specific details it needs to do the task well.
#   - Do NOT put those details in SKILL.md itself; if the agent could do
#     the task correctly without ever reading reference.md, this doesn't
#     exercise progressive disclosure.
#
# Example shape (delete this and write your own):
#   return """---
#   name: your-skill-name
#   description: Use when the user wants to ...
#   ---
#
#   # Your Skill Title
#
#   **Step 1: ...**: ...
#   **Step 2: ...**: before proceeding, read reference.md in this skill's
#     directory for the exact ... to use. Do not guess these.
#   """
# ════════════════════════════════════════════════════════════════════════

def build_skill_md() -> str:
    """TODO 1: return your own SKILL.md content as a string."""
    return """---
name: triage-bug-report
description: Use when the user wants to triage, prioritize, or classify a software bug report.
---

# Triage a Bug Report

Turn a raw bug report into a structured triage decision with severity,
priority, and next steps.

**Step 1: Restate the bug**: Summarize the reported problem in one or two
sentences. Note any missing details (repro steps, environment, expected vs
actual).

**Step 2: Classify impact**: Decide whether the bug blocks core workflows,
affects a subset of users, or is cosmetic.

**Step 3: Look up the rubric**: Before assigning severity or priority, read
`reference.md` in this skill's directory for the exact severity scale,
priority matrix, and output template. Do not invent your own labels or
SLA hours; they are specific to this team's process.

**Step 4: Assign severity and priority**: Map the bug to one severity and
one priority from reference.md, using the matrix there.

**Step 5: Next actions**: List 2-4 concrete follow-ups (who should look,
what to verify, whether a hotfix is warranted) consistent with the
priority's SLA from reference.md.

## Output

Fill the triage template from reference.md. Every field must use labels
and numbers from that file — do not substitute common industry defaults.
"""


# ════════════════════════════════════════════════════════════════════════
# TODO 2: Write reference.md's content.
#
# This should contain the specific facts your SKILL.md pointed to and
# depends on: a rubric, a set of numbers, a template, a checklist. Specific
# enough that an answer produced without reading it would visibly differ
# from one produced with it.
# ════════════════════════════════════════════════════════════════════════

def build_reference_md() -> str:
    """TODO 2: return the content of your skill's reference.md."""
    return """# Bug Triage Rubric (Team Atlas)

Use only these labels and numbers. Do not substitute P0/P1 industry defaults
or generic "critical/major/minor" wording.

## Severity scale

| Code | Name          | Meaning |
|------|---------------|---------|
| S1   | Showstopper   | Core path unusable; data loss or security exposure |
| S2   | Major         | Important feature broken; workaround exists |
| S3   | Minor         | Partial degradation; most users unaffected |
| S4   | Polish        | Cosmetic, docs, or nice-to-have |

## Priority matrix (severity × user impact)

| Severity | Many users / production | Few users / staging | Internal only |
|----------|-------------------------|---------------------|---------------|
| S1       | PRI-NOW                 | PRI-DAY             | PRI-WEEK      |
| S2       | PRI-DAY                 | PRI-WEEK            | PRI-BACKLOG   |
| S3       | PRI-WEEK                | PRI-BACKLOG         | PRI-BACKLOG   |
| S4       | PRI-BACKLOG             | PRI-BACKLOG         | PRI-BACKLOG   |

## SLA by priority (response target)

| Priority    | First engineer response | Hotfix allowed? |
|-------------|-------------------------|------------------|
| PRI-NOW     | within 30 minutes       | yes              |
| PRI-DAY     | within 4 hours          | yes if S1        |
| PRI-WEEK    | within 2 business days  | no               |
| PRI-BACKLOG | next planning cycle     | no               |

## Output template

```
## Triage
- Summary:
- Severity: (S1–S4 + name)
- Priority: (PRI-*)
- SLA: (copy hours from table above)
- Hotfix: yes/no (per table)
- Missing info:
- Next actions:
  1.
  2.
```
"""


# Write the skill to a scratch directory so it's discoverable through a
# FilesystemBackend, the same mechanism the lab uses for python/m3/skills/.
_tmp_root = Path(tempfile.mkdtemp(prefix="m3_2_homework_"))
_skill_dir = _tmp_root / "skills" / SKILL_NAME
_skill_dir.mkdir(parents=True, exist_ok=True)
(_skill_dir / "SKILL.md").write_text(build_skill_md())
(_skill_dir / "reference.md").write_text(build_reference_md())

backend = FilesystemBackend(root_dir=str(_tmp_root), virtual_mode=True)
print(f"Skill files written to: {_skill_dir}")


# ════════════════════════════════════════════════════════════════════════
# TODO 3: Write a system prompt and a triggering question.
#
# SYSTEM_PROMPT: give the agent a persona of your choosing (a name, a
# voice, anything you want).
# USER_QUESTION: a question that should match your skill's `description`
# closely enough that the agent activates it.
# ════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are Mira, a calm on-call engineer who triages bugs for
Team Atlas. Be precise, use the team's labels, and never invent severity or
priority codes."""
USER_QUESTION = (
    "Please triage this bug: After yesterday's deploy, the checkout button on "
    "production does nothing for every customer — carts are stuck and we are "
    "losing orders. No workaround. Classify severity and priority."
)

agent = create_deep_agent(
    model=model,
    name="Homework_Agent",
    backend=backend,
    skills=["/skills"],
    system_prompt=SYSTEM_PROMPT,
)

result = agent.invoke({"messages": [{"role": "user", "content": USER_QUESTION}]})
print(result["messages"][-1].content)

read_calls = [
    call
    for msg in result["messages"]
    for call in getattr(msg, "tool_calls", [])
    if call["name"] == "read_file"
]
reference_was_read = any(call["args"].get("file_path") == REFERENCE_PATH for call in read_calls)
print(f"\n--- Did the agent read {REFERENCE_PATH}? {reference_was_read} ---")
if not reference_was_read:
    print(
        "It didn't. Either SKILL.md isn't clearly telling it to, or the "
        "task is answerable without the details in reference.md."
    )
