#!/usr/bin/env python3
"""
OpenAI billing and usage cost checker

This program provides multiple ways to check OpenAI API usage costs:
1. Direct API billing endpoints (requires admin permissions)
2. Usage tracking with cost calculations
3. Manual usage estimation tools
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import requests
from openai import OpenAI


# OpenAI pricing as of 2025 (USD per 1M tokens)
OPENAI_PRICING = {
    # GPT-4 models
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-4-0613": {"input": 30.00, "output": 60.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4-turbo-preview": {"input": 10.00, "output": 30.00},
    "gpt-4-0125-preview": {"input": 10.00, "output": 30.00},
    "gpt-4-1106-preview": {"input": 10.00, "output": 30.00},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o-2024-05-13": {"input": 5.00, "output": 15.00},
    "gpt-4o-2024-08-06": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
    
    # GPT-3.5 models
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "gpt-3.5-turbo-0125": {"input": 0.50, "output": 1.50},
    "gpt-3.5-turbo-1106": {"input": 1.00, "output": 2.00},
    "gpt-3.5-turbo-instruct": {"input": 1.50, "output": 2.00},
    
    # o1 models
    "o1-mini": {"input": 3.00, "output": 12.00},
    "o1-preview": {"input": 15.00, "output": 60.00},
    
    # Embedding models
    "text-embedding-3-small": {"input": 0.02, "output": 0.00},
    "text-embedding-3-large": {"input": 0.13, "output": 0.00},
    "text-embedding-ada-002": {"input": 0.10, "output": 0.00},
    
    # Image models (per image)
    "dall-e-3": {"standard": 0.040, "hd": 0.080},  # 1024x1024
    "dall-e-2": {"standard": 0.020},  # 1024x1024
    
    # Audio models
    "whisper-1": {"per_minute": 0.006},
    "tts-1": {"per_1k_chars": 0.015},
    "tts-1-hd": {"per_1k_chars": 0.030},
}


class OpenAIBillingChecker:
    """OpenAI billing and cost checker"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.usage_log = []
    
    def check_subscription_info(self) -> Dict[str, Any]:
        """Check subscription and billing information"""
        endpoints_to_try = [
            "/dashboard/billing/subscription",
            "/dashboard/billing/usage",
            "/dashboard/billing/credit_grants",
            "/billing/subscription",
            "/billing/usage",
            "/billing/credit_grants"
        ]
        
        results = {}
        
        for endpoint in endpoints_to_try:
            try:
                response = requests.get(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results[endpoint] = {
                        "success": True,
                        "data": data
                    }
                else:
                    results[endpoint] = {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text[:200]
                    }
            except Exception as e:
                results[endpoint] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    def check_usage_with_costs(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Check usage with cost calculations"""
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        endpoints_to_try = [
            f"/dashboard/billing/usage?start_date={start_date}&end_date={end_date}",
            f"/usage?start_date={start_date}&end_date={end_date}",
            f"/dashboard/billing/usage?date={start_date}",
            f"/usage?date={start_date}"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                response = requests.get(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    usage_data = response.json()
                    return {
                        "success": True,
                        "endpoint": endpoint,
                        "start_date": start_date,
                        "end_date": end_date,
                        "usage_data": usage_data,
                        "estimated_cost": self.calculate_cost_from_usage(usage_data)
                    }
                    
            except Exception as e:
                continue
        
        return {
            "success": False,
            "error": "Unable to access usage data with any available endpoint",
            "endpoints_tried": endpoints_to_try
        }
    
    def calculate_cost_from_usage(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate costs from usage data"""
        if not usage_data or "data" not in usage_data:
            return {"error": "Invalid usage data format"}
        
        total_cost = 0.0
        breakdown = {}
        
        for entry in usage_data.get("data", []):
            if "snapshot_id" in entry:
                # Handle daily usage snapshots
                for line_item in entry.get("line_items", []):
                    model = line_item.get("name", "unknown")
                    cost = line_item.get("cost", 0) / 100  # Convert cents to dollars
                    total_cost += cost
                    breakdown[model] = breakdown.get(model, 0) + cost
        
        return {
            "total_cost_usd": round(total_cost, 4),
            "breakdown_by_model": breakdown,
            "period": f"{usage_data.get('start_date', 'unknown')} to {usage_data.get('end_date', 'unknown')}"
        }
    
    def estimate_cost_from_tokens(self, model: str, prompt_tokens: int, completion_tokens: int = 0) -> Dict[str, Any]:
        """Estimate cost from token usage"""
        if model not in OPENAI_PRICING:
            return {
                "error": f"Pricing not available for model: {model}",
                "available_models": list(OPENAI_PRICING.keys())
            }
        
        pricing = OPENAI_PRICING[model]
        
        # Calculate costs (pricing is per 1M tokens)
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        return {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "total_cost_usd": round(total_cost, 6),
            "pricing_per_1m_tokens": pricing
        }
    
    def track_usage_with_test_calls(self, models_to_test: List[str] = None) -> Dict[str, Any]:
        """Track usage by making test calls and calculating costs"""
        if models_to_test is None:
            models_to_test = ["gpt-3.5-turbo", "gpt-4o-mini"]
        
        results = []
        total_estimated_cost = 0.0
        
        for model in models_to_test:
            try:
                print(f"Testing model: {model}")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Hello, what's the weather like?"}],
                    max_tokens=10
                )
                
                if response.usage:
                    cost_estimate = self.estimate_cost_from_tokens(
                        model,
                        response.usage.prompt_tokens,
                        response.usage.completion_tokens
                    )
                    
                    results.append({
                        "model": model,
                        "success": True,
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        },
                        "cost_estimate": cost_estimate,
                        "response_preview": response.choices[0].message.content[:50] if response.choices else ""
                    })
                    
                    if "total_cost_usd" in cost_estimate:
                        total_estimated_cost += cost_estimate["total_cost_usd"]
                
            except Exception as e:
                results.append({
                    "model": model,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "test_results": results,
            "total_estimated_cost_usd": round(total_estimated_cost, 6),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_comprehensive_billing_report(self) -> Dict[str, Any]:
        """Get comprehensive billing and usage report"""
        print("Generating comprehensive billing report...")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "api_key": f"{self.api_key[:8]}...{self.api_key[-4:]}",
            "checks": {}
        }
        
        # 1. Check subscription info
        print("1. Checking subscription and billing information...")
        report["checks"]["subscription_info"] = self.check_subscription_info()
        
        # 2. Check usage with costs
        print("2. Checking usage data...")
        report["checks"]["usage_data"] = self.check_usage_with_costs()
        
        # 3. Track usage with test calls
        print("3. Testing models and calculating costs...")
        report["checks"]["test_usage"] = self.track_usage_with_test_calls()
        
        # 4. Add pricing reference
        report["pricing_reference"] = OPENAI_PRICING
        
        return report
    
    def display_billing_report(self, report: Dict[str, Any]):
        """Display billing report in formatted way"""
        print("\n" + "="*80)
        print("OpenAI Billing and Usage Cost Report")
        print("="*80)
        print(f"Generated: {report['timestamp']}")
        print(f"API Key: {report['api_key']}")
        print("="*80)
        
        # Subscription Info
        sub_info = report["checks"]["subscription_info"]
        print(f"\n💳 Billing Information Access:")
        successful_endpoints = [ep for ep, data in sub_info.items() if data.get("success")]
        
        if successful_endpoints:
            print("   ✅ Successfully accessed billing data from:")
            for endpoint in successful_endpoints:
                print(f"     - {endpoint}")
                data = sub_info[endpoint]["data"]
                if "hard_limit_usd" in data:
                    print(f"       Hard Limit: ${data['hard_limit_usd']}")
                if "soft_limit_usd" in data:
                    print(f"       Soft Limit: ${data['soft_limit_usd']}")
                if "total_usage" in data:
                    print(f"       Total Usage: ${data['total_usage']}")
        else:
            print("   ❌ No billing endpoints accessible (requires admin permissions)")
            print("   Available alternatives:")
            print("     - Use OpenAI Dashboard: https://platform.openai.com/usage")
            print("     - Contact organization admin for billing access")
        
        # Usage Data
        usage_data = report["checks"]["usage_data"]
        print(f"\n📊 Usage Data:")
        if usage_data["success"]:
            print("   ✅ Usage data retrieved successfully")
            print(f"   Endpoint: {usage_data['endpoint']}")
            print(f"   Period: {usage_data['start_date']} to {usage_data['end_date']}")
            
            if "estimated_cost" in usage_data:
                cost_info = usage_data["estimated_cost"]
                if "total_cost_usd" in cost_info:
                    print(f"   💰 Total Cost: ${cost_info['total_cost_usd']}")
                    if "breakdown_by_model" in cost_info:
                        print("   Cost Breakdown:")
                        for model, cost in cost_info["breakdown_by_model"].items():
                            print(f"     - {model}: ${cost:.4f}")
        else:
            print("   ❌ Usage data not accessible")
            print(f"   Error: {usage_data['error']}")
        
        # Test Usage
        test_usage = report["checks"]["test_usage"]
        print(f"\n🧪 Live Usage Test:")
        print(f"   Total estimated cost from tests: ${test_usage['total_estimated_cost_usd']}")
        
        for result in test_usage["test_results"]:
            model = result["model"]
            if result["success"]:
                usage = result["usage"]
                cost = result["cost_estimate"]
                print(f"   ✅ {model}:")
                print(f"     Tokens: {usage['total_tokens']} ({usage['prompt_tokens']} + {usage['completion_tokens']})")
                print(f"     Cost: ${cost['total_cost_usd']:.6f}")
                print(f"     Response: {result['response_preview']}...")
            else:
                print(f"   ❌ {model}: {result['error']}")
        
        # Pricing Reference
        print(f"\n💰 Current Pricing Reference (per 1M tokens):")
        popular_models = ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-4-turbo"]
        for model in popular_models:
            if model in OPENAI_PRICING:
                pricing = OPENAI_PRICING[model]
                print(f"   {model}: ${pricing['input']:.2f} input, ${pricing['output']:.2f} output")
        
        print(f"\n🌐 For complete billing details, visit:")
        print(f"   https://platform.openai.com/usage")
        print(f"   https://platform.openai.com/account/billing")
        
        print("\n" + "="*80)


def main():
    """Main function"""
    # Get API key
    api_key = None
    export_flag = False
    
    if len(sys.argv) >= 2:
        if sys.argv[1].startswith('sk-'):
            api_key = sys.argv[1]
            export_flag = '--export' in sys.argv[2:]
        elif sys.argv[1] == '--export':
            api_key = os.getenv('OPENAI_API_KEY')
            export_flag = True
    elif os.getenv('OPENAI_API_KEY'):
        api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("Usage: python check_openai_billing.py <API_KEY> [--export]")
        print("Example: python check_openai_billing.py sk-1234567890abcdef")
        print("\nOr set OPENAI_API_KEY environment variable:")
        print("         export OPENAI_API_KEY='sk-1234567890abcdef'")
        print("         python check_openai_billing.py")
        sys.exit(1)
    
    if not api_key.startswith('sk-'):
        print("Error: Invalid API key format")
        sys.exit(1)
    
    try:
        checker = OpenAIBillingChecker(api_key)
        report = checker.get_comprehensive_billing_report()
        checker.display_billing_report(report)
        
        if export_flag:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"openai_billing_report_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nReport exported to: {filename}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()