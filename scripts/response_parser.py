#!/usr/bin/env python3
"""
Response Parser for Medical AI Leaderboard
Extracts and validates JSON responses from OpenRouter models
"""

import json
import re
from typing import Dict, List, Any, Optional


class ResponseParser:
    """Parses and validates model responses"""

    def __init__(self, expected_question_ids: List[str] = None):
        """
        Initialize the response parser

        Args:
            expected_question_ids: List of expected question IDs for validation
        """
        self.expected_question_ids = set(expected_question_ids) if expected_question_ids else None

    def parse_response(self, response_text: str) -> Dict[str, str]:
        """
        Parse the model response and extract answer JSON

        Args:
            response_text: Raw response text from the model

        Returns:
            Dictionary mapping question IDs to answers

        Raises:
            ValueError: If response cannot be parsed or is invalid
        """
        # Try to extract JSON from the response
        json_data = self._extract_json(response_text)

        # Validate the structure
        answers = self._validate_answers(json_data)

        return answers

    def _extract_json(self, response_text: str) -> Any:
        """
        Extract JSON from response text

        Handles JSON in markdown code blocks or plain JSON
        Also handles function call format: {'name': 'json', 'arguments': {...}}

        Args:
            response_text: Raw response text

        Returns:
            Parsed JSON data

        Raises:
            ValueError: If JSON cannot be extracted or parsed
        """
        # Helper function to unwrap function calls recursively
        def unwrap_function_calls(data: Any, max_depth: int = 5, current_depth: int = 0) -> Any:
            """Recursively unwrap function call structures"""
            if current_depth >= max_depth:
                return data

            if isinstance(data, dict) and 'name' in data and 'arguments' in data:
                # Unwrap one level and recurse
                return unwrap_function_calls(data['arguments'], max_depth, current_depth + 1)

            # If it's a list, try to unwrap each element
            if isinstance(data, list):
                unwrapped_list = []
                for item in data:
                    unwrapped = unwrap_function_calls(item, max_depth, current_depth)
                    unwrapped_list.append(unwrapped)
                return unwrapped_list

            # If it's a dict, try to unwrap each value
            if isinstance(data, dict):
                unwrapped_dict = {}
                for key, value in data.items():
                    unwrapped_dict[key] = unwrap_function_calls(value, max_depth, current_depth)
                return unwrapped_dict

            return data

        # First, try to find JSON in markdown code blocks
        json_pattern = r'```(?:json)?\s*\n?([\s\S]*?)\n?```'
        matches = re.findall(json_pattern, response_text)

        if matches:
            # Try each match
            for match in matches:
                try:
                    data = json.loads(match.strip())
                    return unwrap_function_calls(data)
                except json.JSONDecodeError:
                    continue

        # If no code blocks, try parsing the entire response as JSON
        try:
            data = json.loads(response_text.strip())
            return unwrap_function_calls(data)
        except json.JSONDecodeError:
            pass

        # Try to find a JSON object anywhere in the text
        json_obj_pattern = r'\{[\s\S]*\}'
        matches = re.findall(json_obj_pattern, response_text)

        for match in matches:
            try:
                data = json.loads(match)
                return unwrap_function_calls(data)
            except json.JSONDecodeError:
                continue

        raise ValueError("Could not extract valid JSON from response")

    def _validate_answers(self, data: Any) -> Dict[str, str]:
        """
        Validate the structure of answers

        Args:
            data: Parsed JSON data

        Returns:
            Dictionary mapping question IDs to answers

        Raises:
            ValueError: If data structure is invalid
        """
        # Helper function to check if a dict is a wrapper (contains data but not an answer item)
        def is_wrapper_dict(item: Any) -> bool:
            """Check if dict is a wrapper containing data, not an answer item"""
            if not isinstance(item, dict):
                return False
            # Answer items have 'id' and 'answer' fields
            if 'id' in item and 'answer' in item:
                return False
            # Wrapper dicts have fields like 'data', 'content', 'results', 'total', 'metadata', etc.
            data_fields = {'data', 'content', 'results', 'answers', 'response', 'items', 'list'}
            return bool(data_fields & set(item.keys()))

        # Helper function to extract list from wrapper dict
        def extract_from_wrapper(wrapper: dict) -> Any:
            """Extract the actual list from a wrapper dict"""
            for field in ['data', 'content', 'results', 'answers', 'response', 'items', 'list']:
                if field in wrapper:
                    return wrapper[field]
            return wrapper

        # Handle different response formats
        if isinstance(data, dict):
            # Try common field names for answers
            if 'answers' in data:
                answers_list = data['answers']
            elif 'response' in data:
                answers_list = data['response']
            elif 'data' in data:
                answers_list = data['data']
            elif 'results' in data:
                answers_list = data['results']
            elif 'content' in data:
                answers_list = data['content']
            else:
                # Might be a direct mapping
                answers_list = data
        elif isinstance(data, list):
            answers_list = data
        else:
            raise ValueError(f"Unexpected data type: {type(data)}")

        # Flatten nested wrapper structures in lists
        if isinstance(answers_list, list):
            flattened = []
            for item in answers_list:
                if is_wrapper_dict(item):
                    # Extract data from wrapper and add to flattened list
                    extracted = extract_from_wrapper(item)
                    if isinstance(extracted, list):
                        flattened.extend(extracted)
                    else:
                        flattened.append(extracted)
                else:
                    flattened.append(item)
            answers_list = flattened

        # Convert to dict if it's a list
        if isinstance(answers_list, list):
            answers = {}
            for item in answers_list:
                # Handle both 'id' and 'question_id' field names
                if isinstance(item, dict):
                    qid_field = None
                    if 'id' in item and 'answer' in item:
                        qid_field = 'id'
                    elif 'question_id' in item and 'answer' in item:
                        qid_field = 'question_id'

                    if qid_field:
                        q_id = item[qid_field]
                        answer = item['answer']
                        answers[q_id] = answer
                    else:
                        raise ValueError(f"Invalid answer item: {item}")
                else:
                    raise ValueError(f"Invalid answer item (not a dict): {item}")
        else:
            answers = answers_list

        # Validate answer format
        for q_id, answer in answers.items():
            if not isinstance(answer, str) or answer not in ['A', 'B', 'C', 'D', 'E']:
                raise ValueError(f"Invalid answer format for {q_id}: {answer} (expected A, B, C, D, or E)")

        # Validate question IDs if expected set is provided
        if self.expected_question_ids:
            missing_ids = self.expected_question_ids - set(answers.keys())
            if missing_ids:
                print(f"Warning: Missing answers for {len(missing_ids)} questions")
                # Don't raise error, just warn

        return answers

    def format_for_evaluation(self, answers: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Format answers for the evaluation script

        Args:
            answers: Dictionary mapping question IDs to answers

        Returns:
            List of dicts with 'id' and 'answer' keys
        """
        return [
            {"id": q_id, "answer": answer}
            for q_id, answer in answers.items()
        ]


if __name__ == "__main__":
    # Test the response parser
    parser = ResponseParser(expected_question_ids=["IT0001", "IT0002"])

    # Test valid response
    test_response_1 = '''
```json
{
  "answers": [
    {"id": "IT0001", "answer": "A"},
    {"id": "IT0002", "answer": "C"}
  ]
}
```
'''

    try:
        answers = parser.parse_response(test_response_1)
        print("Test 1 passed!")
        print(f"Answers: {answers}")
    except Exception as e:
        print(f"Test 1 failed: {e}")

    # Test response without code blocks
    test_response_2 = '{"answers": [{"id": "IT0001", "answer": "B"}, {"id": "IT0002", "answer": "D"}]}'

    try:
        answers = parser.parse_response(test_response_2)
        print("\nTest 2 passed!")
        print(f"Answers: {answers}")
    except Exception as e:
        print(f"\nTest 2 failed: {e}")

    # Test invalid answer
    test_response_3 = '{"answers": [{"id": "IT0001", "answer": "X"}]}'

    try:
        answers = parser.parse_response(test_response_3)
        print("\nTest 3 passed!")
        print(f"Answers: {answers}")
    except Exception as e:
        print(f"\nTest 3 failed (expected): {e}")
