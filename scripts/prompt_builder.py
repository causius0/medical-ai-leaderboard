#!/usr/bin/env python3
"""
Prompt Builder for Medical AI Leaderboard
Constructs prompts from templates and injects question data
"""

import json
import os
from typing import List, Dict, Any


def apply_image_descriptions(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Inject image descriptions into question text for test-time use.

    For every question carrying an `image_description` field (produced by
    scripts/build_enriched_dataset.py), appends a localized
    "[<label>: <description>]" line to the question text so text-only models
    can attempt image-dependent questions.

    Does not mutate the input list (returns shallow copies). Questions without
    a description are returned unchanged.
    """
    out = []
    for q in questions:
        description = q.get("image_description")
        if not description:
            out.append(q)
            continue
        label = q.get("image_description_label", "Image description")
        q2 = dict(q)
        q2["question"] = f"{q['question']}\n\n[{label}: {description}]"
        out.append(q2)
    return out


class PromptBuilder:
    """Builds prompts for OpenRouter API calls"""

    def __init__(self, template_path: str = None):
        """
        Initialize the prompt builder

        Args:
            template_path: Path to prompt template file
        """
        if template_path is None:
            # Default to docs/prompt.txt
            script_dir = os.path.dirname(os.path.abspath(__file__))
            repo_root = os.path.dirname(script_dir)
            template_path = os.path.join(repo_root, "docs", "prompt.txt")

        self.template_path = template_path
        self.template = self._load_template()

    def _load_template(self) -> str:
        """Load the prompt template from file"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template not found at: {self.template_path}")

    def build_prompt(self, questions: List[Dict[str, Any]]) -> str:
        """
        Build a complete prompt by injecting questions into the template

        Args:
            questions: List of question dictionaries

        Returns:
            Complete prompt as string
        """
        # Convert questions to JSON format for the prompt
        questions_json = json.dumps(questions, ensure_ascii=False, indent=2)

        # Append the questions to the template
        full_prompt = f"{self.template}\n\n```json\n{questions_json}\n```\n\nPlease answer ALL {len(questions)} questions above."

        return full_prompt

    def build_message(self, questions: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Build a message dictionary for the API call

        Args:
            questions: List of question dictionaries

        Returns:
            Message dict with 'role' and 'content'
        """
        prompt_content = self.build_prompt(questions)
        return {
            "role": "user",
            "content": prompt_content
        }

    def estimate_tokens(self, questions: List[Dict[str, Any]]) -> int:
        """
        Estimate the number of tokens in the prompt

        This is a rough estimate: ~4 characters per token

        Args:
            questions: List of question dictionaries

        Returns:
            Estimated token count
        """
        prompt = self.build_prompt(questions)
        # Rough estimate: 4 characters per token
        return len(prompt) // 4


if __name__ == "__main__":
    # Test the prompt builder
    builder = PromptBuilder()

    # Create sample questions
    sample_questions = [
        {
            "id": "IT0001",
            "question": "Sample question 1",
            "options": [
                {"letter": "A", "text": "Option A"},
                {"letter": "B", "text": "Option B"},
                {"letter": "C", "text": "Option C"},
                {"letter": "D", "text": "Option D"},
                {"letter": "E", "text": "Option E"}
            ]
        },
        {
            "id": "IT0002",
            "question": "Sample question 2",
            "options": [
                {"letter": "A", "text": "Option A"},
                {"letter": "B", "text": "Option B"},
                {"letter": "C", "text": "Option C"},
                {"letter": "D", "text": "Option D"},
                {"letter": "E", "text": "Option E"}
            ]
        }
    ]

    # Build prompt
    message = builder.build_message(sample_questions)

    print("Sample message content (first 500 chars):")
    print(message["content"][:500])
    print(f"\nEstimated tokens: {builder.estimate_tokens(sample_questions)}")
