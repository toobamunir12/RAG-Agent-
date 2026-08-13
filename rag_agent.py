import asyncio

import chromadb
import acruxcore as acrux
from dotenv import load_dotenv

from ingestion_pipeline import CHROMA_PATH, COLLECTION_NAME, get_embedding

load_dotenv()


@acrux.tool
async def search_docs(query: str) -> str:
    """Searches the UET Mardan undergraduate prospectus for passages relevant to the query."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(COLLECTION_NAME)
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3,
    )
    documents = results["documents"][0]
    context = "\n\n".join(documents)
    return context


async def ask(question: str) -> str:
    async with acrux.AcruxCore() as hub:
        rendered = await hub.prompts.render(
            "uet-rag-agent",
            "production",
            {"question": question},
        )
        result = await hub.gateway.run_tool_loop(
            model=rendered.model or "rag-model",
            messages=rendered.messages,
            tools=[search_docs],
            prompt_version_id=rendered.version_id,
        )
        return result.content or ""


if __name__ == "__main__":
    question = input("Ask a question about UET Mardan: ")
    answer = asyncio.run(ask(question))
    print("\nAnswer:")
    print(answer)
