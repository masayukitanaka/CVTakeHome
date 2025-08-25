#!/usr/bin/env python3
"""
OpenAI token usage checker

This program checks the usage status of a specified OpenAI API token including:
- Account information
- Usage statistics
- Billing information
- Rate limits
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import requests
from openai import OpenAI


class OpenAIUsageChecker:
    """OpenAI API usage status checker"""
    
    def __init__(self, api_key: str):
        """
        Initialize the usage checker
        
        Args:
            api_key: OpenAI API key to check
        """
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def check_models(self) -> Dict[str, Any]:
        """Check available models"""
        try:
            models = self.client.models.list()
            return {
                "success": True,
                "models": [model.id for model in models.data],
                "count": len(models.data)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_account_info(self) -> Dict[str, Any]:
        """Check account information"""
        try:
            # Try to get organization info (if available)
            response = requests.get(
                f"{self.base_url}/organizations",
                headers=self.headers
            )
            
            if response.status_code == 200:
                org_data = response.json()
                return {
                    "success": True,
                    "organizations": org_data.get("data", [])
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_usage_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Check usage statistics
        
        Args:
            start_date: Start date in YYYY-MM-DD format (default: 30 days ago)
            end_date: End date in YYYY-MM-DD format (default: today)
        """
        try:
            # Set default dates if not provided
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            # Try to get usage data (Note: This endpoint may require specific permissions)
            response = requests.get(
                f"{self.base_url}/usage",
                headers=self.headers,
                params={
                    "start_date": start_date,
                    "end_date": end_date
                }
            )
            
            if response.status_code == 200:
                usage_data = response.json()
                return {
                    "success": True,
                    "start_date": start_date,
                    "end_date": end_date,
                    "usage_data": usage_data
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "note": "Usage endpoint may require specific permissions or may not be available for all account types"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def test_api_key(self) -> Dict[str, Any]:
        """Test if the API key is valid by making a simple API call"""
        try:
            # Make a simple API call to test the key
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=1
            )
            
            return {
                "success": True,
                "model_used": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                    "total_tokens": response.usage.total_tokens if response.usage else None
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_billing_info(self) -> Dict[str, Any]:
        """Check billing information (if available)"""
        try:
            # Try to get billing info (may require specific permissions)
            response = requests.get(
                f"{self.base_url}/dashboard/billing/subscription",
                headers=self.headers
            )
            
            if response.status_code == 200:
                billing_data = response.json()
                return {
                    "success": True,
                    "billing_data": billing_data
                }
            else:
                # Try alternative billing endpoint
                response = requests.get(
                    f"{self.base_url}/dashboard/billing/credit_grants",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    credit_data = response.json()
                    return {
                        "success": True,
                        "credit_data": credit_data
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: Billing information not accessible",
                        "note": "Billing endpoints may require admin permissions or may not be available for all account types"
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the OpenAI API key"""
        print("Checking OpenAI API key status...")
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "api_key": f"{self.api_key[:8]}...{self.api_key[-4:]}",  # Masked key
            "checks": {}
        }
        
        # Test API key validity
        print("1. Testing API key validity...")
        status["checks"]["api_key_test"] = self.test_api_key()
        
        # Check available models
        print("2. Checking available models...")
        status["checks"]["models"] = self.check_models()
        
        # Check account info
        print("3. Checking account information...")
        status["checks"]["account_info"] = self.check_account_info()
        
        # Check usage stats
        print("4. Checking usage statistics...")
        status["checks"]["usage_stats"] = self.check_usage_stats()
        
        # Check billing info
        print("5. Checking billing information...")
        status["checks"]["billing_info"] = self.check_billing_info()
        
        return status
    
    def display_status(self, status: Dict[str, Any]):
        """Display the status in a formatted way"""
        print("\n" + "="*80)
        print(f"OpenAI API Key Status Report")
        print("="*80)
        print(f"Timestamp: {status['timestamp']}")
        print(f"API Key: {status['api_key']}")
        print("="*80)
        
        # API Key Test
        api_test = status["checks"]["api_key_test"]
        print(f"\n🔑 API Key Test: {'✅ VALID' if api_test['success'] else '❌ INVALID'}")
        if api_test["success"]:
            print(f"   Model Used: {api_test['model_used']}")
            if api_test["usage"]:
                usage = api_test["usage"]
                print(f"   Token Usage: {usage['total_tokens']} total ({usage['prompt_tokens']} prompt + {usage['completion_tokens']} completion)")
        else:
            print(f"   Error: {api_test['error']}")
        
        # Models
        models = status["checks"]["models"]
        print(f"\n📋 Available Models: {'✅ SUCCESS' if models['success'] else '❌ FAILED'}")
        if models["success"]:
            print(f"   Total Models: {models['count']}")
            print(f"   Models: {', '.join(models['models'][:10])}{'...' if len(models['models']) > 10 else ''}")
        else:
            print(f"   Error: {models['error']}")
        
        # Account Info
        account = status["checks"]["account_info"]
        print(f"\n🏢 Account Information: {'✅ SUCCESS' if account['success'] else '❌ FAILED'}")
        if account["success"]:
            orgs = account["organizations"]
            if orgs:
                for org in orgs:
                    print(f"   Organization: {org.get('name', 'N/A')} (ID: {org.get('id', 'N/A')})")
            else:
                print("   No organization information available")
        else:
            print(f"   Error: {account['error']}")
        
        # Usage Stats
        usage = status["checks"]["usage_stats"]
        print(f"\n📊 Usage Statistics: {'✅ SUCCESS' if usage['success'] else '❌ FAILED'}")
        if usage["success"]:
            print(f"   Period: {usage['start_date']} to {usage['end_date']}")
            if "usage_data" in usage:
                print(f"   Usage Data: {json.dumps(usage['usage_data'], indent=2)}")
        else:
            print(f"   Error: {usage['error']}")
            if "note" in usage:
                print(f"   Note: {usage['note']}")
        
        # Billing Info
        billing = status["checks"]["billing_info"]
        print(f"\n💳 Billing Information: {'✅ SUCCESS' if billing['success'] else '❌ FAILED'}")
        if billing["success"]:
            if "billing_data" in billing:
                print(f"   Billing Data: {json.dumps(billing['billing_data'], indent=2)}")
            if "credit_data" in billing:
                print(f"   Credit Data: {json.dumps(billing['credit_data'], indent=2)}")
        else:
            print(f"   Error: {billing['error']}")
            if "note" in billing:
                print(f"   Note: {billing['note']}")
        
        print("\n" + "="*80)
    
    def export_status(self, status: Dict[str, Any], output_file: str = None):
        """Export status to JSON file"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"openai_usage_status_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
        
        print(f"\nStatus exported to: {output_file}")
        return output_file


def main():
    """Main function"""
    # First check if we have environment variable
    env_api_key = os.getenv('OPENAI_API_KEY')
    
    # Parse arguments
    api_key = None
    export_flag = False
    
    if len(sys.argv) >= 2:
        # Check if first argument is API key or flag
        if sys.argv[1].startswith('sk-'):
            api_key = sys.argv[1]
            export_flag = '--export' in sys.argv[2:]
        elif sys.argv[1] == '--export':
            api_key = env_api_key
            export_flag = True
        else:
            # Invalid argument format
            api_key = None
    elif env_api_key:
        # No arguments but environment variable exists
        api_key = env_api_key
        export_flag = False
    
    # Show usage if no valid API key found
    if not api_key:
        print("Usage: python check_openai_usage.py <API_KEY> [--export]")
        print("Example: python check_openai_usage.py sk-1234567890abcdef")
        print("         python check_openai_usage.py sk-1234567890abcdef --export")
        print("\nAlternatively, set OPENAI_API_KEY environment variable:")
        print("         export OPENAI_API_KEY='sk-1234567890abcdef'")
        print("         python check_openai_usage.py")
        print("         python check_openai_usage.py --export")
        sys.exit(1)
    
    # Validate API key format
    if not api_key or not api_key.startswith('sk-'):
        print("Error: Invalid API key format. OpenAI API keys should start with 'sk-'")
        sys.exit(1)
    
    try:
        # Create checker and get status
        checker = OpenAIUsageChecker(api_key)
        status = checker.get_comprehensive_status()
        
        # Display results
        checker.display_status(status)
        
        # Export if requested
        if export_flag:
            checker.export_status(status)
        
        return status
        
    except Exception as e:
        print(f"Error: Failed to check OpenAI usage: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()