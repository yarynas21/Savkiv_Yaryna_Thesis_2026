"""Robust JSON parser that handles LLM output with markdown formatting."""

import json
import re
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.outputs import Generation
from utils.logger import get_logger

logger = get_logger(__name__)


def _clean_and_parse_json(text: str) -> dict:
    original_text = text
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    text = text.replace("{{", "{").replace("}}", "}")

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON after markdown cleanup: {e}")
        logger.debug(f"Text that failed to parse: {text[:200]}")

        start_idx = text.find("{")
        end_idx = text.rfind("}")

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_candidate = text[start_idx:end_idx + 1]
            try:
                return json.loads(json_candidate)
            except json.JSONDecodeError:
                logger.debug("Failed to parse extracted JSON candidate")

        logger.error(f"Could not parse JSON. Original text: {original_text[:500]}")
        raise


class RobustJsonOutputParser(JsonOutputParser):
    """JSON parser that handles markdown formatting (double braces)."""

    def parse(self, text: str) -> dict:
        return _clean_and_parse_json(text)

    def parse_result(self, generations: list[Generation], *, partial: bool = False) -> Any:
        text = generations[0].text if generations else ""
        logger.debug(f"Parsing JSON from text: {text[:100]}...")

        try:
            return _clean_and_parse_json(text)
        except json.JSONDecodeError as e:
            msg = f"Invalid json output: {text}"
            raise OutputParserException(msg, llm_output=text) from e
