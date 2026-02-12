"""
Security Integration Module
Integrates air-gapped security features with existing components
"""

import logging
from typing import Optional

from security.airgap import AirgapSecurityManager

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SecurityIntegration:
    """
    Integrates security features with existing components
    """
    
    def __init__(self, config_path: str = "config/airgap_security.json"):
        """
        Initialize security integration
        
        Args:
            config_path: Path to security configuration
        """
        self.security_manager = AirgapSecurityManager(config_path=config_path)
        logger.info("Security integration initialized")
    
    def secure_model_loading(self, model_path: str, user_id: str) -> bool:
        """
        Secure model loading with validation
        
        Args:
            model_path: Path to model
            user_id: User ID
            
        Returns:
            True if model loading is allowed, False otherwise
        """
        # Validate user access
        if not self.security_manager.validate_user_access(user_id):
            logger.warning(f"User {user_id} not authorized to load models")
            return False
        
        # Validate model path
        if not self.security_manager.validate_model_path(model_path):
            logger.warning(f"Model path {model_path} not authorized")
            return False
        
        # Log successful validation
        self.security_manager.log_security_event(
            "model_loading_authorized",
            {"model_path": model_path, "user_id": user_id}
        )
        
        return True
    
    def secure_data_access(self, data_path: str, user_id: str, case_id: Optional[str] = None) -> Optional[str]:
        """
        Secure data access with validation and isolation
        
        Args:
            data_path: Path to data
            user_id: User ID
            case_id: Optional case ID for data isolation
            
        Returns:
            Secured data path if access is allowed, None otherwise
        """
        # Validate user access
        if not self.security_manager.validate_user_access(user_id):
            logger.warning(f"User {user_id} not authorized to access data")
            return None
        
        # Validate data path
        if not self.security_manager.validate_data_path(data_path):
            logger.warning(f"Data path {data_path} not authorized")
            return None
        
        # Apply data isolation if case_id is provided
        if case_id:
            secured_path = self.security_manager.ensure_data_isolation(case_id, data_path)
        else:
            secured_path = data_path
        
        # Log successful validation
        self.security_manager.log_security_event(
            "data_access_authorized",
            {"data_path": data_path, "secured_path": secured_path, "user_id": user_id}
        )
        
        return secured_path
    
    def secure_network_operation(self, operation: str, user_id: str) -> bool:
        """
        Secure network operation
        
        Args:
            operation: Network operation description
            user_id: User ID
            
        Returns:
            True if network operation is allowed, False otherwise
        """
        # Check if network access is allowed
        if not self.security_manager.check_network_access():
            logger.warning(f"Network operation '{operation}' blocked in air-gapped mode")
            
            # Log blocked operation
            self.security_manager.log_security_event(
                "network_operation_blocked",
                {"operation": operation, "user_id": user_id}
            )
            
            return False
        
        # Validate user access
        if not self.security_manager.validate_user_access(user_id):
            logger.warning(f"User {user_id} not authorized for network operations")
            return False
        
        # Log authorized operation
        self.security_manager.log_security_event(
            "network_operation_authorized",
            {"operation": operation, "user_id": user_id}
        )
        
        return True
    
    def secure_storage(self, data: str, user_id: str) -> str:
        """
        Secure data storage with encryption
        
        Args:
            data: Data to store securely
            user_id: User ID
            
        Returns:
            Encrypted data
        """
        # Validate user access
        if not self.security_manager.validate_user_access(user_id):
            logger.warning(f"User {user_id} not authorized for secure storage")
            # Return empty string instead of raising exception
            return ""
        
        # Encrypt data
        encrypted = self.security_manager.encrypt_data(data)
        
        # Log encryption operation
        self.security_manager.log_security_event(
            "data_encrypted",
            {"user_id": user_id, "data_size": len(data)}
        )
        
        return encrypted
    
    def secure_retrieval(self, encrypted_data: str, user_id: str) -> bytes:
        """
        Secure data retrieval with decryption
        
        Args:
            encrypted_data: Encrypted data
            user_id: User ID
            
        Returns:
            Decrypted data
        """
        # Validate user access
        if not self.security_manager.validate_user_access(user_id):
            logger.warning(f"User {user_id} not authorized for secure retrieval")
            # Return empty bytes instead of raising exception
            return b""
        
        # Decrypt data
        decrypted = self.security_manager.decrypt_data(encrypted_data)
        
        # Log decryption operation
        self.security_manager.log_security_event(
            "data_decrypted",
            {"user_id": user_id, "data_size": len(decrypted)}
        )
        
        return decrypted


# Create singleton instance
security = SecurityIntegration()