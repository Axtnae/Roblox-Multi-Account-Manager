import base64
import hashlib
import json
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
class SecurityManager:
    """Handles encryption/decryption of account data using PBKDF2 and Fernet."""
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.salt_file = os.path.join(self.data_dir, "security.salt")
        self.data_file = os.path.join(self.data_dir, "accounts.json")
    def _get_or_create_salt(self):
        """Get existing salt or create a new one."""
        if os.path.exists(self.salt_file):
            with open(self.salt_file, 'rb') as f:
                return f.read()
        else:
            salt = os.urandom(16)
            with open(self.salt_file, 'wb') as f:
                f.write(salt)
            return salt
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password using PBKDF2."""
        salt = self._get_or_create_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    def encrypt_data(self, data: dict, password: str) -> bool:
        """Encrypt and save account data."""
        try:
            key = self._derive_key(password)
            fernet = Fernet(key)
            json_data = json.dumps(data, indent=2)
            encrypted_data = fernet.encrypt(json_data.encode())
            with open(self.data_file, 'wb') as f:
                f.write(encrypted_data)
            return True
        except Exception as e:
            print(f"Encryption error: {e}")
            return False
    def decrypt_data(self, password: str) -> dict:
        """Decrypt and load account data."""
        try:
            if not os.path.exists(self.data_file):
                return {}
            key = self._derive_key(password)
            fernet = Fernet(key)
            with open(self.data_file, 'rb') as f:
                encrypted_data = f.read()
            decrypted_data = fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            print(f"Decryption error: {e}")
            return None
    def data_exists(self) -> bool:
        """Check if encrypted data file exists."""
        return os.path.exists(self.data_file)
