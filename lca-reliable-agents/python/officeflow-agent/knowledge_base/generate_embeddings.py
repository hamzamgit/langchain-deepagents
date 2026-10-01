"""Pre-generate embeddings for the knowledge base to speed up agent startup."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llm_client import client, EMBEDDING_MODEL

DOCS_DIR = "./documents"
EMBEDDINGS_DIR = "./embeddings"


async def generate_embeddings():
    """Generate embeddings for whole documents."""
    docs_path = Path(DOCS_DIR)
    embeddings_path = Path(EMBEDDINGS_DIR)

    docs = []
    for file_path in docs_path.glob("*.md"):
        if file_path.name == "CHUNKING_NOTES.md":
            continue
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            docs.append((file_path.name, content))

    print(f"Generating embeddings for {len(docs)} documents...")
    embeddings = []
    for filename, content in docs:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=content
        )
        embeddings.append(response.data[0].embedding)
        print(f"  {filename}")

    cache_data = {
        "docs": docs,
        "embeddings": embeddings
    }
    cache_path = embeddings_path / "embeddings.json"
    with open(cache_path, 'w') as f:
        json.dump(cache_data, f)
    print(f"\nSaved embeddings to {cache_path}")


async def main():
    await generate_embeddings()
    print("\nDone! Agents will now load embeddings from cache.")


if __name__ == "__main__":
    asyncio.run(main())
