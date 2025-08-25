#!/usr/bin/env python3
"""
OpenAI Total Usage Estimator

Estimates total usage and costs when dashboard access is not available.
Uses various methods to gather usage information and provide estimates.
"""

import sys
import os
import json
from datetime import datetime, timedelta, date
from typing import Dict, Any, List
import requests
from openai import OpenAI


OPENAI_PRICING = {
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "gpt-3.5-turbo-0125": {"input": 0.50, "output": 1.50},
    "o1-mini": {"input": 3.00, "output": 12.00},
    "o1-preview": {"input": 15.00, "output": 60.00},
}


class OpenAIUsageEstimator:
    """Estimates OpenAI usage and costs without dashboard access"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def try_usage_endpoints(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Try various usage endpoints with different date ranges"""
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            # Try from 90 days ago
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        
        # List of endpoints and parameter combinations to try
        endpoints_to_try = [
            # Dashboard billing endpoints
            f"https://api.openai.com/dashboard/billing/usage?start_date={start_date}&end_date={end_date}",
            f"https://api.openai.com/v1/dashboard/billing/usage?start_date={start_date}&end_date={end_date}",
            
            # Usage endpoints
            f"https://api.openai.com/v1/usage?start_date={start_date}&end_date={end_date}",
            f"https://api.openai.com/usage?start_date={start_date}&end_date={end_date}",
            
            # Daily usage endpoints
            f"https://api.openai.com/v1/dashboard/billing/usage?date={end_date}",
            f"https://api.openai.com/v1/usage?date={end_date}",
            
            # Alternative formats
            f"https://api.openai.com/v1/dashboard/billing/usage?from={start_date}&to={end_date}",
            f"https://api.openai.com/v1/usage?from={start_date}&to={end_date}",
        ]
        
        results = {}
        
        for endpoint in endpoints_to_try:
            try:
                print(f"Trying: {endpoint}")
                response = requests.get(endpoint, headers=self.headers)
                
                result_data = {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "success": response.status_code == 200
                }
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        result_data["data"] = data
                        result_data["estimated_cost"] = self.estimate_cost_from_response(data)
                    except json.JSONDecodeError:
                        result_data["raw_response"] = response.text[:500]
                else:
                    result_data["error"] = response.text[:200]
                
                results[endpoint] = result_data
                
                # If we get success, also store the successful data
                if response.status_code == 200:
                    print(f"✅ Success! Found data at {endpoint}")
                    break
                    
            except Exception as e:
                results[endpoint] = {
                    "endpoint": endpoint,
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    def estimate_cost_from_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate costs from API response data"""
        if not data:
            return {"error": "No data provided"}
        
        total_cost = 0.0
        breakdown = {}
        
        # Handle different response formats
        if "data" in data and isinstance(data["data"], list):
            for entry in data["data"]:
                if "line_items" in entry:
                    for item in entry["line_items"]:
                        model = item.get("name", "unknown")
                        cost = item.get("cost", 0)
                        if isinstance(cost, (int, float)):
                            cost = cost / 100 if cost > 1 else cost  # Convert cents to dollars if needed
                            total_cost += cost
                            breakdown[model] = breakdown.get(model, 0) + cost
                
                elif "cost" in entry:
                    cost = entry["cost"]
                    if isinstance(cost, (int, float)):
                        cost = cost / 100 if cost > 1 else cost
                        total_cost += cost
                        model = entry.get("model", entry.get("name", "unknown"))
                        breakdown[model] = breakdown.get(model, 0) + cost
        
        elif "total_cost" in data:
            total_cost = data["total_cost"]
            if isinstance(total_cost, (int, float)) and total_cost > 1:
                total_cost = total_cost / 100  # Convert cents to dollars
        
        elif "usage" in data:
            # Handle usage data format
            usage_data = data["usage"]
            for model, usage in usage_data.items():
                if model in OPENAI_PRICING and isinstance(usage, dict):
                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)
                    model_cost = self.calculate_model_cost(model, input_tokens, output_tokens)
                    total_cost += model_cost["total_cost"]
                    breakdown[model] = model_cost["total_cost"]
        
        return {
            "total_cost_usd": round(total_cost, 6),
            "breakdown": breakdown,
            "raw_data": data
        }
    
    def calculate_model_cost(self, model: str, input_tokens: int, output_tokens: int) -> Dict[str, Any]:
        """Calculate cost for specific model and tokens"""
        if model not in OPENAI_PRICING:
            return {"total_cost": 0, "error": f"Unknown model: {model}"}
        
        pricing = OPENAI_PRICING[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        }
    
    def estimate_usage_from_api_calls(self) -> Dict[str, Any]:
        """Estimate usage by making test calls and extrapolating"""
        print("Making test API calls to estimate usage patterns...")
        
        test_models = ["gpt-3.5-turbo", "gpt-4o-mini"]
        results = []
        
        for model in test_models:
            try:
                # Make a small test call
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Count from 1 to 5"}],
                    max_tokens=20
                )
                
                if response.usage:
                    cost = self.calculate_model_cost(
                        model, 
                        response.usage.prompt_tokens, 
                        response.usage.completion_tokens
                    )
                    
                    results.append({
                        "model": model,
                        "test_usage": response.usage.total_tokens,
                        "test_cost": cost["total_cost"],
                        "success": True
                    })
                    
            except Exception as e:
                results.append({
                    "model": model,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "test_results": results,
            "note": "These are small test calls to verify model access and pricing"
        }
    
    def try_historical_usage(self) -> Dict[str, Any]:
        """Try to get historical usage data using different time periods"""
        print("Attempting to retrieve historical usage data...")
        
        # Try different date ranges
        date_ranges = [
            # Last 7 days
            {
                "start": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d"),
                "label": "Last 7 days"
            },
            # Last 30 days
            {
                "start": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d"),
                "label": "Last 30 days"
            },
            # Last 90 days
            {
                "start": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d"),
                "label": "Last 90 days"
            },
            # Current month
            {
                "start": datetime.now().replace(day=1).strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d"),
                "label": "Current month"
            }
        ]
        
        all_results = {}
        
        for period in date_ranges:
            print(f"Checking {period['label']}...")
            results = self.try_usage_endpoints(period["start"], period["end"])
            
            # Find successful results
            successful_results = {k: v for k, v in results.items() if v.get("success")}
            
            if successful_results:
                all_results[period["label"]] = {
                    "period": period,
                    "results": successful_results,
                    "status": "success"
                }
                print(f"✅ Found data for {period['label']}")
            else:
                all_results[period["label"]] = {
                    "period": period,
                    "results": results,
                    "status": "failed"
                }
                print(f"❌ No data found for {period['label']}")
        
        return all_results
    
    def generate_usage_estimate(self) -> Dict[str, Any]:
        """Generate comprehensive usage estimate"""
        print("="*60)
        print("OpenAI Total Usage Estimator")
        print("="*60)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "api_key": f"{self.api_key[:8]}...{self.api_key[-4:]}",
            "estimation_methods": {}
        }
        
        # Method 1: Try historical usage endpoints
        print("\n1. Attempting to retrieve historical usage data...")
        historical_data = self.try_historical_usage()
        report["estimation_methods"]["historical_usage"] = historical_data
        
        # Method 2: Test API calls for current pricing verification
        print("\n2. Testing current API access and pricing...")
        test_calls = self.estimate_usage_from_api_calls()
        report["estimation_methods"]["test_calls"] = test_calls
        
        # Summarize findings
        summary = self.summarize_findings(report)
        report["summary"] = summary
        
        return report
    
    def summarize_findings(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize the findings from all estimation methods"""
        summary = {
            "total_estimated_cost": 0.0,
            "successful_data_sources": [],
            "failed_attempts": 0,
            "recommendations": []
        }
        
        # Check historical usage results
        historical = report["estimation_methods"]["historical_usage"]
        for period, data in historical.items():
            if data["status"] == "success":
                summary["successful_data_sources"].append(period)
                
                # Extract cost data if available
                for endpoint, result in data["results"].items():
                    if "estimated_cost" in result and "total_cost_usd" in result["estimated_cost"]:
                        cost = result["estimated_cost"]["total_cost_usd"]
                        summary["total_estimated_cost"] += cost
                        print(f"Found cost data: ${cost} for {period}")
            else:
                summary["failed_attempts"] += 1
        
        # Add recommendations based on findings
        if summary["successful_data_sources"]:
            summary["recommendations"].append("✅ Successfully retrieved some usage data")
            if summary["total_estimated_cost"] > 0:
                summary["recommendations"].append(f"💰 Estimated total cost: ${summary['total_estimated_cost']:.6f}")
            else:
                summary["recommendations"].append("💰 Usage appears to be very minimal (under $0.01)")
        else:
            summary["recommendations"].extend([
                "❌ Unable to access usage data through API",
                "🔑 This API key may have restricted permissions",
                "📧 Contact the organization admin for billing access",
                "🌐 Request dashboard access at https://platform.openai.com/",
                "📊 Consider using organization-level API keys for usage tracking"
            ])
        
        return summary
    
    def display_report(self, report: Dict[str, Any]):
        """Display the usage estimation report"""
        print("\n" + "="*60)
        print("USAGE ESTIMATION REPORT")
        print("="*60)
        
        summary = report["summary"]
        
        print(f"\n📊 Data Sources Checked:")
        historical = report["estimation_methods"]["historical_usage"]
        for period, data in historical.items():
            status = "✅" if data["status"] == "success" else "❌"
            print(f"   {status} {period}: {data['status']}")
        
        print(f"\n💰 Cost Estimation:")
        if summary["total_estimated_cost"] > 0:
            print(f"   Total estimated cost: ${summary['total_estimated_cost']:.6f}")
            print("   Note: This may not include all historical usage")
        else:
            print("   No usage costs detected in accessible periods")
            print("   This could mean:")
            print("     - Very minimal usage (under detection threshold)")
            print("     - API key has restricted access to billing data")
            print("     - Usage data is outside the checked time periods")
        
        print(f"\n📋 Summary:")
        for recommendation in summary["recommendations"]:
            print(f"   {recommendation}")
        
        print(f"\n🔗 Alternative Methods:")
        print("   1. Request organization admin to share billing info")
        print("   2. Ask for dashboard access upgrade")
        print("   3. Use organization-level API key")
        print("   4. Contact OpenAI support for usage history")
        
        print("\n" + "="*60)


def main():
    """Main function"""
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
        print("Usage: python estimate_total_usage.py <API_KEY> [--export]")
        print("Or set OPENAI_API_KEY environment variable")
        sys.exit(1)
    
    try:
        estimator = OpenAIUsageEstimator(api_key)
        report = estimator.generate_usage_estimate()
        estimator.display_report(report)
        
        if export_flag:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"openai_usage_estimate_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nReport exported to: {filename}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()