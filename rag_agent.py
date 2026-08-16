import asyncio
from dataclasses import dataclass
from typing import Optional

import chromadb
import acruxcore as acrux
from dotenv import load_dotenv

from ingestion_pipeline import CHROMA_PATH, COLLECTION_NAME, get_embedding

load_dotenv()


@dataclass
class AskResult:
    """Answer plus the Acrux Core trace it was produced under.

    ``trace_id`` is what the frontend sends back with a 👍/👎 so feedback
    lands on the exact trace that produced this answer.
    """

    answer: str
    trace_id: Optional[str]


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


async def ask(question: str) -> AskResult:
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
        return AskResult(answer=result.content or "", trace_id=result.trace_id)


async def submit_answer_feedback(
    trace_id: str,
    rating: int,
    comment: Optional[str] = None,
) -> None:
    """Send a 👍/👎 (rating = 1 or -1) on a previous answer's trace to Acrux Core."""
    async with acrux.AcruxCore() as hub:
        await hub.traces.submit_feedback(
            trace_id,
            rating=rating,
            source="end_user",
            comment=comment,
        )


if __name__ == "__main__":
    question = input("Ask a question about UET Mardan: ")
    result = asyncio.run(ask(question))
    print("\nAnswer:")
    print(result.answer)
