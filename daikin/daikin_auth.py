#!/usr/bin/env python3
"""
Daikin OAuth Authentication
Single script to handle Daikin heat pump authentication via OAuth2/PKCE
"""

import requests
import json
import base64
import urllib.parse
import secrets
import hashlib
import webbrowser
from datetime import datetime, timedelta

# Set up logging - integrate with main dashboard logging system
import sys
sys.path.append('../tariff_tracker')

try:
    from logging_config import get_logger, get_structured_logger, TimingContext
    logger = get_logger('daikin.auth')
    structured_logger = get_structured_logger('daikin.auth')
except ImportError:
    # Fallback to basic logging if main dashboard logging not available
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    structured_logger = None

class DaikinAuth:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_base = "https://idp.onecta.daikineurope.com/v1/oidc"
        self.tokens_file = "tokens.json"
        
    def get_auth_url(self):
        """Generate OAuth authorization URL (manual flow to avoid localhost issues)."""
        print("🔐 Starting Daikin OAuth authentication...")
        
        # Generate PKCE parameters
        code_verifier = secrets.token_urlsafe(96)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        state = secrets.token_urlsafe(32)
        
        # Save for later use
        auth_state = {
            'code_verifier': code_verifier,
            'state': state,
            'timestamp': datetime.now().isoformat()
        }
        
        with open('auth_state.json', 'w') as f:
            json.dump(auth_state, f, indent=2)
        
        # Build authorization URL with required redirect_uri and deviceId
        auth_params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'scope': 'openid onecta:basic.integration',
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'deviceId': 'daikin-integration-app'
        }
        
        auth_url = f"{self.auth_base}/authorize?" + urllib.parse.urlencode(auth_params)
        
        print("\n" + "="*60)
        print("🌐 STEP 1: Open this URL in your browser:")
        print("="*60)
        print(auth_url)
        print("="*60)
        print("\n📋 STEP 2: After logging in, you'll be redirected to a page showing an authorization code")
        print("💡 STEP 3: Copy that code and run: python daikin_auth.py --code YOUR_CODE_HERE")
        
        return auth_url
    
    def exchange_code_for_tokens(self, authorization_code):
        """Exchange authorization code for access tokens."""
        print(f"🔄 Exchanging authorization code for tokens...")
        
        # Load auth state
        try:
            with open('auth_state.json', 'r') as f:
                auth_state = json.load(f)
        except FileNotFoundError:
            print("❌ No auth state found. Run authentication first.")
            return False
        
        code_verifier = auth_state.get('code_verifier')
        if not code_verifier:
            print("❌ No code verifier found in auth state.")
            return False
        
        # Clean up the authorization code
        if '&' in authorization_code:
            authorization_code = authorization_code.split('&')[0]
        
        # Prepare token request
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': authorization_code,
            'code_verifier': code_verifier,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob'
        }
        
        try:
            response = requests.post(
                f"{self.auth_base}/token",
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            if response.status_code == 200:
                token_response = response.json()
                
                # Save tokens
                token_info = {
                    'access_token': token_response.get('access_token'),
                    'refresh_token': token_response.get('refresh_token'),
                    'expires_at': (datetime.now() + timedelta(seconds=token_response.get('expires_in', 3600))).isoformat(),
                    'saved_at': datetime.now().isoformat(),
                    'client_id': self.client_id
                }
                
                with open(self.tokens_file, 'w') as f:
                    json.dump(token_info, f, indent=2)
                
                print("✅ Authentication successful! Tokens saved.")
                
                # Clean up auth state
                try:
                    import os
                    os.remove('auth_state.json')
                except:
                    pass
                
                return True
            else:
                print(f"❌ Token exchange failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error during token exchange: {e}")
            return False
    
    def refresh_tokens(self):
        """Refresh access tokens using refresh token."""
        try:
            with open(self.tokens_file, 'r') as f:
                token_info = json.load(f)
        except FileNotFoundError:
            print("❌ No tokens found. Authentication required.")
            return False
        
        refresh_token = token_info.get('refresh_token')
        if not refresh_token:
            print("❌ No refresh token available.")
            return False
        
        print("🔄 Refreshing access tokens...")
        
        refresh_data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token
        }
        
        try:
            response = requests.post(
                f"{self.auth_base}/token",
                data=refresh_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            if response.status_code == 200:
                token_response = response.json()
                
                # Update tokens
                token_info.update({
                    'access_token': token_response.get('access_token'),
                    'refresh_token': token_response.get('refresh_token', refresh_token),
                    'expires_at': (datetime.now() + timedelta(seconds=token_response.get('expires_in', 3600))).isoformat(),
                    'saved_at': datetime.now().isoformat()
                })
                
                with open(self.tokens_file, 'w') as f:
                    json.dump(token_info, f, indent=2)
                
                print("✅ Tokens refreshed successfully!")
                return True
            else:
                print(f"❌ Token refresh failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error refreshing tokens: {e}")
            return False
    
    def is_authenticated(self):
        """Check if we have valid tokens."""
        try:
            with open(self.tokens_file, 'r') as f:
                token_info = json.load(f)
            
            # Check if tokens are for the correct client
            if token_info.get('client_id') != self.client_id:
                return False
            
            # Check if tokens are expired
            expires_at_str = token_info.get('expires_at')
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now() > expires_at:
                    print("🔄 Tokens expired, attempting refresh...")
                    return self.refresh_tokens()
            
            return token_info.get('access_token') is not None
            
        except FileNotFoundError:
            return False
        except Exception:
            return False
    
    def get_access_token(self):
        """Get current access token (refreshes if needed)."""
        if not self.is_authenticated():
            return None
        
        try:
            with open(self.tokens_file, 'r') as f:
                token_info = json.load(f)
            return token_info.get('access_token')
        except:
            return None

def main():
    """Command line interface for authentication."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Daikin OAuth Authentication')
    parser.add_argument('--code', help='Authorization code from OAuth callback')
    parser.add_argument('--status', action='store_true', help='Check authentication status')
    parser.add_argument('--refresh', action='store_true', help='Refresh tokens')
    args = parser.parse_args()
    
    # Your Daikin credentials
    client_id = "nEfgPUQTMd_eVEa0ZDYMWOxC"
    client_secret = "6Ne0AWgG9nFwKOTs-TzDNo-gABOtzcdJSHb8yq80UR9TUfHuuX0zYy72yqmua29tHXMQVT4uHRNX8Ts4rrtaZw"
    
    auth = DaikinAuth(client_id, client_secret)
    
    if args.code:
        # Exchange authorization code for tokens
        success = auth.exchange_code_for_tokens(args.code)
        if success:
            print("\n✅ You can now use daikin_api.py to get heat pump data!")
        else:
            print("\n❌ Authentication failed.")
    
    elif args.status:
        # Check authentication status
        if auth.is_authenticated():
            print("✅ Authenticated and ready to use API")
        else:
            print("❌ Not authenticated. Run authentication first.")
    
    elif args.refresh:
        # Refresh tokens
        auth.refresh_tokens()
    
    else:
        # Start authentication flow
        auth_url = auth.get_auth_url()
        
        # Optionally open browser
        try:
            open_browser = input("\n🌐 Open browser automatically? (y/n): ").lower().strip()
            if open_browser in ['y', 'yes']:
                webbrowser.open(auth_url)
        except KeyboardInterrupt:
            print("\n👋 Authentication cancelled.")

if __name__ == "__main__":
    main() 