#!/usr/bin/env python3
"""
OpenAI Usage Tracker

Creates a local log to track API usage and costs over time.
Useful when dashboard access is not available.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, Any
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

USAGE_LOG_FILE = "openai_usage_log.json"


def load_usage_log() -> Dict[str, Any]:
    """Load existing usage log or create new one"""
    if os.path.exists(USAGE_LOG_FILE):
        with open(USAGE_LOG_FILE, 'r') as f:
            return json.load(f)
    return {
        "created_at": datetime.now().isoformat(),
        "total_cost": 0.0,
        "total_tokens": 0,
        "calls": [],
        "daily_summary": {}
    }


def save_usage_log(log_data: Dict[str, Any]):
    """Save usage log to file"""
    with open(USAGE_LOG_FILE, 'w') as f:
        json.dump(log_data, f, indent=2)


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for given usage"""
    if model not in OPENAI_PRICING:
        return 0.0
    
    pricing = OPENAI_PRICING[model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


def log_usage(model: str, input_tokens: int, output_tokens: int, purpose: str = ""):
    """Log a usage entry"""
    log_data = load_usage_log()
    
    cost = calculate_cost(model, input_tokens, output_tokens)
    total_tokens = input_tokens + output_tokens
    
    # Add new call entry
    call_entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost": cost,
        "purpose": purpose
    }
    
    log_data["calls"].append(call_entry)
    log_data["total_cost"] += cost
    log_data["total_tokens"] += total_tokens
    
    # Update daily summary
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in log_data["daily_summary"]:
        log_data["daily_summary"][today] = {
            "calls": 0,
            "tokens": 0,
            "cost": 0.0,
            "models": {}
        }
    
    daily = log_data["daily_summary"][today]
    daily["calls"] += 1
    daily["tokens"] += total_tokens
    daily["cost"] += cost
    
    if model not in daily["models"]:
        daily["models"][model] = {"calls": 0, "tokens": 0, "cost": 0.0}
    
    daily["models"][model]["calls"] += 1
    daily["models"][model]["tokens"] += total_tokens
    daily["models"][model]["cost"] += cost
    
    save_usage_log(log_data)
    
    print(f"✅ Logged usage: {model} - {total_tokens} tokens - ${cost:.6f}")


def show_usage_summary():
    """Display usage summary"""
    if not os.path.exists(USAGE_LOG_FILE):
        print("No usage log found. Start tracking by using log_usage().")
        return
    
    log_data = load_usage_log()
    
    print("="*60)
    print("OpenAI Usage Summary")
    print("="*60)
    print(f"Log created: {log_data['created_at']}")
    print(f"Total API calls: {len(log_data['calls'])}")
    print(f"Total tokens used: {log_data['total_tokens']:,}")
    print(f"Total estimated cost: ${log_data['total_cost']:.6f}")
    
    if log_data['calls']:
        print(f"\n📊 Recent calls (last 5):")
        for call in log_data['calls'][-5:]:
            timestamp = call['timestamp'][:19].replace('T', ' ')
            print(f"   {timestamp} | {call['model']} | {call['total_tokens']} tokens | ${call['cost']:.6f}")
            if call['purpose']:
                print(f"      Purpose: {call['purpose']}")
    
    if log_data['daily_summary']:
        print(f"\n📅 Daily summary (last 7 days):")
        recent_days = sorted(log_data['daily_summary'].keys())[-7:]
        for day in recent_days:
            daily = log_data['daily_summary'][day]
            print(f"   {day}: {daily['calls']} calls, {daily['tokens']:,} tokens, ${daily['cost']:.6f}")
            
            # Show model breakdown for the day
            for model, stats in daily['models'].items():
                print(f"     - {model}: {stats['calls']} calls, ${stats['cost']:.6f}")


def test_and_log():
    """Make a test API call and log it"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return
    
    client = OpenAI(api_key=api_key)
    
    try:
        print("Making test API call...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'Hello from usage tracker!'"}],
            max_tokens=20
        )
        
        if response.usage:
            log_usage(
                model="gpt-4o-mini",
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                purpose="Usage tracker test"
            )
            
            print(f"Response: {response.choices[0].message.content}")
        else:
            print("No usage data returned from API")
            
    except Exception as e:
        print(f"Error making API call: {e}")


def export_usage_csv():
    """Export usage log to CSV format"""
    if not os.path.exists(USAGE_LOG_FILE):
        print("No usage log found.")
        return
    
    log_data = load_usage_log()
    
    csv_filename = f"openai_usage_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(csv_filename, 'w') as f:
        # Write header
        f.write("Timestamp,Model,Input_Tokens,Output_Tokens,Total_Tokens,Cost_USD,Purpose\n")
        
        # Write data
        for call in log_data['calls']:
            f.write(f"{call['timestamp']},{call['model']},{call['input_tokens']},{call['output_tokens']},{call['total_tokens']},{call['cost']:.6f},{call.get('purpose', '')}\n")
    
    print(f"Usage data exported to: {csv_filename}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("OpenAI Usage Tracker")
        print("Usage:")
        print("  python usage_tracker.py summary          - Show usage summary")
        print("  python usage_tracker.py test             - Make test call and log")
        print("  python usage_tracker.py log <model> <input_tokens> <output_tokens> [purpose]")
        print("  python usage_tracker.py export           - Export to CSV")
        print("\nExamples:")
        print("  python usage_tracker.py summary")
        print("  python usage_tracker.py test")
        print("  python usage_tracker.py log gpt-4o-mini 100 50 'Testing API'")
        print("  python usage_tracker.py export")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "summary":
        show_usage_summary()
    
    elif command == "test":
        test_and_log()
        show_usage_summary()
    
    elif command == "log":
        if len(sys.argv) < 5:
            print("Usage: python usage_tracker.py log <model> <input_tokens> <output_tokens> [purpose]")
            sys.exit(1)
        
        model = sys.argv[2]
        try:
            input_tokens = int(sys.argv[3])
            output_tokens = int(sys.argv[4])
            purpose = sys.argv[5] if len(sys.argv) > 5 else ""
            
            log_usage(model, input_tokens, output_tokens, purpose)
            show_usage_summary()
            
        except ValueError:
            print("Error: Token counts must be integers")
            sys.exit(1)
    
    elif command == "export":
        export_usage_csv()
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()