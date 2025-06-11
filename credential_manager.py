#!/usr/bin/env python3
"""
Secure Credential Management for OctopusTracker
Supports multiple credential storage methods with security best practices.
"""

import os
import json
import getpass
import base64
from pathlib import Path
from typing import Optional, Dict, Tuple

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

class CredentialManager:
    """Secure credential management with multiple storage options."""
    
    SERVICE_NAME = "OctopusTracker"
    
    def __init__(self):
        self.credentials_file = Path('data/credentials.enc')
        self.config_file = Path('data/credential_config.json')
        self._cached_credentials = None  # Cache decrypted credentials in memory
        self._cached_password = None     # Cache password for session
        
    def derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2."""
        if not ENCRYPTION_AVAILABLE:
            raise ImportError("cryptography package required for encryption")
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def encrypt_credentials(self, credentials: Dict[str, str], password: str) -> bytes:
        """Encrypt credentials using password-derived key."""
        salt = os.urandom(16)
        key = self.derive_key_from_password(password, salt)
        fernet = Fernet(key)
        
        credential_json = json.dumps(credentials).encode()
        encrypted_data = fernet.encrypt(credential_json)
        
        # Prepend salt to encrypted data
        return salt + encrypted_data
    
    def decrypt_credentials(self, encrypted_data: bytes, password: str) -> Dict[str, str]:
        """Decrypt credentials using password."""
        salt = encrypted_data[:16]
        encrypted_content = encrypted_data[16:]
        
        key = self.derive_key_from_password(password, salt)
        fernet = Fernet(key)
        
        decrypted_data = fernet.decrypt(encrypted_content)
        return json.loads(decrypted_data.decode())
    
    def save_config(self, method: str, additional_info: dict = None):
        """Save credential storage method configuration."""
        config = {
            'method': method,
            'info': additional_info or {}
        }
        
        os.makedirs('data', exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def load_config(self) -> Dict:
        """Load credential storage configuration."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {'method': 'none'}
    
    def store_credentials_environment(self, api_key: str, account_number: str) -> bool:
        """Store credentials as environment variables (session only)."""
        try:
            os.environ['OCTOPUS_API_KEY'] = api_key
            os.environ['OCTOPUS_ACCOUNT_NUMBER'] = account_number
            
            self.save_config('environment', {
                'note': 'Credentials stored in environment variables for current session only'
            })
            
            print("✅ Credentials stored in environment variables")
            print("⚠️  Note: These will only persist for the current session")
            return True
            
        except Exception as e:
            print(f"❌ Error storing environment credentials: {e}")
            return False
    
    def store_credentials_encrypted(self, api_key: str, account_number: str, password: str = None) -> bool:
        """Store credentials in encrypted file."""
        if not ENCRYPTION_AVAILABLE:
            print("❌ Encryption not available. Install cryptography: pip install cryptography")
            return False
            
        try:
            if not password:
                password = getpass.getpass("Enter encryption password: ")
                confirm_password = getpass.getpass("Confirm encryption password: ")
                
                if password != confirm_password:
                    print("❌ Passwords don't match")
                    return False
            
            credentials = {
                'api_key': api_key,
                'account_number': account_number
            }
            
            encrypted_data = self.encrypt_credentials(credentials, password)
            
            os.makedirs('data', exist_ok=True)
            with open(self.credentials_file, 'wb') as f:
                f.write(encrypted_data)
            
            self.save_config('encrypted_file', {
                'file': str(self.credentials_file),
                'note': 'Credentials encrypted with password'
            })
            
            print(f"✅ Credentials encrypted and saved to {self.credentials_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error storing encrypted credentials: {e}")
            return False
    
    def store_credentials_keyring(self, api_key: str, account_number: str) -> bool:
        """Store credentials in system keyring."""
        if not KEYRING_AVAILABLE:
            print("❌ Keyring not available. Install keyring: pip install keyring")
            return False
            
        try:
            keyring.set_password(self.SERVICE_NAME, "api_key", api_key)
            keyring.set_password(self.SERVICE_NAME, "account_number", account_number)
            
            self.save_config('keyring', {
                'service': self.SERVICE_NAME,
                'note': 'Credentials stored in system keyring'
            })
            
            print("✅ Credentials stored in system keyring")
            return True
            
        except Exception as e:
            print(f"❌ Error storing keyring credentials: {e}")
            return False
    
    def load_credentials_environment(self) -> Tuple[Optional[str], Optional[str]]:
        """Load credentials from environment variables."""
        api_key = os.getenv('OCTOPUS_API_KEY')
        account_number = os.getenv('OCTOPUS_ACCOUNT_NUMBER')
        return api_key, account_number
    
    def load_credentials_encrypted(self, password: str = None, silent: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """Load credentials from encrypted file with optional caching."""
        if not ENCRYPTION_AVAILABLE:
            return None, None
            
        try:
            if not self.credentials_file.exists():
                return None, None
            
            # Return cached credentials if available
            if self._cached_credentials is not None:
                return self._cached_credentials.get('api_key'), self._cached_credentials.get('account_number')
            
            # Use cached password if available
            if not password and self._cached_password:
                password = self._cached_password
            
            # If still no password and not silent, prompt for it
            if not password and not silent:
                password = getpass.getpass("Enter encryption password: ")
            
            # If still no password and silent mode, return None
            if not password:
                return None, None
            
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
            
            credentials = self.decrypt_credentials(encrypted_data, password)
            
            # Cache the credentials and password for this session
            self._cached_credentials = credentials
            self._cached_password = password
            
            return credentials.get('api_key'), credentials.get('account_number')
            
        except Exception as e:
            if not silent:
                print(f"❌ Error loading encrypted credentials: {e}")
            return None, None
    
    def load_credentials_keyring(self) -> Tuple[Optional[str], Optional[str]]:
        """Load credentials from system keyring."""
        if not KEYRING_AVAILABLE:
            return None, None
            
        try:
            api_key = keyring.get_password(self.SERVICE_NAME, "api_key")
            account_number = keyring.get_password(self.SERVICE_NAME, "account_number")
            return api_key, account_number
            
        except Exception as e:
            print(f"❌ Error loading keyring credentials: {e}")
            return None, None
    
    def load_credentials_legacy(self) -> Tuple[Optional[str], Optional[str]]:
        """Load credentials from legacy plaintext files (for migration)."""
        api_key = None
        account_number = None
        
        try:
            if Path('oct_api.txt').exists():
                with open('oct_api.txt', 'r') as f:
                    api_key = f.read().strip()
            
            if Path('account_info.txt').exists():
                with open('account_info.txt', 'r') as f:
                    account_number = f.read().strip()
                    
        except Exception as e:
            print(f"Warning: Error loading legacy credentials: {e}")
        
        return api_key, account_number
    
    def get_credentials(self, password: str = None, silent: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """Get credentials using the configured method."""
        config = self.load_config()
        method = config.get('method', 'none')
        
        if method == 'environment':
            return self.load_credentials_environment()
        elif method == 'encrypted_file':
            return self.load_credentials_encrypted(password, silent)
        elif method == 'keyring':
            return self.load_credentials_keyring()
        else:
            # Try all methods in order of preference
            api_key, account_number = self.load_credentials_environment()
            if api_key and account_number:
                return api_key, account_number
            
            api_key, account_number = self.load_credentials_keyring()
            if api_key and account_number:
                return api_key, account_number
            
            api_key, account_number = self.load_credentials_encrypted(password, silent)
            if api_key and account_number:
                return api_key, account_number
            
            # Fallback to legacy files for migration
            return self.load_credentials_legacy()
    
    def cache_password(self, password: str) -> bool:
        """Cache password for the session (for web dashboard use)."""
        try:
            # Test if the password works by trying to decrypt
            if self.credentials_file.exists():
                with open(self.credentials_file, 'rb') as f:
                    encrypted_data = f.read()
                credentials = self.decrypt_credentials(encrypted_data, password)
                
                # If successful, cache both password and credentials
                self._cached_password = password
                self._cached_credentials = credentials
                return True
            return False
        except Exception:
            return False
    
    def clear_cache(self):
        """Clear cached credentials and password."""
        self._cached_credentials = None
        self._cached_password = None
    
    def migrate_legacy_credentials(self, storage_method: str = 'environment') -> bool:
        """Migrate credentials from legacy plaintext files to secure storage."""
        print("🔄 Migrating legacy plaintext credentials to secure storage...")
        
        api_key, account_number = self.load_credentials_legacy()
        
        if not api_key or not account_number:
            print("❌ No legacy credentials found to migrate")
            return False
        
        print(f"✅ Found legacy credentials")
        print(f"   API Key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '***'}")
        print(f"   Account: {account_number}")
        
        success = False
        if storage_method == 'encrypted_file':
            success = self.store_credentials_encrypted(api_key, account_number)
        elif storage_method == 'keyring':
            success = self.store_credentials_keyring(api_key, account_number)
        elif storage_method == 'environment':
            success = self.store_credentials_environment(api_key, account_number)
        
        if success:
            # Securely delete legacy files
            try:
                if Path('oct_api.txt').exists():
                    Path('oct_api.txt').unlink()
                    print("🗑️  Deleted oct_api.txt")
                
                if Path('account_info.txt').exists():
                    Path('account_info.txt').unlink()
                    print("🗑️  Deleted account_info.txt")
                
                print("✅ Legacy credential migration completed")
                return True
                
            except Exception as e:
                print(f"⚠️  Could not delete legacy files: {e}")
                return True
        else:
            print("❌ Migration failed")
            return False


if __name__ == "__main__":
    manager = CredentialManager()
    
    print("🔐 OctopusTracker Credential Manager")
    print("=" * 40)
    print("1. Migrate legacy credentials")
    print("2. Store new credentials (environment)")
    print("3. Store new credentials (encrypted)")
    print("4. Store new credentials (keyring)")
    print("5. Test credentials")
    
    choice = input("Select option (1-5): ").strip()
    
    if choice == '1':
        method = input("Storage method (environment/encrypted_file/keyring) [environment]: ").strip()
        if not method:
            method = 'environment'
        manager.migrate_legacy_credentials(method)
    
    elif choice in ['2', '3', '4']:
        api_key = getpass.getpass("Enter Octopus API Key: ")
        account_number = input("Enter Account Number: ")
        
        if choice == '2':
            manager.store_credentials_environment(api_key, account_number)
        elif choice == '3':
            manager.store_credentials_encrypted(api_key, account_number)
        elif choice == '4':
            manager.store_credentials_keyring(api_key, account_number)
    
    elif choice == '5':
        api_key, account_number = manager.get_credentials()
        if api_key and account_number:
            print(f"✅ Credentials found:")
            print(f"   API Key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '***'}")
            print(f"   Account: {account_number}")
        else:
            print("❌ No credentials found") 