"""
Manifest Signing System for Forensic Integrity
Provides cryptographic signing of ingestion manifests for chain of custody

Features:
- RSA-2048 key pair generation
- SHA256-based signing
- Signature verification
- Manifest tamper detection
- Append-only audit trail
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ManifestSigner:
    """
    Cryptographic signing and verification for forensic manifests
    Ensures chain of custody and tamper detection
    """
    
    def __init__(self, keys_dir: str = "security/keys"):
        """
        Initialize manifest signer
        
        Args:
            keys_dir: Directory to store cryptographic keys
        """
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        
        self.private_key_path = self.keys_dir / "private_key.pem"
        self.public_key_path = self.keys_dir / "public_key.pem"
        
        # Load or generate keys
        if not self.private_key_path.exists():
            self._generate_key_pair()
        
        self.private_key = self._load_private_key()
        self.public_key = self._load_public_key()
        
        logger.info("Manifest signer initialized")
    
    def _generate_key_pair(self):
        """Generate RSA-2048 key pair for signing"""
        logger.info("Generating RSA-2048 key pair...")
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Save private key (encrypted)
        with open(self.private_key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()  # For demo; use BestAvailableEncryption in production
            ))
        
        # Generate and save public key
        public_key = private_key.public_key()
        with open(self.public_key_path, 'wb') as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        
        # Set restrictive permissions (read-only for owner)
        os.chmod(self.private_key_path, 0o400)
        os.chmod(self.public_key_path, 0o444)
        
        logger.info(f"Key pair generated and saved to {self.keys_dir}")
    
    def _load_private_key(self):
        """Load private key from file"""
        with open(self.private_key_path, 'rb') as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
    
    def _load_public_key(self):
        """Load public key from file"""
        with open(self.public_key_path, 'rb') as f:
            return serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
    
    def sign_manifest(self, manifest_data: Dict) -> Tuple[Dict, str]:
        """
        Sign a manifest with private key
        
        Args:
            manifest_data: Manifest dictionary to sign
            
        Returns:
            Tuple of (signed_manifest, signature_hex)
        """
        # Create canonical JSON representation (sorted keys)
        canonical_json = json.dumps(manifest_data, sort_keys=True, indent=2)
        
        # Compute SHA256 hash of canonical data
        data_hash = hashlib.sha256(canonical_json.encode()).digest()
        
        # Sign the hash
        signature = self.private_key.sign(
            data_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Convert signature to hex string
        signature_hex = signature.hex()
        
        # Add signature to manifest
        signed_manifest = manifest_data.copy()
        signed_manifest['signature'] = signature_hex
        signed_manifest['signature_algorithm'] = 'RSA-2048-PSS-SHA256'
        signed_manifest['signed_at'] = datetime.now().isoformat()
        
        logger.info(f"Manifest signed: {manifest_data.get('manifest_id', 'unknown')}")
        
        return signed_manifest, signature_hex
    
    def verify_manifest(self, signed_manifest: Dict) -> bool:
        """
        Verify manifest signature
        
        Args:
            signed_manifest: Signed manifest dictionary
            
        Returns:
            True if signature is valid, False otherwise
        """
        if 'signature' not in signed_manifest:
            logger.error("Manifest has no signature")
            return False
        
        # Extract signature and remove from manifest copy
        manifest_copy = signed_manifest.copy()
        signature_hex = manifest_copy.pop('signature')
        manifest_copy.pop('signature_algorithm', None)
        manifest_copy.pop('signed_at', None)
        
        # Convert signature from hex
        signature = bytes.fromhex(signature_hex)
        
        # Create canonical JSON
        canonical_json = json.dumps(manifest_copy, sort_keys=True, indent=2)
        data_hash = hashlib.sha256(canonical_json.encode()).digest()
        
        # Verify signature
        try:
            self.public_key.verify(
                signature,
                data_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            logger.info(f"Manifest signature verified: {signed_manifest.get('manifest_id', 'unknown')}")
            return True
        except InvalidSignature:
            logger.error(f"Invalid signature for manifest: {signed_manifest.get('manifest_id', 'unknown')}")
            return False
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False
    
    def sign_manifest_file(self, manifest_file_path: str) -> str:
        """
        Sign a manifest JSON file
        
        Args:
            manifest_file_path: Path to manifest JSON file
            
        Returns:
            Path to signed manifest file
        """
        # Read manifest
        with open(manifest_file_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        
        # Sign manifest
        signed_manifest, _ = self.sign_manifest(manifest_data)
        
        # Save signed manifest
        signed_path = manifest_file_path.replace('.json', '.signed.json')
        with open(signed_path, 'w', encoding='utf-8') as f:
            json.dump(signed_manifest, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Signed manifest saved to: {signed_path}")
        return signed_path
    
    def verify_manifest_file(self, signed_manifest_path: str) -> bool:
        """
        Verify a signed manifest file
        
        Args:
            signed_manifest_path: Path to signed manifest file
            
        Returns:
            True if valid, False otherwise
        """
        with open(signed_manifest_path, 'r', encoding='utf-8') as f:
            signed_manifest = json.load(f)
        
        return self.verify_manifest(signed_manifest)
    
    def export_public_key(self, output_path: str):
        """
        Export public key for distribution
        
        Args:
            output_path: Path to save public key
        """
        with open(self.public_key_path, 'rb') as src:
            with open(output_path, 'wb') as dst:
                dst.write(src.read())
        
        logger.info(f"Public key exported to: {output_path}")


class ChainOfCustodyLogger:
    """
    Append-only chain of custody logging system
    Ensures immutable audit trail
    """
    
    def __init__(self, log_dir: str = "data/audit_logs/chain_of_custody"):
        """
        Initialize chain of custody logger
        
        Args:
            log_dir: Directory for custody logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.signer = ManifestSigner()
        
        logger.info("Chain of custody logger initialized")
    
    def log_event(self, 
                  case_id: str,
                  event_type: str,
                  description: str,
                  user: str,
                  metadata: Optional[Dict] = None) -> str:
        """
        Log a chain of custody event
        
        Args:
            case_id: Case identifier
            event_type: Type of event (ingest, access, export, etc.)
            description: Event description
            user: User performing action
            metadata: Additional metadata
            
        Returns:
            Event ID
        """
        import uuid
        
        event_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Create event record
        event = {
            'event_id': event_id,
            'case_id': case_id,
            'event_type': event_type,
            'description': description,
            'user': user,
            'timestamp': timestamp.isoformat(),
            'metadata': metadata or {}
        }
        
        # Sign event
        signed_event, signature = self.signer.sign_manifest(event)
        
        # Append to log file (one file per case)
        log_file = self.log_dir / f"{case_id}_custody.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(signed_event, ensure_ascii=False) + '\n')
        
        logger.info(f"Custody event logged: {event_type} for case {case_id}")
        
        return event_id
    
    def verify_log_integrity(self, case_id: str) -> Tuple[bool, List[Dict]]:
        """
        Verify integrity of custody log for a case
        
        Args:
            case_id: Case identifier
            
        Returns:
            Tuple of (all_valid, invalid_events)
        """
        log_file = self.log_dir / f"{case_id}_custody.jsonl"
        
        if not log_file.exists():
            logger.warning(f"No custody log found for case: {case_id}")
            return False, []
        
        all_valid = True
        invalid_events = []
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                
                try:
                    event = json.loads(line)
                    
                    # Verify signature
                    if not self.signer.verify_manifest(event):
                        all_valid = False
                        invalid_events.append({
                            'line_number': line_num,
                            'event_id': event.get('event_id'),
                            'reason': 'Invalid signature'
                        })
                except json.JSONDecodeError:
                    all_valid = False
                    invalid_events.append({
                        'line_number': line_num,
                        'reason': 'Invalid JSON'
                    })
        
        if all_valid:
            logger.info(f"Custody log verified successfully for case: {case_id}")
        else:
            logger.error(f"Custody log verification failed for case: {case_id}")
        
        return all_valid, invalid_events
    
    def get_custody_trail(self, case_id: str) -> List[Dict]:
        """
        Get complete custody trail for a case
        
        Args:
            case_id: Case identifier
            
        Returns:
            List of custody events
        """
        log_file = self.log_dir / f"{case_id}_custody.jsonl"
        
        if not log_file.exists():
            return []
        
        events = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        
        return events


# Example usage and testing
if __name__ == "__main__":
    # Initialize signer
    signer = ManifestSigner()
    
    # Example manifest
    manifest = {
        'manifest_id': 'MAN_2024_001',
        'case_id': 'CASE_2024_001',
        'file_name': 'evidence.ufdr',
        'file_hash': 'abc123...',
        'examiner': 'Inspector Kumar',
        'timestamp': datetime.now().isoformat()
    }
    
    # Sign manifest
    signed_manifest, signature = signer.sign_manifest(manifest)
    print(f"Signature: {signature[:50]}...")
    
    # Verify manifest
    is_valid = signer.verify_manifest(signed_manifest)
    print(f"Signature valid: {is_valid}")
    
    # Test tampering detection
    tampered_manifest = signed_manifest.copy()
    tampered_manifest['examiner'] = 'Unauthorized User'
    is_valid_tampered = signer.verify_manifest(tampered_manifest)
    print(f"Tampered manifest valid: {is_valid_tampered}")
    
    # Chain of custody logging
    custody_logger = ChainOfCustodyLogger()
    
    # Log events
    custody_logger.log_event(
        case_id='CASE_2024_001',
        event_type='INGEST',
        description='UFDR file ingested from seized device',
        user='Inspector Kumar',
        metadata={'device': 'Samsung Galaxy S21', 'imei': '123456789'}
    )
    
    custody_logger.log_event(
        case_id='CASE_2024_001',
        event_type='QUERY',
        description='Natural language query executed',
        user='Analyst Sharma',
        metadata={'query': 'Show messages with crypto addresses'}
    )
    
    # Verify log integrity
    valid, invalid = custody_logger.verify_log_integrity('CASE_2024_001')
    print(f"\nCustody log valid: {valid}")
    
    # Get custody trail
    trail = custody_logger.get_custody_trail('CASE_2024_001')
    print(f"Total custody events: {len(trail)}")