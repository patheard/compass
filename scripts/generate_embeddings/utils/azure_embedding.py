#!/usr/bin/env python3
"""
Azure OpenAI embedding utility.
"""

import logging
import time
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


def get_embedding(
    text: str,
    client: AzureOpenAI,
    model: str,
    max_retries: int = 3,
) -> list[float] | None:
    """Get embedding from Azure OpenAI with exponential backoff retry.

    Args:
        text: Text to embed
        client: AzureOpenAI client instance
        model: Model name to use for embeddings
        max_retries: Maximum number of retry attempts

    Returns:
        Embedding vector or None if all retries fail
    """
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                input=text,
                model=model,
            )
            return response.data[0].embedding
        except Exception as e:
            wait_time = 2**attempt  # Exponential backoff: 1, 2, 4 seconds
            logger.warning(
                f"Embedding API call failed (attempt {attempt + 1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("All retry attempts failed for text chunk")
                return None
    return None


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Test the function
    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )

    test_text = "This is a test string for embedding."
    embedding = get_embedding(
        test_text,
        client,
        os.getenv("AZURE_OPENAI_EMBEDDINGS_MODEL"),
    )

    if embedding:
        print(f"Successfully generated embedding with {len(embedding)} dimensions")
        print(f"First 5 values: {embedding[:5]}")
    else:
        print("Failed to generate embedding")
