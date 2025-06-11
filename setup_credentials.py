#!/usr/bin/env python3
"""
Octopus Energy API Credentials Setup
Simple script to help set up API credentials for data refresh functionality.
"""

import os
import sys
from pathlib import Path

def main():
    print("🐙 Octopus Energy API Credentials Setup")
    print("=" * 50)
    print()
    print("This script will help you set up your API credentials for automatic")
    print("data refresh functionality in the dashboard.")
    print()
    
    # Get API Key
    print("📝 Step 1: API Key")
    print("You can find your API key at: https://octopus.energy/dashboard/developer/")
    print()
    
    api_key = input("Enter your Octopus Energy API Key: ").strip()
    if not api_key:
        print("❌ API key is required. Exiting.")
        sys.exit(1)
    
    # Get Account Number
    print()
    print("📝 Step 2: Account Number")
    print("Your account number is shown on your Octopus Energy account (format: A-AAAA1111)")
    print()
    
    account_number = input("Enter your Account Number: ").strip()
    if not account_number:
        print("❌ Account number is required. Exiting.")
        sys.exit(1)
    
    # Validate account number format
    if not account_number.startswith('A-') or len(account_number) != 9:
        print("⚠️  Warning: Account number should be in format A-AAAA1111")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Setup cancelled.")
            sys.exit(1)
    
    print()
    print("💾 Saving credentials...")
    
    try:
        # Save to files
        with open('oct_api.txt', 'w') as f:
            f.write(api_key)
        
        with open('account_info.txt', 'w') as f:
            f.write(account_number)
        
        # Also set environment variables for current session
        os.environ['OCTOPUS_API_KEY'] = api_key
        os.environ['OCTOPUS_ACCOUNT_NUMBER'] = account_number
        
        print("✅ Credentials saved successfully!")
        print()
        print("📁 Files created:")
        print(f"  - oct_api.txt")
        print(f"  - account_info.txt")
        print()
        print("🔒 Security Note:")
        print("  - These files contain sensitive information")
        print("  - Make sure they're not committed to version control")
        print("  - The .gitignore file should exclude them")
        print()
        print("🚀 You can now use the data refresh functionality in the dashboard!")
        print("   Navigate to the main dashboard and use the 'Data Refresh Center'")
        
    except Exception as e:
        print(f"❌ Error saving credentials: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 