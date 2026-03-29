#!/usr/bin/env python3
"""
Test script for Gemma 3 4B - single question test
"""

import os
import sys
import json
from pathlib import Path

# Load environment variables
repo_root = Path(__file__).parent.parent
env_file = repo_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Add scripts directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from openrouter_client import OpenRouterClient
from prompt_builder import PromptBuilder

def main():
    print("Testing Gemma 3 4B with single question...")

    # Load text-only questions
    questions_path = repo_root / "data" / "ssm_questions_text_only.json"

    with open(questions_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    # Take just the first question
    model_questions = []
    for q in questions[:1]:
        q_copy = q.copy()
        if 'correct_answer' in q_copy:
            del q_copy['correct_answer']
        model_questions.append(q_copy)

    print(f"Testing with {len(model_questions)} question(s)")

    # Initialize components
    client = OpenRouterClient()
    builder = PromptBuilder()

    # Model config
    model_id = "google/gemma-3-4b-it"  # Try without :free to avoid rate limits
    temperature = 0.7

    message = builder.build_message(model_questions)

    print(f"\nModel ID: {model_id}")
    print(f"Message length: {len(message['content'])} characters")

    try:
        print("\nSending test request to OpenRouter...")
        response = client.call_model(
            model=model_id,
            messages=[message],
            temperature=temperature,
            max_tokens=500
        )

        print("\n✅ Request successful!")
        print(f"Response status: {response.get('object', 'N/A')}")

        if 'choices' in response and len(response['choices']) > 0:
            content = response['choices'][0]['message']['content']
            print(f"\nResponse content (first 500 chars):\n{content[:500]}")

        if 'usage' in response:
            print(f"\nToken usage: {response['usage']}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
