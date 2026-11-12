import json
import logging
import mimetypes
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types, errors

from app.ai.llm.base import LLMClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiClient(LLMClient):

    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("Gemini API key is not configured.")

        self.client = genai.Client(
            api_key=settings.gemini_api_key,
        )

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        *,
        temperature: float = 0.2,
        max_output_tokens: int = 4096,
        images: list | None = None,
    ) -> dict:

        contents = [f"{system}\n\n{user}"]

        for image_path in images or []:
            path = Path(image_path)

            if not path.is_file():
                raise ValueError(f"Image not found: {path.name}")

            mime_type, _ = mimetypes.guess_type(str(path))

            if mime_type not in {
                "image/png",
                "image/jpeg",
                "image/webp",
            }:
                raise ValueError(f"Unsupported image: {path.name}")

            image_data = path.read_bytes()

            contents.append(
                types.Part.from_bytes(
                    data=image_data,
                    mime_type=mime_type,
                )
            )

        max_retries = max(0, settings.ai_max_retries)

        for attempt in range(max_retries + 1):
            try:
                logger.info(
                    "Gemini API call attempt %d/%d (model=%s).",
                    attempt + 1,
                    max_retries + 1,
                    settings.gemini_model,
                )

                response = self.client.models.generate_content(
                    model=settings.gemini_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_json_schema=schema,
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        http_options=types.HttpOptions(
                            timeout=settings.ai_timeout_seconds * 1000,
                        ),
                    ),
                )

                if not response.text:
                    raise ValueError("Gemini returned an empty response.")

                result = json.loads(response.text)

                if not isinstance(result, dict):
                    raise ValueError("Gemini response must be a JSON object.")

                logger.info("Gemini API call succeeded on attempt %d.", attempt + 1)
                return result

            except errors.APIError as exc:
                status_code = getattr(exc, "code", None)

                retryable = (
                    status_code == 429
                    or (
                        isinstance(status_code, int)
                        and 500 <= status_code <= 599
                    )
                )

                if not retryable or attempt == max_retries:
                    logger.error(
                        "Gemini API error (status=%s) on attempt %d, "
                        "not retrying: %s",
                        status_code,
                        attempt + 1,
                        exc,
                    )
                    raise

                delay = 1 if attempt == 0 else 3
                logger.warning(
                    "Gemini API error (status=%s) on attempt %d, "
                    "retrying in %ds.",
                    status_code,
                    attempt + 1,
                    delay,
                )

                time.sleep(delay)
