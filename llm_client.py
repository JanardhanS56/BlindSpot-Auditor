import asyncio
import logging
from typing import Any
import groq
from groq import APIConnectionError, APIStatusError, AsyncGroq, RateLimitError
from config import DEFAULT_MODEL, GROQ_API_KEY, MAX_RETRIES

logger = logging.getLogger(__name__)


class GroqLLMClient:
    def __init__(self, api_key: str | None = None, default_model: str = DEFAULT_MODEL):
        self.api_key = api_key or GROQ_API_KEY
        self.client = AsyncGroq(api_key=self.api_key)
        self.default_model = default_model
        self.last_metadata: dict[str, Any] = {}
        self._fallback_model: str | None = None

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> str:
        target_model = model or self._fallback_model or self.default_model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        attempt = 0
        backoff = 2.0
        current_max_tokens = max_tokens

        while attempt < MAX_RETRIES:
            try:
                response = await self.client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=current_max_tokens,
                )
                choice = response.choices[0]
                content = choice.message.content or ""

                usage = getattr(response, "usage", None)
                self.last_metadata = {
                    "model": target_model,
                    "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                    "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
                    "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
                }
                return content
            except groq.NotFoundError as e:
                logger.warning("Model %s not found on Groq. Checking fallback.", target_model)
                if self._fallback_model is None:
                    try:
                        models_resp = await self.client.models.list()
                        available = [m.id for m in models_resp.data]
                        preferred = [
                            "openai/gpt-oss-120b",
                            "openai/gpt-oss-20b",
                            "qwen/qwen3.8-27b",
                        ]
                        chosen = next(
                            (m for m in preferred if m in available),
                            available[0] if available else None,
                        )
                        if chosen:
                            self._fallback_model = chosen
                            self.default_model = chosen
                    except Exception as list_err:
                        logger.error("Failed to query models list: %s", list_err)
                if self._fallback_model:
                    target_model = self._fallback_model
                    logger.info("Retrying with fallback model: %s", self._fallback_model)
                    continue
                raise e
            except (RateLimitError, APIConnectionError) as e:
                attempt += 1
                # If OTPM limit exceeded, cut max_tokens to fit
                err_str = str(e)
                if "output tokens per minute" in err_str or "OTPM" in err_str:
                    current_max_tokens = min(current_max_tokens, 500)
                logger.warning(
                    "Groq API error (%s). Attempt %s/%s. Backing off %ss (max_tokens=%s).",
                    e,
                    attempt,
                    MAX_RETRIES,
                    backoff,
                    current_max_tokens,
                )
                if attempt >= MAX_RETRIES:
                    raise
                await asyncio.sleep(backoff)
                backoff *= 2.0
            except APIStatusError as e:
                if e.status_code >= 500:
                    attempt += 1
                    logger.warning(
                        "Groq status %s. Attempt %s/%s. Backing off %ss.",
                        e.status_code,
                        attempt,
                        MAX_RETRIES,
                        backoff,
                    )
                    if attempt >= MAX_RETRIES:
                        raise
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                else:
                    raise

        raise RuntimeError(f"Failed to complete Groq request after {MAX_RETRIES} attempts.")

    async def close(self):
        await self.client.close()


# Default singleton instance
default_llm_client = GroqLLMClient()


async def chat(
    system_prompt: str,
    user_message: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
) -> str:
    """Module-level chat convenience function."""
    return await default_llm_client.chat(
        system_prompt=system_prompt,
        user_message=user_message,
        model=model,
        temperature=temperature,
    )
