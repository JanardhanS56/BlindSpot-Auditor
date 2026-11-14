import asyncio
import logging
import math
from typing import Literal
import httpx
import config

logger = logging.getLogger(__name__)

NVIDIA_EMBED_URL = "https://integrate.api.nvidia.com/v1/embeddings"
DEFAULT_EMBED_MODEL = "nvidia/nemotron-3.5-embed-8b"


def l2_normalize(vec: list[float]) -> list[float]:
    """Normalizes vector to unit length (L2 norm = 1.0)."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


class NvidiaEmbedder:
    """NVIDIA Nemotron-3.5-Embed-8B client for generating dense embeddings."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_EMBED_MODEL,
        truncate_dim: int | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        self.api_key = api_key or config.NVIDIA_API_KEY
        self.model = model
        self.truncate_dim = truncate_dim
        self.timeout = timeout
        self.max_retries = max_retries

    async def embed_batch(
        self,
        texts: list[str],
        input_type: Literal["passage", "query"] = "passage",
    ) -> list[list[float]]:
        """Embeds a batch of texts using NVIDIA Nemotron embedding model."""
        if not texts:
            return []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Process in chunks of up to 16 to prevent payload limits
        chunk_size = 16
        all_embeddings: list[list[float]] = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for i in range(0, len(texts), chunk_size):
                sub_batch = texts[i : i + chunk_size]
                payload = {
                    "input": sub_batch,
                    "model": self.model,
                    "input_type": input_type,
                    "encoding_format": "float",
                }

                attempt = 0
                backoff = 1.0
                while attempt < self.max_retries:
                    try:
                        response = await client.post(
                            NVIDIA_EMBED_URL,
                            headers=headers,
                            json=payload,
                        )

                        if response.status_code == 200:
                            data = response.json()
                            embeddings_data = data.get("data", [])
                            # Sort by index to maintain ordering
                            embeddings_data.sort(key=lambda x: x.get("index", 0))

                            for item in embeddings_data:
                                vec = item["embedding"]
                                if self.truncate_dim and len(vec) > self.truncate_dim:
                                    vec = l2_normalize(vec[: self.truncate_dim])
                                all_embeddings.append(vec)
                            break

                        elif response.status_code in (429, 500, 502, 503, 504):
                            attempt += 1
                            logger.warning(
                                "NVIDIA API status %s on attempt %d/%d. Backoff %ss.",
                                response.status_code,
                                attempt,
                                self.max_retries,
                                backoff,
                            )
                            if attempt >= self.max_retries:
                                response.raise_for_status()
                            await asyncio.sleep(backoff)
                            backoff *= 2.0
                        else:
                            response.raise_for_status()

                    except (httpx.RequestError, httpx.HTTPStatusError) as req_err:
                        attempt += 1
                        logger.warning(
                            "NVIDIA API request failed (%s). Attempt %d/%d.",
                            req_err,
                            attempt,
                            self.max_retries,
                        )
                        if attempt >= self.max_retries:
                            raise
                        await asyncio.sleep(backoff)
                        backoff *= 2.0

        return all_embeddings

    async def embed(
        self,
        text: str,
        input_type: Literal["passage", "query"] = "passage",
    ) -> list[float]:
        """Embeds a single string and returns its vector."""
        results = await self.embed_batch([text], input_type=input_type)
        if not results:
            raise RuntimeError("No embedding returned from NVIDIA API")
        return results[0]
