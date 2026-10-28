from __future__ import annotations

import base64
import re
from typing import Any

from PIL import Image

from backend.copy_checker.services.vision_service import VisionService


class InMemoryVisionService(VisionService):
    """
    Vision inference service for PIL images already loaded in RAM.
    """

    @staticmethod
    def _extract_allowed_question_numbers(
        prompt: str,
    ) -> list[int] | None:
        """
        Extract question numbers explicitly requested
        for the current extraction pass.
        """

        patterns = [
            r"Authoritative question numbers for THIS PASS:"
            r"\s*((?:Q\s*\d+\s*,?\s*)+)",

            r"The authoritative MCQ question numbers are:"
            r"\s*((?:Q\s*\d+\s*,?\s*)+)",

            r"The authoritative non-MCQ question numbers are:"
            r"\s*((?:Q\s*\d+\s*,?\s*)+)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                prompt,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            numbers = [
                int(number)
                for number in re.findall(
                    r"Q\s*(\d+)",
                    match.group(1),
                    flags=re.IGNORECASE,
                )
            ]

            numbers = sorted(set(numbers))

            if numbers:
                return numbers

        return None

    def analyze_pil_image(
        self,
        image: Image.Image,
        prompt: str,
        *,
        max_dimension: int = 2048,
        jpeg_quality: int = 95,
        temperature: float = 0.0,
        extraction_mode: str = "general",
    ) -> dict[str, Any]:
        """
        Analyze an in-memory image using the configured vision model.

        Returns a dictionary containing:
            raw
            parsed
            model
            provider
            image_path
            image_source
        """

        if not isinstance(image, Image.Image):
            raise TypeError(
                "image must be a PIL.Image.Image instance."
            )

        if not prompt or not prompt.strip():
            raise ValueError(
                "Vision prompt must not be empty."
            )

        if extraction_mode not in {
            "general",
            "mcq",
        }:
            raise ValueError(
                f"Unsupported extraction mode: {extraction_mode}"
            )

        allowed_question_numbers = (
            self._extract_allowed_question_numbers(prompt)
        )

        print(
            "Schema allowed question numbers:",
            allowed_question_numbers,
        )

        # --------------------------------------------------------
        # Normalize image and encode it for the API
        # --------------------------------------------------------

        image_bytes = self.normalize_image(
            image=image,
            max_dimension=max_dimension,
            jpeg_quality=jpeg_quality,
        )

        encoded = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        image_url = (
            "data:image/jpeg;base64,"
            + encoded
        )

        # --------------------------------------------------------
        # MCQ structured-output schema
        # --------------------------------------------------------

        if extraction_mode == "mcq":
            extraction_schema = {
                "type": "json_schema",
                "json_schema": {
                    "name": "mcq_answer_sheet_extraction",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "page_number": {
                                "type": "integer"
                            },
                            "page_type": {
                                "type": "string"
                            },
                            "content": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "question_no": (
                                            {
                                                "type": "integer",
                                                "enum": (
                                                    allowed_question_numbers
                                                ),
                                            }
                                            if allowed_question_numbers
                                            else {
                                                "type": "integer"
                                            }
                                        ),
                                        "content_type": {
                                            "type": "string",
                                            "enum": ["answer"],
                                        },
                                        "text": {
                                            "type": "string",
                                            "enum": [
                                                "A",
                                                "B",
                                                "C",
                                                "D",
                                                "BLANK",
                                            ],
                                        },
                                        "confidence": {
                                            "type": "number"
                                        },
                                    },
                                    "required": [
                                        "question_no",
                                        "content_type",
                                        "text",
                                        "confidence",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                            "other_content": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "content_type": {
                                            "type": "string"
                                        },
                                        "text": {
                                            "type": "string"
                                        },
                                        "confidence": {
                                            "type": "number"
                                        },
                                    },
                                    "required": [
                                        "content_type",
                                        "text",
                                        "confidence",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                            "review_required": {
                                "type": "boolean"
                            },
                            "warnings": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                            },
                        },
                        "required": [
                            "page_number",
                            "page_type",
                            "content",
                            "other_content",
                            "review_required",
                            "warnings",
                        ],
                        "additionalProperties": False,
                    },
                },
            }

            model_max_tokens = 768

            system_prompt = (
                "You are a precise handwritten MCQ "
                "answer extraction system. "
                "For every answer item, text MUST be exactly "
                "one character: A, B, C, or D. "
                "Never repeat an option. "
                "Never copy question text. "
                "Never copy answer choices. "
                "Return JSON only."
            )

        # --------------------------------------------------------
        # General / subjective structured-output schema
        # --------------------------------------------------------

        else:
            extraction_schema = {
                "type": "json_schema",
                "json_schema": {
                    "name": "answer_sheet_extraction",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "page_number": {
                                "type": "integer"
                            },
                            "page_type": {
                                "type": "string"
                            },
                            "content": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "question_no": {
                                            "type": "integer"
                                        },
                                        "content_type": {
                                            "type": "string"
                                        },
                                        "text": {
                                            "type": "string"
                                        },
                                        "confidence": {
                                            "type": "number"
                                        },
                                    },
                                    "required": [
                                        "question_no",
                                        "content_type",
                                        "text",
                                        "confidence",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                            "other_content": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "content_type": {
                                            "type": "string"
                                        },
                                        "text": {
                                            "type": "string"
                                        },
                                        "confidence": {
                                            "type": "number"
                                        },
                                    },
                                    "required": [
                                        "content_type",
                                        "text",
                                        "confidence",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                            "review_required": {
                                "type": "boolean"
                            },
                            "warnings": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                            },
                        },
                        "required": [
                            "page_number",
                            "page_type",
                            "content",
                            "other_content",
                            "review_required",
                            "warnings",
                        ],
                        "additionalProperties": False,
                    },
                },
            }

            model_max_tokens = 1536

            system_prompt = (
                "You are a precise handwritten document "
                "extraction system. Follow the schema exactly. "
                "Return JSON only."
            )

        # --------------------------------------------------------
        # Call the vision model
        # --------------------------------------------------------

        try:
            response = (
                self.client
                .chat
                .completions
                .create(
                    model=self.model,
                    temperature=temperature,
                    max_tokens=model_max_tokens,
                    response_format=extraction_schema,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt,
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": image_url,
                                    },
                                },
                            ],
                        },
                    ],
                )
            )

        except Exception as exc:
            raise RuntimeError(
                "Vision model request failed for "
                "in-memory image.\n"
                f"Provider: {self.get_provider_name()}\n"
                f"Model: {self.get_model_name()}\n"
                f"Error: {exc}"
            ) from exc

        # --------------------------------------------------------
        # Validate the response
        # --------------------------------------------------------

        if not response.choices:
            raise RuntimeError(
                "Vision model returned no choices."
            )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:
            raise RuntimeError(
                "Vision model returned empty content."
            )

        # --------------------------------------------------------
        # Parse JSON and return a consistent response structure
        # --------------------------------------------------------

        parsed = self.parse_json_response(content)

        return {
            "raw": content,
            "parsed": parsed,
            "model": self.get_model_name(),
            "provider": self.get_provider_name(),
            "image_path": None,
            "image_source": "memory",
        }