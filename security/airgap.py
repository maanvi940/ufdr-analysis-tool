"""
Air-gapped Deployment Security Module
Provides security features for operating in air-gapped environments
"""

import os
import logging
import json
import hashlib
import base64
from typing import Dict, Union, Any
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AirgapSecurityManager:
    """
    Security manager for air-gapped deployments
    Handles model validation, data isolation, and access controls
    """
    
    def __init__(self, 
                config_path: str = "config/airgap_security.json",
                enable_strict_mode: bool = True):
        """
        Initialize the air-gapped security manager
        
        Args:
            config_path: Path to security configuration file
            enable_strict_mode: Whether to enable strict security checks
        """
        self.config_path = config_path
        self.strict_mode = enable_strict_mode
        self.config = self._load_config()
        self.security_log_path = self.config.get("security_log_path", "logs/security.log")
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.security_log_path), exist_ok=True)
        
        # Initialize file handler for security logs
        self.file_handler = logging.FileHandler(self.security_log_path)
        self.file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.file_handler.setFormatter(formatter)
        logger.addHandler(self.file_handler)
        
        # Log initialization
        self.log_security_event("security_manager_initialized", 
                               {"strict_mode": self.strict_mode})
    
    def _load_config(self) -> Dict:
        """Load security configuration from file"""
        default_config = {
            "allowed_model_paths": ["infra/models/"],
            "allowed_data_paths": ["data/"],
            "network_access": False,
            "allowed_users": ["admin"],
            "model_checksums": {},
            "security_log_path": "logs/security.log",
            "data_isolation_enabled": True,
            "encryption_enabled": True
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Loaded security configuration from {self.config_path}")
                    return config
            else:
                # Create default config if it doesn't exist
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                logger.info(f"Created default security configuration at {self.config_path}")
                return default_config
        except Exception as e:
            logger.error(f"Error loading security configuration: {str(e)}")
            return default_config
    
    def log_security_event(self, 
                          event_type: str, 
                          details: Dict[str, Any]) -> None:
        """
        Log a security event
        
        Args:
            event_type: Type of security event
            details: Details about the event
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "details": details
        }
        
        logger.info(f"Security event: {event_type} - {json.dumps(details)}")
    
    def validate_model_path(self, model_path: str) -> bool:
        """
        Validate that a model path is allowed
        
        Args:
            model_path: Path to model file
            
        Returns:
            True if the model path is allowed, False otherwise
        """
        # Check if path is within allowed directories
        allowed = False
        for allowed_path in self.config.get("allowed_model_paths", []):
            if model_path.startswith(allowed_path):
                allowed = True
                break
        
        if not allowed:
            self.log_security_event("unauthorized_model_access", 
                                   {"model_path": model_path})
            return False
        
        # Check model checksum if available
        checksums = self.config.get("model_checksums", {})
        if model_path in checksums and os.path.exists(model_path):
            expected_checksum = checksums[model_path]
            actual_checksum = self._compute_file_checksum(model_path)
            
            if expected_checksum != actual_checksum:
                self.log_security_event("model_checksum_mismatch", 
                                       {"model_path": model_path,
                                        "expected": expected_checksum,
                                        "actual": actual_checksum})
                return False
        
        return True
    
    def validate_data_path(self, data_path: str) -> bool:
        """
        Validate that a data path is allowed
        
        Args:
            data_path: Path to data file or directory
            
        Returns:
            True if the data path is allowed, False otherwise
        """
        # Check if path is within allowed directories
        allowed = False
        for allowed_path in self.config.get("allowed_data_paths", []):
            if data_path.startswith(allowed_path):
                allowed = True
                break
        
        if not allowed:
            self.log_security_event("unauthorized_data_access", 
                                   {"data_path": data_path})
            return False
        
        return True
    
    def _compute_file_checksum(self, file_path: str) -> str:
        """
        Compute SHA-256 checksum of a file
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex digest of SHA-256 hash
        """
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                # Read and update hash in chunks for memory efficiency
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error computing checksum for {file_path}: {str(e)}")
            return ""
    
    def register_model_checksum(self, model_path: str) -> bool:
        """
        Register the checksum of a model file
        
        Args:
            model_path: Path to model file
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(model_path):
            logger.error(f"Model file not found: {model_path}")
            return False
        
        try:
            checksum = self._compute_file_checksum(model_path)
            
            # Update config
            self.config.setdefault("model_checksums", {})[model_path] = checksum
            
            # Save updated config
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            self.log_security_event("model_checksum_registered", 
                                   {"model_path": model_path, 
                                    "checksum": checksum})
            
            return True
        except Exception as e:
            logger.error(f"Error registering model checksum: {str(e)}")
            return False
    
    def check_network_access(self) -> bool:
        """
        Check if network access is allowed
        
        Returns:
            True if network access is allowed, False otherwise
        """
        network_access = self.config.get("network_access", False)
        
        if network_access and self.strict_mode:
            self.log_security_event("network_access_warning", 
                                   {"allowed": network_access, 
                                    "strict_mode": self.strict_mode})
        
        return network_access
    
    def validate_user_access(self, user_id: str) -> bool:
        """
        Validate that a user has access
        
        Args:
            user_id: User ID
            
        Returns:
            True if the user has access, False otherwise
        """
        allowed_users = self.config.get("allowed_users", [])
        
        if not allowed_users or user_id in allowed_users:
            return True
        
        self.log_security_event("unauthorized_user_access", 
                               {"user_id": user_id})
        return False
    
    def encrypt_data(self, data: Union[str, bytes]) -> str:
        """
        Encrypt data for secure storage
        Simple implementation for demonstration purposes
        In production, use proper cryptographic libraries
        
        Args:
            data: Data to encrypt
            
        Returns:
            Base64-encoded encrypted data
        """
        if not self.config.get("encryption_enabled", True):
            # Return base64 encoded data without encryption
            if isinstance(data, str):
                data = data.encode('utf-8')
            return base64.b64encode(data).decode('utf-8')
        
        # In a real implementation, use proper encryption
        # This is just a placeholder
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # XOR with a fixed key (NOT secure, just for demonstration)
        key = b'AIRGAP_SECURITY_KEY'
        encrypted = bytearray()
        for i, byte in enumerate(data):
            encrypted.append(byte ^ key[i % len(key)])
        
        # Return base64 encoded
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt_data(self, encrypted_data: str) -> bytes:
        """
        Decrypt data
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            
        Returns:
            Decrypted data
        """
        # Decode base64
        data = base64.b64decode(encrypted_data)
        
        if not self.config.get("encryption_enabled", True):
            return data
        
        # In a real implementation, use proper decryption
        # This is just a placeholder matching the encrypt_data method
        key = b'AIRGAP_SECURITY_KEY'
        decrypted = bytearray()
        for i, byte in enumerate(data):
            decrypted.append(byte ^ key[i % len(key)])
        
        return bytes(decrypted)
    
    def ensure_data_isolation(self, case_id: str, data_path: str) -> str:
        """
        Ensure data isolation between cases
        
        Args:
            case_id: Case ID
            data_path: Path to data
            
        Returns:
            Isolated data path
        """
        if not self.config.get("data_isolation_enabled", True):
            return data_path
        
        # Create isolated directory for case
        case_dir = os.path.join("data", "cases", case_id)
        os.makedirs(case_dir, exist_ok=True)
        
        # If data_path is already in the case directory, return it
        if data_path.startswith(case_dir):
            return data_path
        
        # Otherwise, create a symbolic link or copy
        filename = os.path.basename(data_path)
        isolated_path = os.path.join(case_dir, filename)
        
        # Log the isolation
        self.log_security_event("data_isolation", 
                               {"case_id": case_id,
                                "original_path": data_path,
                                "isolated_path": isolated_path})
        
        return isolated_path


def create_default_config():
    """Create default security configuration file"""
    config_path = "config/airgap_security.json"
    
    default_config = {
        "allowed_model_paths": ["infra/models/"],
        "allowed_data_paths": ["data/"],
        "network_access": False,
        "allowed_users": ["admin"],
        "model_checksums": {},
        "security_log_path": "logs/security.log",
        "data_isolation_enabled": True,
        "encryption_enabled": True
    }
    
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    print(f"Created default security configuration at {config_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Air-gapped Security Manager")
    parser.add_argument("--create-config", action="store_true", 
                        help="Create default security configuration")
    parser.add_argument("--register-model", type=str,
                        help="Register checksum for a model file")
    
    args = parser.parse_args()
    
    if args.create_config:
        create_default_config()
    
    if args.register_model:
        security_manager = AirgapSecurityManager()
        if security_manager.register_model_checksum(args.register_model):
            print(f"Successfully registered checksum for {args.register_model}")
        else:
            print(f"Failed to register checksum for {args.register_model}")