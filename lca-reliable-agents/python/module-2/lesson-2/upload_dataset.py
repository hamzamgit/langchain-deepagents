"""Upload officeflow-dataset.csv to LangSmith as 'officeflow-dataset'.

Usage (from python/):
    uv run python module-2/lesson-2/upload_dataset.py
"""
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client

_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")
load_dotenv()

DATASET_NAME = "officeflow-dataset"
CSV_PATH = Path(__file__).resolve().parent / "officeflow-dataset.csv"


def main() -> None:
    client = Client()

    try:
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
        print(f"Dataset already exists: {dataset.name} ({dataset.id})")
    except Exception:
        dataset = client.upload_csv(
            csv_file=str(CSV_PATH),
            input_keys=["question"],
            output_keys=[],
            name=DATASET_NAME,
            description="OfficeFlow eval questions from module-2 lesson-2",
            data_type="kv",
        )
        print(f"Created dataset: {dataset.name} ({dataset.id})")

    examples = list(client.list_examples(dataset_id=dataset.id))
    print(f"Examples: {len(examples)}")


if __name__ == "__main__":
    main()
