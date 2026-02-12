"""
AES-256 Encryption System for Sensitive Data
Provides encryption for at-rest data storage and secure file handling

Features:
- AES-256-GCM encryption
- Secure key derivation (PBKDF2)
- Encrypted file storage
- Secure key management
- IV generation and management
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64
import secrets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataEncryptor:
    """
    AES-256-GCM encryption for sensitive forensic data
    Provides secure at-rest encryption with authenticated encryption
    """
    
    def __init__(self, master_key_path: str = "security/keys/master.key"):
        """
        Initialize data encryptor
        
        Args:
            master_key_path: Path to master key file
        """
        self.master_key_path = Path(master_key_path)
        self.master_key_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or generate master key
        if not self.master_key_path.exists():
            self._generate_master_key()
        
        self.master_key = self._load_master_key()
        
        logger.info("Data encryptor initialized with AES-256-GCM")
    
    def _generate_master_key(self):
        """Generate a secure 256-bit master key"""
        logger.info("Generating 256-bit master key...")
        
        # Generate cryptographically secure random key
        master_key = secrets.token_bytes(32)  # 256 bits
        
        # Save with restrictive permissions
        with open(self.master_key_path, 'wb') as f:
            f.write(master_key)
        
        # Set read-only for owner
        os.chmod(self.master_key_path, 0o400)
        
        logger.info(f"Master key generated and saved to {self.master_key_path}")
    
    def _load_master_key(self) -> bytes:
        """Load master key from file"""
        with open(self.master_key_path, 'rb') as f:
            return f.read()
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2
        
        Args:
            password: Password string
            salt: Salt bytes
            
        Returns:
            Derived key (32 bytes)
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(password.encode())
    
    def encrypt_data(self, data: bytes) -> Dict[str, str]:
        """
        Encrypt data using AES-256-GCM
        
        Args:
            data: Raw data bytes to encrypt
            
        Returns:
            Dictionary with ciphertext, iv, and tag (all base64-encoded)
        """
        # Generate random IV (Initialization Vector)
        iv = secrets.token_bytes(12)  # 96 bits for GCM
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.master_key),
            modes.GCM(iv),
            backend=default_backend()
        )
        
        # Encrypt
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Get authentication tag
        tag = encryptor.tag
        
        # Return base64-encoded components
        return {
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
            'iv': base64.b64encode(iv).decode('utf-8'),
            'tag': base64.b64encode(tag).decode('utf-8'),
            'algorithm': 'AES-256-GCM'
        }
    
    def decrypt_data(self, encrypted_data: Dict[str, str]) -> bytes:
        """
        Decrypt data using AES-256-GCM
        
        Args:
            encrypted_data: Dictionary with ciphertext, iv, and tag
            
        Returns:
            Decrypted data bytes
        """
        # Decode base64 components
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        iv = base64.b64decode(encrypted_data['iv'])
        tag = base64.b64decode(encrypted_data['tag'])
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.master_key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        
        # Decrypt
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        return plaintext
    
    def encrypt_file(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        Encrypt a file
        
        Args:
            input_path: Path to file to encrypt
            output_path: Path to save encrypted file (defaults to input_path + .enc)
            
        Returns:
            Path to encrypted file
        """
        if output_path is None:
            output_path = input_path + '.enc'
        
        # Read file
        with open(input_path, 'rb') as f:
            data = f.read()
        
        # Encrypt
        encrypted = self.encrypt_data(data)
        
        # Save encrypted file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(encrypted, f, indent=2)
        
        logger.info(f"File encrypted: {input_path} -> {output_path}")
        
        return output_path
    
    def decrypt_file(self, encrypted_path: str, output_path: Optional[str] = None) -> str:
        """
        Decrypt a file
        
        Args:
            encrypted_path: Path to encrypted file
            output_path: Path to save decrypted file
            
        Returns:
            Path to decrypted file
        """
        if output_path is None:
            output_path = encrypted_path.replace('.enc', '')
        
        # Read encrypted file
        with open(encrypted_path, 'r', encoding='utf-8') as f:
            encrypted = json.load(f)
        
        # Decrypt
        data = self.decrypt_data(encrypted)
        
        # Save decrypted file
        with open(output_path, 'wb') as f:
            f.write(data)
        
        logger.info(f"File decrypted: {encrypted_path} -> {output_path}")
        
        return output_path
    
    def encrypt_string(self, text: str) -> str:
        """
        Encrypt a string
        
        Args:
            text: Plain text string
            
        Returns:
            Base64-encoded encrypted data (JSON string)
        """
        encrypted = self.encrypt_data(text.encode('utf-8'))
        return base64.b64encode(json.dumps(encrypted).encode()).decode('utf-8')
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """
        Decrypt a string
        
        Args:
            encrypted_text: Base64-encoded encrypted data
            
        Returns:
            Decrypted plain text string
        """
        encrypted = json.loads(base64.b64decode(encrypted_text).decode('utf-8'))
        return self.decrypt_data(encrypted).decode('utf-8')


class SecureStorage:
    """
    Secure storage manager for sensitive forensic data
    Combines encryption with integrity checking
    """
    
    def __init__(self, storage_dir: str = "data/secure_storage"):
        """
        Initialize secure storage
        
        Args:
            storage_dir: Directory for secure storage
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.encryptor = DataEncryptor()
        
        logger.info("Secure storage initialized")
    
    def store_secure(self, case_id: str, data_type: str, data: Dict) -> str:
        """
        Store data securely with encryption
        
        Args:
            case_id: Case identifier
            data_type: Type of data (e.g., 'evidence', 'analysis', 'export')
            data: Data dictionary to store
            
        Returns:
            Storage ID
        """
        import uuid
        
        storage_id = str(uuid.uuid4())
        
        # Create storage record
        record = {
            'storage_id': storage_id,
            'case_id': case_id,
            'data_type': data_type,
            'data': data
        }
        
        # Convert to JSON
        json_data = json.dumps(record, ensure_ascii=False)
        
        # Encrypt
        encrypted = self.encryptor.encrypt_data(json_data.encode('utf-8'))
        
        # Add integrity hash
        encrypted['integrity_hash'] = hashlib.sha256(
            json_data.encode('utf-8')
        ).hexdigest()
        
        # Save to file
        case_dir = self.storage_dir / case_id
        case_dir.mkdir(exist_ok=True)
        
        storage_file = case_dir / f"{data_type}_{storage_id}.json"
        with open(storage_file, 'w', encoding='utf-8') as f:
            json.dump(encrypted, f, indent=2)
        
        logger.info(f"Data stored securely: {storage_id}")
        
        return storage_id
    
    def retrieve_secure(self, case_id: str, storage_id: str, data_type: str) -> Dict:
        """
        Retrieve and decrypt stored data
        
        Args:
            case_id: Case identifier
            storage_id: Storage ID
            data_type: Type of data
            
        Returns:
            Decrypted data dictionary
        """
        storage_file = self.storage_dir / case_id / f"{data_type}_{storage_id}.json"
        
        if not storage_file.exists():
            raise FileNotFoundError(f"Storage file not found: {storage_file}")
        
        # Load encrypted data
        with open(storage_file, 'r', encoding='utf-8') as f:
            encrypted = json.load(f)
        
        # Extract integrity hash
        expected_hash = encrypted.pop('integrity_hash', None)
        
        # Decrypt
        decrypted_bytes = self.encryptor.decrypt_data(encrypted)
        decrypted_json = decrypted_bytes.decode('utf-8')
        
        # Verify integrity
        if expected_hash:
            actual_hash = hashlib.sha256(decrypted_json.encode('utf-8')).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError("Integrity check failed - data may be corrupted")
        
        # Parse JSON
        record = json.loads(decrypted_json)
        
        logger.info(f"Data retrieved securely: {storage_id}")
        
        return record['data']
    
    def list_secure_items(self, case_id: str) -> list:
        """
        List all secure storage items for a case
        
        Args:
            case_id: Case identifier
            
        Returns:
            List of storage metadata
        """
        case_dir = self.storage_dir / case_id
        
        if not case_dir.exists():
            return []
        
        items = []
        for file in case_dir.glob('*.json'):
            items.append({
                'filename': file.name,
                'size': file.stat().st_size,
                'modified': file.stat().st_mtime
            })
        
        return items
    
    def delete_secure(self, case_id: str, storage_id: str, data_type: str):
        """
        Securely delete stored data
        
        Args:
            case_id: Case identifier
            storage_id: Storage ID
            data_type: Type of data
        """
        storage_file = self.storage_dir / case_id / f"{data_type}_{storage_id}.json"
        
        if storage_file.exists():
            # Overwrite with random data before deletion (secure wipe)
            file_size = storage_file.stat().st_size
            with open(storage_file, 'wb') as f:
                f.write(secrets.token_bytes(file_size))
            
            # Delete file
            storage_file.unlink()
            
            logger.info(f"Data securely deleted: {storage_id}")


# Example usage and testing
if __name__ == "__main__":
    # Initialize encryptor
    encryptor = DataEncryptor()
    
    # Test data encryption
    test_data = b"Sensitive forensic evidence data - case #12345"
    
    # Encrypt
    encrypted = encryptor.encrypt_data(test_data)
    print(f"Encrypted: {encrypted['ciphertext'][:50]}...")
    
    # Decrypt
    decrypted = encryptor.decrypt_data(encrypted)
    print(f"Decrypted: {decrypted.decode('utf-8')}")
    print(f"Match: {decrypted == test_data}")
    
    # Test file encryption
    print("\n--- File Encryption Test ---")
    test_file = "test_evidence.txt"
    with open(test_file, 'w') as f:
        f.write("Confidential case information\nSuspect: John Doe\nEvidence: Digital traces")
    
    encrypted_file = encryptor.encrypt_file(test_file)
    print(f"File encrypted: {encrypted_file}")
    
    decrypted_file = encryptor.decrypt_file(encrypted_file, "test_decrypted.txt")
    print(f"File decrypted: {decrypted_file}")
    
    # Test secure storage
    print("\n--- Secure Storage Test ---")
    storage = SecureStorage()
    
    evidence_data = {
        'type': 'digital_evidence',
        'description': 'WhatsApp messages with crypto transactions',
        'messages': [
            {'from': '+91XXXXXXXXXX', 'text': 'Transfer BTC to wallet: 1A1z...'},
            {'from': '+91XXXXXXXXXX', 'text': 'Meeting at midnight'}
        ]
    }
    
    storage_id = storage.store_secure('CASE_2024_001', 'evidence', evidence_data)
    print(f"Stored with ID: {storage_id}")
    
    retrieved = storage.retrieve_secure('CASE_2024_001', storage_id, 'evidence')
    print(f"Retrieved: {retrieved['type']}")
    print(f"Match: {retrieved == evidence_data}")
    
    # Cleanup
    os.remove(test_file)
    os.remove(encrypted_file)
    os.remove("test_decrypted.txt")