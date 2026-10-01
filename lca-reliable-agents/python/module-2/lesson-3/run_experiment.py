from pathlib import Path

from dotenv import load_dotenv
from langsmith import evaluate

# Load repo-root .env (and cwd if present)
_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")
load_dotenv()


# Dummy "app" that always returns a response mentioning OfficeFlow
def dummy_app(inputs: dict) -> dict:
    return {"response": "Sure! In OfficeFlow, you can reset your password from the settings page."}


# Code-based Eval — check if the response mentions "officeflow"
def mentions_officeflow(outputs: dict) -> bool:
    return "officeflow" in outputs["response"].lower()


# Experiment
results = evaluate(
    dummy_app,
    data="officeflow-dataset",
    evaluators=[mentions_officeflow]
)
