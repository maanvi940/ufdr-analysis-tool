"""
Enhanced Vector Index Manager
Adds versioning, safe reindexing, backup/restore, and batch operations
"""

import json
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

try:
    from .index_builder import VectorIndexBuilder
except ImportError:
    from vector.index_builder import VectorIndexBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IndexVersion:
    """Metadata for an index version"""
    version: str
    created_at: str
    total_documents: int
    total_cases: int
    model_name: str
    dimension: int
    checksum: str
    description: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


class EnhancedIndexManager:
    """
    Enhanced vector index manager with versioning and safe operations
    
    Features:
    - Index versioning and history
    - Safe reindexing with rollback
    - Backup and restore
    - Batch operations
    - Index validation
    """
    
    def __init__(self, 
                 index_dir: str = "data/indices",
                 backup_dir: str = "data/indices/backups",
                 model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Initialize enhanced index manager
        
        Args:
            index_dir: Primary index directory
            backup_dir: Directory for index backups
            model_name: Sentence transformer model name
        """
        self.index_dir = Path(index_dir)
        self.backup_dir = Path(backup_dir)
        self.model_name = model_name
        
        # Create directories
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Version tracking
        self.versions_file = self.index_dir / "versions.json"
        self.current_version_file = self.index_dir / "current_version.txt"
        
        # Initialize index builder
        self.index_builder = VectorIndexBuilder(
            model_name=model_name,
            index_dir=str(self.index_dir)
        )
        
        # Load version history
        self.versions = self._load_versions()
        
    def _load_versions(self) -> Dict[str, IndexVersion]:
        """Load version history from disk"""
        if not self.versions_file.exists():
            return {}
        
        with open(self.versions_file, 'r') as f:
            data = json.load(f)
        
        return {
            v['version']: IndexVersion(**v) 
            for v in data.get('versions', [])
        }
    
    def _save_versions(self):
        """Save version history to disk"""
        data = {
            'versions': [v.to_dict() for v in self.versions.values()],
            'updated_at': datetime.utcnow().isoformat()
        }
        
        with open(self.versions_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _compute_index_checksum(self) -> str:
        """Compute checksum for current index"""
        index_path = self.index_dir / "faiss.index"
        mapping_path = self.index_dir / "doc_mapping.pkl"
        
        sha256 = hashlib.sha256()
        
        if index_path.exists():
            with open(index_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
        
        if mapping_path.exists():
            with open(mapping_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
        
        return sha256.hexdigest()[:16]
    
    def create_version(self, description: str = "") -> IndexVersion:
        """
        Create a new version of the current index
        
        Args:
            description: Description of this version
            
        Returns:
            IndexVersion object
        """
        stats = self.index_builder.get_index_stats()
        
        version = IndexVersion(
            version=datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
            created_at=datetime.utcnow().isoformat(),
            total_documents=stats['total_documents'],
            total_cases=len(stats['cases']),
            model_name=self.model_name,
            dimension=stats['dimension'],
            checksum=self._compute_index_checksum(),
            description=description
        )
        
        # Save version metadata
        self.versions[version.version] = version
        self._save_versions()
        
        # Update current version marker
        with open(self.current_version_file, 'w') as f:
            f.write(version.version)
        
        logger.info(f"Created index version: {version.version}")
        return version
    
    def backup_current_index(self, version: Optional[str] = None) -> Path:
        """
        Backup the current index
        
        Args:
            version: Version name (default: auto-generated timestamp)
            
        Returns:
            Path to backup directory
        """
        if version is None:
            version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        backup_path = self.backup_dir / version
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Copy index files
        files_to_backup = [
            "faiss.index",
            "vectors.npy",  # Fallback storage
            "doc_mapping.pkl",
            "versions.json",
            "current_version.txt"
        ]
        
        backed_up_files = []
        for filename in files_to_backup:
            source = self.index_dir / filename
            if source.exists():
                dest = backup_path / filename
                shutil.copy2(source, dest)
                backed_up_files.append(filename)
        
        # Save backup metadata
        metadata = {
            'version': version,
            'created_at': datetime.utcnow().isoformat(),
            'backed_up_files': backed_up_files,
            'checksum': self._compute_index_checksum()
        }
        
        with open(backup_path / "backup_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Backed up index to: {backup_path}")
        return backup_path
    
    def restore_from_backup(self, version: str) -> bool:
        """
        Restore index from a backup
        
        Args:
            version: Version to restore
            
        Returns:
            True if successful
        """
        backup_path = self.backup_dir / version
        
        if not backup_path.exists():
            raise ValueError(f"Backup version not found: {version}")
        
        # Load backup metadata
        metadata_file = backup_path / "backup_metadata.json"
        if not metadata_file.exists():
            raise ValueError(f"Backup metadata not found for version: {version}")
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        logger.info(f"Restoring index from backup: {version}")
        
        # Create safety backup of current state
        safety_backup = self.backup_current_index(
            version=f"pre_restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )
        logger.info(f"Created safety backup at: {safety_backup}")
        
        try:
            # Restore files
            for filename in metadata['backed_up_files']:
                source = backup_path / filename
                dest = self.index_dir / filename
                
                if source.exists():
                    shutil.copy2(source, dest)
                    logger.info(f"Restored: {filename}")
            
            # Reload index builder
            self.index_builder = VectorIndexBuilder(
                model_name=self.model_name,
                index_dir=str(self.index_dir)
            )
            
            # Reload versions
            self.versions = self._load_versions()
            
            logger.info(f"Successfully restored index from version: {version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            logger.info(f"Safety backup available at: {safety_backup}")
            return False
    
    def safe_reindex(self,
                    case_ids: List[str],
                    parsed_dir: str = "data/parsed",
                    description: str = "") -> bool:
        """
        Safely reindex cases with automatic backup and rollback
        
        Args:
            case_ids: List of case IDs to reindex
            parsed_dir: Directory with parsed data
            description: Description of reindex operation
            
        Returns:
            True if successful
        """
        # Create pre-reindex backup
        backup_version = f"pre_reindex_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup_current_index(version=backup_version)
        logger.info(f"Created backup before reindex: {backup_path}")
        
        try:
            # Perform reindexing
            total_indexed = 0
            for case_id in case_ids:
                logger.info(f"Reindexing case: {case_id}")
                count = self.index_builder.index_case_artifacts(
                    case_id=case_id,
                    parsed_dir=parsed_dir
                )
                total_indexed += count
                logger.info(f"Indexed {count} artifacts from case {case_id}")
            
            # Verify index integrity
            if not self.verify_index_integrity():
                raise ValueError("Index integrity check failed after reindex")
            
            # Create new version
            self.create_version(
                description=f"Reindexed {len(case_ids)} cases: {', '.join(case_ids)}. {description}"
            )
            
            logger.info(f"Successfully reindexed {total_indexed} artifacts")
            return True
            
        except Exception as e:
            logger.error(f"Reindex failed: {e}")
            logger.info("Rolling back to pre-reindex state...")
            
            # Rollback to backup
            if self.restore_from_backup(backup_version):
                logger.info("Successfully rolled back to pre-reindex state")
            else:
                logger.error("Rollback failed! Manual restoration may be required")
            
            return False
    
    def verify_index_integrity(self) -> bool:
        """
        Verify index integrity
        
        Returns:
            True if index is valid
        """
        try:
            stats = self.index_builder.get_index_stats()
            
            # Check basic stats
            if stats['total_vectors'] < 0 or stats['total_documents'] < 0:
                logger.error("Invalid index statistics")
                return False
            
            # Check files exist
            index_path = self.index_dir / "faiss.index"
            mapping_path = self.index_dir / "doc_mapping.pkl"
            vectors_path = self.index_dir / "vectors.npy"
            
            # At least one index storage should exist
            if not index_path.exists() and not vectors_path.exists():
                logger.error("No index storage found")
                return False
            
            if not mapping_path.exists():
                logger.error("Document mapping not found")
                return False
            
            # Verify counts match
            if stats['total_vectors'] != stats['total_documents']:
                logger.warning(f"Vector count ({stats['total_vectors']}) != document count ({stats['total_documents']})")
            
            logger.info("Index integrity check passed")
            return True
            
        except Exception as e:
            logger.error(f"Index integrity check failed: {e}")
            return False
    
    def batch_add_documents(self,
                           documents: List[Dict],
                           case_id: str,
                           batch_size: int = 100) -> int:
        """
        Add documents in batches for better performance
        
        Args:
            documents: List of document dictionaries with 'content' and 'metadata'
            case_id: Case identifier
            batch_size: Documents per batch
            
        Returns:
            Total documents added
        """
        total_added = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            texts = [doc['content'] for doc in batch]
            metadatas = [doc.get('metadata', {}) for doc in batch]
            
            self.index_builder.add_text_batch(texts, metadatas, case_id)
            total_added += len(batch)
            
            logger.info(f"Added batch {i // batch_size + 1}: {len(batch)} documents")
        
        logger.info(f"Total documents added: {total_added}")
        return total_added
    
    def get_version_history(self) -> List[IndexVersion]:
        """Get list of all index versions, sorted by date"""
        return sorted(
            self.versions.values(),
            key=lambda v: v.created_at,
            reverse=True
        )
    
    def get_current_version(self) -> Optional[str]:
        """Get the current version identifier"""
        if self.current_version_file.exists():
            return self.current_version_file.read_text().strip()
        return None
    
    def list_backups(self) -> List[Dict]:
        """List all available backups"""
        backups = []
        
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / "backup_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    backups.append(metadata)
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)
    
    def cleanup_old_backups(self, keep_n: int = 5):
        """
        Remove old backups, keeping only the N most recent
        
        Args:
            keep_n: Number of backups to keep
        """
        backups = self.list_backups()
        
        if len(backups) <= keep_n:
            logger.info(f"Only {len(backups)} backups exist, nothing to clean")
            return
        
        to_remove = backups[keep_n:]
        
        for backup_meta in to_remove:
            backup_version = backup_meta['version']
            backup_path = self.backup_dir / backup_version
            
            if backup_path.exists():
                shutil.rmtree(backup_path)
                logger.info(f"Removed old backup: {backup_version}")
        
        logger.info(f"Cleaned up {len(to_remove)} old backups")
    
    def get_index_stats(self) -> Dict:
        """Get comprehensive index statistics"""
        stats = self.index_builder.get_index_stats()
        
        # Add version info
        stats['current_version'] = self.get_current_version()
        stats['total_versions'] = len(self.versions)
        stats['index_checksum'] = self._compute_index_checksum()
        
        # Add backup info
        stats['total_backups'] = len(self.list_backups())
        
        return stats
    
    def export_index_metadata(self, output_file: str):
        """Export index metadata for documentation"""
        metadata = {
            'index_statistics': self.get_index_stats(),
            'version_history': [v.to_dict() for v in self.get_version_history()],
            'backups': self.list_backups(),
            'model_name': self.model_name,
            'index_directory': str(self.index_dir),
            'exported_at': datetime.utcnow().isoformat()
        }
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Exported index metadata to: {output_path}")


def main():
    """CLI interface for enhanced index manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Vector Index Manager")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Backup current index')
    backup_parser.add_argument('--version', help='Version name (default: timestamp)')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('version', help='Version to restore')
    
    # Reindex command
    reindex_parser = subparsers.add_parser('reindex', help='Safely reindex cases')
    reindex_parser.add_argument('case_ids', nargs='+', help='Case IDs to reindex')
    reindex_parser.add_argument('--description', default='', help='Reindex description')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify index integrity')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List backups or versions')
    list_parser.add_argument('--backups', action='store_true', help='List backups')
    list_parser.add_argument('--versions', action='store_true', help='List versions')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show index statistics')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old backups')
    cleanup_parser.add_argument('--keep', type=int, default=5, help='Number of backups to keep')
    
    args = parser.parse_args()
    
    # Create manager
    manager = EnhancedIndexManager()
    
    try:
        if args.command == 'backup':
            backup_path = manager.backup_current_index(version=args.version)
            print(f"\n✓ Backup created: {backup_path}")
        
        elif args.command == 'restore':
            if manager.restore_from_backup(args.version):
                print(f"\n✓ Successfully restored from version: {args.version}")
            else:
                print(f"\n✗ Failed to restore from version: {args.version}")
                return 1
        
        elif args.command == 'reindex':
            if manager.safe_reindex(args.case_ids, description=args.description):
                print(f"\n✓ Successfully reindexed cases: {', '.join(args.case_ids)}")
            else:
                print(f"\n✗ Reindex failed")
                return 1
        
        elif args.command == 'verify':
            if manager.verify_index_integrity():
                print("\n✓ Index integrity verified")
            else:
                print("\n✗ Index integrity check failed")
                return 1
        
        elif args.command == 'list':
            if args.backups:
                backups = manager.list_backups()
                print(f"\nAvailable backups ({len(backups)}):")
                for backup in backups:
                    print(f"  - {backup['version']} ({backup['created_at']})")
            
            if args.versions:
                versions = manager.get_version_history()
                print(f"\nVersion history ({len(versions)}):")
                for version in versions:
                    print(f"  - {version.version}: {version.description}")
                    print(f"    Created: {version.created_at}")
                    print(f"    Documents: {version.total_documents}, Cases: {version.total_cases}")
        
        elif args.command == 'stats':
            stats = manager.get_index_stats()
            print("\nIndex Statistics:")
            print(f"  Total vectors: {stats['total_vectors']}")
            print(f"  Total documents: {stats['total_documents']}")
            print(f"  Dimension: {stats['dimension']}")
            print(f"  Cases: {len(stats['cases'])}")
            print(f"  Current version: {stats['current_version']}")
            print(f"  Total versions: {stats['total_versions']}")
            print(f"  Total backups: {stats['total_backups']}")
            print(f"  Checksum: {stats['index_checksum']}")
        
        elif args.command == 'cleanup':
            manager.cleanup_old_backups(keep_n=args.keep)
            print(f"\n✓ Cleaned up old backups (kept {args.keep} most recent)")
        
        else:
            parser.print_help()
            return 1
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())