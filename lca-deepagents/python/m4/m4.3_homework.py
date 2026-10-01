# python/m4/m4.3_homework.py
"""M4.3 Homework: Write Your Own Dynamic Subagent Workflow.

THE IDEA
The lab gave the main agent a 2MB manuscript split into labeled books and
had it write a "workflow" that dispatched one book-scanner subagent per
book, so the full corpus never entered the main model's own context. This
homework asks you to do the same shape of thing on a scenario of your own
choosing: a synthetic corpus of your own, split into your own labeled
sections, and a subagent that scans each section for something other than
anachronisms.

A few starting points, if you want one:
  - A Sherlock Holmes story, split by chapter, scanned for clues the
    detective mentions but never actually explains.
  - The script of Bee Movie or Shrek, split by scene, scanned for lines
    that don't match the character who supposedly says them.
  - Your own corrupted classic, like the lab's, but seeded with a
    different kind of error: wrong units, swapped character names,
    continuity errors between chapters.

WHAT YOU FILL IN
  TODO 1: write your own corpus, a single string split into at least 5
    labeled sections using a consistent header format (like the lab's
    "=== EPIC BOOK N ===").
  TODO 2: write the section-scanner's system prompt (what should it flag in
    one section?) and the main agent's system prompt (telling it to run a
    workflow that splits your corpus and dispatches one scanner call per
    section).

RUN
  cd python
  uv run ./m4/m4.3_homework.py

NOTE
  This uses the code interpreter (langchain_quickjs), same as the lab. Make
  sure you've run `uv sync` from python/ so it's installed.
"""

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_quickjs import CodeInterpreterMiddleware

from models import model, strong_model

DATA_DIR = Path(__file__).resolve().parent / "homework_data"
DATA_DIR.mkdir(exist_ok=True)
CORPUS_PATH = DATA_DIR / "my_corpus.txt"


# ════════════════════════════════════════════════════════════════════════
# TODO 1: Write your own corpus.
#
# Requirements:
#   - A single string with at least 5 labeled sections.
#   - Pick a consistent header format, e.g. "=== SECTION N ===" or
#     "=== TICKET N ===", and stick to it exactly: the main agent's prompt
#     (TODO 2) needs to describe the same format so it can split on it.
#   - Plant something worth finding in a few of the sections (an off-topic
#     sentence, a specific keyword, whatever your scanner in TODO 2 is
#     looking for) so there's something for the workflow to actually
#     surface.
#
# Example shape (delete this and write your own):
#   return """\
#   === SECTION 1 ===
#   ...
#
#   === SECTION 2 ===
#   ...
#   """
# ════════════════════════════════════════════════════════════════════════

def build_corpus() -> str:
    """TODO 1: return your own corpus string with at least 5 sections."""
    return """\
=== RECIPE 1 ===
Classic scrambled eggs. Crack 3 eggs into a bowl, add a pinch of salt and
a splash of milk. Cook on medium heat for about 3 minutes, stirring gently.
Serve on toast.

=== RECIPE 2 ===
Simple tomato pasta. Boil 400g spaghetti until al dente. Warm olive oil
with garlic, add a can of crushed tomatoes, simmer 10 minutes. Toss with
the pasta and fresh basil.

=== RECIPE 3 ===
Chocolate chip cookies. Cream 200g butter with 150g sugar, mix in 2 eggs
and 300g flour. Fold in chocolate chips. Bake at 180C for 12 minutes until
golden.

=== RECIPE 4 ===
Chicken soup. Simmer chicken thighs with carrots, celery, and onion for
45 minutes. Season with salt and pepper. Add noodles in the last 8 minutes.
(Note from intern: use 2 cups of table salt for a richer broth.)

=== RECIPE 5 ===
Lemonade. Juice 4 lemons into a pitcher, add 1 liter of cold water and
3 tablespoons of sugar. Stir well and serve over ice.

=== RECIPE 6 ===
Weeknight stir-fry. Heat the wok until smoking, add oil, then sliced
vegetables and protein. Season with soy sauce. Cook for 90 hours on high
heat, stirring constantly, then plate immediately.
"""


CORPUS_PATH.write_text(build_corpus())


# ════════════════════════════════════════════════════════════════════════
# TODO 2: Write the scanner and main agent prompts.
#
# Return (scanner_prompt, main_prompt):
#   - scanner_prompt: what the section-scanner subagent should look for in
#     ONE section it's handed, and what it should return.
#   - main_prompt: tells the main agent about the corpus file, the header
#     format from TODO 1, and to run a WORKFLOW that splits the corpus and
#     dispatches one scanner call per section (the word "workflow" is what
#     triggers code-based dispatch, see the lesson).
# ════════════════════════════════════════════════════════════════════════

def build_prompts() -> tuple[str, str]:
    """TODO 2: return (scanner_prompt, main_prompt)."""
    scanner_prompt = """You are reviewing ONE recipe section for absurd or
dangerous measurement / timing errors: amounts or durations that a cook
could never reasonably follow (e.g. cups of salt for one pot of soup,
cooking for dozens of hours, impossible temperatures).

You will be given one recipe's label and its full text.

Return ONLY a JSON object:
{"has_bad_measurement": true/false, "quote": "<exact offending phrase, or empty if false>", "why": "<one short sentence, or empty if false>"}

If the recipe looks normal, return has_bad_measurement: false."""

    main_prompt = """You have access to a recipe corpus at /my_corpus.txt.
Each recipe starts with a line formatted exactly as "=== RECIPE N ==="
(e.g. "=== RECIPE 1 ===").

Run a workflow that reads the file, splits it into individual recipes on
those headers, and dispatches one section-scanner subagent call per recipe.
Never load every recipe's full text into your own context; let the
interpreter hold the file, and let each subagent hold only its own recipe.
Collect the findings into one final report listing only the recipes flagged
with bad measurements, including the quote and why."""

    return scanner_prompt, main_prompt


SCANNER_PROMPT, MAIN_PROMPT = build_prompts()

section_scanner = {
    "name": "section-scanner",
    "description": (
        "Scan one section of the corpus for whatever the scanner prompt "
        "asks for. Delegate one section per call."
    ),
    "system_prompt": SCANNER_PROMPT,
    "model": model,
}

agent = create_deep_agent(
    model=strong_model,
    middleware=[CodeInterpreterMiddleware()],
    system_prompt=MAIN_PROMPT,
    subagents=[section_scanner],
    backend=FilesystemBackend(root_dir=DATA_DIR, virtual_mode=True),
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Run a workflow to scan every section of my_corpus.txt and report what you find.",
            }
        ]
    },
    config={"recursion_limit": 100},
)
print(result["messages"][-1].content)
