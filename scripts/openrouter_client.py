#!/usr/bin/env python3
"""
OpenRouter API Client for Medical AI Leaderboard
Handles API communication with various OpenRouter-hosted models
"""

import requests
import json
import os
from typing import Dict, List, Optional, Any
import time


class OpenRouterClient:
    """Client for interacting with OpenRouter API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenRouter client

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not provided and OPENROUTER_API_KEY env var not set")

        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/causius/medical-ai-leaderboard",
            "X-Title": "Medical AI Leaderboard"
        }

    def call_model(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        retry_attempts: int = 3,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        Call an OpenRouter model with the given messages

        Args:
            model: Model identifier (e.g., "qwen/qwen3.5-flash-02-23")
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            response_format: Optional JSON schema for structured output
            retry_attempts: Number of retry attempts on failure
            retry_delay: Delay between retries in seconds

        Returns:
            API response as dictionary

        Raises:
            Exception: If all retry attempts fail
        """
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        if response_format:
            payload["response_format"] = response_format

        for attempt in range(retry_attempts):
            try:
                response = requests.post(url, headers=self.headers, json=payload, timeout=120)

                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', retry_delay))
                    print(f"Rate limited. Waiting {retry_after}s before retry...")
                    time.sleep(retry_after)
                    continue

                # Check for other errors
                if response.status_code >= 500:
                    print(f"Server error ({response.status_code}). Retrying {attempt + 1}/{retry_attempts}...")
                    time.sleep(retry_delay)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout:
                print(f"Timeout on attempt {attempt + 1}/{retry_attempts}")
                if attempt < retry_attempts - 1:
                    time.sleep(retry_delay)
                else:
                    raise Exception("Request timed out after all retry attempts")

            except requests.exceptions.RequestException as e:
                print(f"Request error on attempt {attempt + 1}/{retry_attempts}: {e}")
                if attempt < retry_attempts - 1:
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Request failed after all retry attempts: {e}")

        raise Exception(f"Failed to complete request after {retry_attempts} attempts")

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        Get information about a specific model

        Args:
            model: Model identifier

        Returns:
            Model information dictionary
        """
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            models = response.json()['data']

            for m in models:
                if m['id'] == model:
                    return m

            raise ValueError(f"Model {model} not found")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch model info: {e}")

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate the cost of an API call

        Args:
            model: Model identifier
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        try:
            model_info = self.get_model_info(model)
            prompt_price = float(model_info['pricing']['prompt'])
            completion_price = float(model_info['pricing']['completion'])

            prompt_cost = prompt_tokens * prompt_price
            completion_cost = completion_tokens * completion_price

            return prompt_cost + completion_cost

        except Exception as e:
            print(f"Warning: Could not estimate cost: {e}")
            return 0.0


if __name__ == "__main__":
    # Test the client
    client = OpenRouterClient()

    # Print account info
    print("Testing OpenRouter client...")
    print(f"API Key: {client.api_key[:20]}...")

    # Test a simple call
    test_messages = [
        {"role": "user", "content": "What is 2+2? Reply with just the number."}
    ]

    try:
        response = client.call_model(
            model="qwen/qwen3.5-flash-02-23",
            messages=test_messages,
            max_tokens=10
        )
        print("\nTest successful!")
        print(f"Response: {response['choices'][0]['message']['content']}")
    except Exception as e:
        print(f"\nTest failed: {e}")
