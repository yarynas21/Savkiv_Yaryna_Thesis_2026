"""
Robust JSON Parser
==================
Handles JSON parsing with markdown formatting support (double braces).
"""

import json
import re
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.outputs import Generation
from utils.logger import get_logger

logger = get_logger(__name__)


def _clean_and_parse_json(text: str) -> dict:
    """Clean markdown formatting and parse JSON."""
    original_text = text
    
    # Remove markdown code blocks if present
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    
    # Replace double braces with single braces (markdown escaping)
    text = text.replace("{{", "{").replace("}}", "}")
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON after markdown cleanup: {e}")
        logger.debug(f"Text that failed to parse: {text[:200]}")
        
        # Try to extract JSON object from text using a more robust approach
        # Find the first { and last } and try to parse that
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_candidate = text[start_idx:end_idx + 1]
            try:
                return json.loads(json_candidate)
            except json.JSONDecodeError:
                logger.debug("Failed to parse extracted JSON candidate")
        
        # Last resort: log the original text for debugging
        logger.error(f"Could not parse JSON. Original text: {original_text[:500]}")
        raise


class RobustJsonOutputParser(JsonOutputParser):
    """JSON parser that handles markdown formatting (double braces)."""
    
    def parse(self, text: str) -> dict:
        """Parse JSON, handling markdown formatting."""
        return _clean_and_parse_json(text)
    
    def parse_result(self, generations: list[Generation], *, partial: bool = False) -> Any:
        """Parse the output from LLM, handling markdown formatting."""
        text = generations[0].text if generations else ""
        logger.debug(f"Parsing JSON from text: {text[:100]}...")
        
        try:
            return _clean_and_parse_json(text)
        except json.JSONDecodeError as e:
            msg = f"Invalid json output: {text}"
            raise OutputParserException(msg, llm_output=text) from e
