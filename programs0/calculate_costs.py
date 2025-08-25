#!/usr/bin/env python3
"""
OpenAI Cost Calculator

Simple tool to calculate costs for OpenAI API usage
"""

import sys
from typing import Dict, Any


OPENAI_PRICING = {
    # GPT-4 models
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    
    # GPT-3.5 models
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    
    # o1 models
    "o1-mini": {"input": 3.00, "output": 12.00},
    "o1-preview": {"input": 15.00, "output": 60.00},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int = 0) -> Dict[str, Any]:
    """Calculate cost for given model and token usage"""
    if model not in OPENAI_PRICING:
        print(f"Model '{model}' not found in pricing table.")
        print("Available models:")
        for m in OPENAI_PRICING.keys():
            pricing = OPENAI_PRICING[m]
            print(f"  {m}: ${pricing['input']:.2f}/${pricing['output']:.2f} per 1M tokens")
        return {}
    
    pricing = OPENAI_PRICING[model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost
    
    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(total_cost, 6)
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python calculate_costs.py <model> <input_tokens> [output_tokens]")
        print("Example: python calculate_costs.py gpt-4o-mini 1000 500")
        print("\nAvailable models:")
        for model in OPENAI_PRICING.keys():
            pricing = OPENAI_PRICING[model]
            print(f"  {model}: ${pricing['input']:.2f} input, ${pricing['output']:.2f} output per 1M tokens")
        sys.exit(1)
    
    model = sys.argv[1]
    try:
        input_tokens = int(sys.argv[2])
        output_tokens = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    except ValueError:
        print("Error: Token counts must be integers")
        sys.exit(1)
    
    result = calculate_cost(model, input_tokens, output_tokens)
    if result:
        print(f"\nCost Calculation for {model}:")
        print(f"Input tokens: {result['input_tokens']:,} @ ${OPENAI_PRICING[model]['input']:.2f}/1M = ${result['input_cost']:.6f}")
        print(f"Output tokens: {result['output_tokens']:,} @ ${OPENAI_PRICING[model]['output']:.2f}/1M = ${result['output_cost']:.6f}")
        print(f"Total tokens: {result['total_tokens']:,}")
        print(f"Total cost: ${result['total_cost']:.6f}")


if __name__ == "__main__":
    main()