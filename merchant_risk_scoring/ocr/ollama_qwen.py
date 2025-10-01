"""OCR extraction utilities using the Ollama Qwen2.5 VLM endpoint."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Dict, Iterable, Optional

import requests

DEFAULT_PROMPT_TEMPLATE = """
You are extracting structured business KYC data from the provided document image.\n
Return a compact JSON object with the keys: {fields}.\n
If a value is missing, set it to null. Respond with JSON only.
""".strip()


class OllamaQwenExtractor:
    """Thin client around an Ollama vision-language endpoint for OCR + extraction."""

    def __init__(
        self,
        base_url: str = "http://localhost:11431",
        model: str = "qwen2.5-vl",
        timeout: int = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _encode_image(self, image: bytes | Path) -> str:
        if isinstance(image, Path):
            data = image.read_bytes()
        else:
            data = image
        return base64.b64encode(data).decode("utf-8")

    def _build_prompt(self, fields: Iterable[str], custom_prompt: Optional[str]) -> str:
        if custom_prompt:
            return custom_prompt
        return DEFAULT_PROMPT_TEMPLATE.format(fields=", ".join(fields))

    def extract_fields(
        self,
        image: bytes | Path,
        fields: Iterable[str],
        custom_prompt: Optional[str] = None,
        extra_instructions: Optional[str] = None,
    ) -> Dict[str, Optional[str]]:
        """Call the Ollama API to retrieve structured values for the requested fields."""

        encoded = self._encode_image(image)
        prompt = self._build_prompt(fields, custom_prompt)
        if extra_instructions:
            prompt = f"{prompt}\n{extra_instructions}"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [encoded],
            "format": "json",
        }

        response = requests.post(
            f"{self.base_url}/api/generate", json=payload, timeout=self.timeout
        )
        response.raise_for_status()
        raw_text = response.json().get("response")

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Ollama response is not valid JSON: {raw_text}") from exc

        # Ensure all requested keys exist
        return {field: parsed.get(field) for field in fields}

    def extract_freeform(
        self,
        image: bytes | Path,
        prompt: str,
    ) -> str:
        """Obtain a free-form response from the vision model for exploratory OCR."""

        encoded = self._encode_image(image)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [encoded],
        }
        response = requests.post(
            f"{self.base_url}/api/generate", json=payload, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json().get("response", "")
