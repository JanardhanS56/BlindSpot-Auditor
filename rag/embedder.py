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
        timeout: float = 15.0,
        max_retries: int = 2,
    ):
        self.api_key = api_key or config.NVIDIA_API_KEY
        self.model = model
        if truncate_dim is not None:
            self.truncate_dim = truncate_dim
        elif getattr(config, "EMBEDDING_TRUNCATE", False):
            self.truncate_dim = getattr(config, "EMBEDDING_DIM", 1024)
        else:
            self.truncate_dim = None
        self.timeout = timeout
        self.max_retries = max_retries
        self._cache: dict[tuple[str, str], list[float]] = {}

    async def embed_batch(
        self,
        texts: list[str],
        input_type: Literal["passage", "query"] = "passage",
    ) -> list[list[float]]:
        """Embeds a batch of texts using NVIDIA Nemotron embedding model with local cache."""
        if not texts:
            return []

        # Check cache first for all texts
        uncached_indices = []
        uncached_texts = []
        results: list[list[float] | None] = [None] * len(texts)

        for idx, text in enumerate(texts):
            cache_key = (text, input_type)
            if cache_key in self._cache:
                results[idx] = self._cache[cache_key]
            else:
                uncached_indices.append(idx)
                uncached_texts.append(text)

        if not uncached_texts:
            return [vec for vec in results if vec is not None]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Process in chunks of up to 16 to prevent payload limits
        chunk_size = 16
        fetched_embeddings: list[list[float]] = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for i in range(0, len(uncached_texts), chunk_size):
                sub_batch = uncached_texts[i : i + chunk_size]
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
                            embeddings_data.sort(key=lambda x: x.get("index", 0))

                            for item in embeddings_data:
                                vec = item["embedding"]
                                if self.truncate_dim and len(vec) > self.truncate_dim:
                                    vec = l2_normalize(vec[: self.truncate_dim])
                                fetched_embeddings.append(vec)
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

        for original_idx, vec in zip(uncached_indices, fetched_embeddings):
            self._cache[(texts[original_idx], input_type)] = vec
            results[original_idx] = vec

        return [vec for vec in results if vec is not None]

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
