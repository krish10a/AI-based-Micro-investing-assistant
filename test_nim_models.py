"""
Test script to check which NVIDIA NIM models work with your API key.
Run this with: python test_nim_models.py
"""

from openai import OpenAI

# Your API key
API_KEY = "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"

# Models to test
MODELS = [
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.1-405b-instruct",
    "mistralai/mistral-large-3-675b-instruct-2512",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "google/gemma-7b-it",
    "microsoft/phi-3-medium-128k-instruct",
]

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=API_KEY
)

print("=" * 60)
print("NVIDIA NIM Model Tester")
print("=" * 60)
print()

for model in MODELS:
    print(f"Testing: {model}")
    print("-" * 40)
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello, respond with just 'OK'"}],
            temperature=0.2,
            top_p=0.7,
            max_tokens=50,
            stream=False
        )
        response = completion.choices[0].message.content
        print(f"  SUCCESS: {response.strip()}")
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg:
            print(f"  FAILED: Invalid API key or model not accessible")
        elif "404" in error_msg or "not found" in error_msg.lower():
            print(f"  FAILED: Model not found (404)")
        elif "400" in error_msg:
            print(f"  FAILED: Bad request (400) - model may not be enabled")
        else:
            print(f"  FAILED: {error_msg[:100]}")
    print()

print("=" * 60)
print("Testing complete!")
print("=" * 60)
