"""
Audit logging for Knowledge Graph operations
"""

import json
import logging
import hashlib
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GraphAuditLogger:
    """
    Audit logger for Knowledge Graph operations
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize the audit logger
        
        Args:
            log_dir: Directory to store audit logs (defaults to data/audit_logs)
        """
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path(__file__).parent.parent / "data" / "audit_logs"
        
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a separate file logger for audit logs
        self.audit_logger = logging.getLogger("graph_audit")
        self.audit_logger.setLevel(logging.INFO)
        
        # Add file handler if not already added
        if not self.audit_logger.handlers:
            audit_file = self.log_dir / "graph_audit.log"
            file_handler = logging.FileHandler(audit_file)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            self.audit_logger.addHandler(file_handler)
    
    def log_operation(self, 
                     operation_type: str, 
                     user_id: str, 
                     case_id: Optional[str] = None,
                     details: Optional[Dict[str, Any]] = None,
                     query: Optional[str] = None) -> str:
        """
        Log a graph operation
        
        Args:
            operation_type: Type of operation (e.g., 'query', 'ingest', 'delete')
            user_id: ID of the user performing the operation
            case_id: Optional case ID related to the operation
            details: Optional details about the operation
            query: Optional query executed
            
        Returns:
            Audit log entry ID
        """
        timestamp = datetime.datetime.now().isoformat()
        
        # Create audit log entry
        log_entry = {
            "timestamp": timestamp,
            "operation_type": operation_type,
            "user_id": user_id,
            "case_id": case_id,
            "details": details or {},
            "query": query
        }
        
        # Generate a unique ID for the log entry
        entry_id = self._generate_entry_id(log_entry)
        log_entry["entry_id"] = entry_id
        
        # Log to audit log file
        self.audit_logger.info(json.dumps(log_entry))
        
        # For high-value operations, also write to a separate JSON file
        if operation_type in ["ingest", "delete", "modify", "case_linkage"]:
            self._write_to_json_file(entry_id, log_entry)
        
        return entry_id
    
    def _generate_entry_id(self, log_entry: Dict[str, Any]) -> str:
        """Generate a unique ID for the log entry"""
        entry_str = json.dumps(log_entry, sort_keys=True)
        return hashlib.sha256(entry_str.encode()).hexdigest()[:16]
    
    def _write_to_json_file(self, entry_id: str, log_entry: Dict[str, Any]) -> None:
        """Write log entry to a JSON file"""
        # Create a directory for the current date
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        date_dir = self.log_dir / date_str
        date_dir.mkdir(exist_ok=True)
        
        # Write to JSON file
        file_path = date_dir / f"{entry_id}.json"
        with open(file_path, 'w') as f:
            json.dump(log_entry, f, indent=2)
    
    def get_audit_trail(self, 
                       case_id: Optional[str] = None, 
                       user_id: Optional[str] = None,
                       operation_type: Optional[str] = None,
                       start_time: Optional[str] = None,
                       end_time: Optional[str] = None) -> list:
        """
        Get audit trail filtered by parameters
        
        Args:
            case_id: Optional case ID to filter by
            user_id: Optional user ID to filter by
            operation_type: Optional operation type to filter by
            start_time: Optional start time (ISO format)
            end_time: Optional end time (ISO format)
            
        Returns:
            List of audit log entries
        """
        # Read the audit log file
        audit_file = self.log_dir / "graph_audit.log"
        if not audit_file.exists():
            return []
        
        entries = []
        with open(audit_file, 'r') as f:
            for line in f:
                try:
                    # Extract the JSON part of the log line
                    json_str = line.split(' - ')[-1]
                    entry = json.loads(json_str)
                    
                    # Apply filters
                    if case_id and entry.get("case_id") != case_id:
                        continue
                    if user_id and entry.get("user_id") != user_id:
                        continue
                    if operation_type and entry.get("operation_type") != operation_type:
                        continue
                    if start_time and entry.get("timestamp") < start_time:
                        continue
                    if end_time and entry.get("timestamp") > end_time:
                        continue
                    
                    entries.append(entry)
                except Exception as e:
                    logger.error(f"Error parsing audit log line: {str(e)}")
        
        return entries


# Example usage
if __name__ == "__main__":
    audit_logger = GraphAuditLogger()
    
    # Log a query operation
    entry_id = audit_logger.log_operation(
        operation_type="query",
        user_id="test_user",
        case_id="TEST_CASE_001",
        query="MATCH (p:Person) WHERE p.name CONTAINS 'John' RETURN p",
        details={"source_ip": "127.0.0.1", "client": "web_ui"}
    )
    
    print(f"Logged query operation with ID: {entry_id}")
    
    # Get audit trail
    audit_trail = audit_logger.get_audit_trail(case_id="TEST_CASE_001")
    print(f"Found {len(audit_trail)} audit entries for case TEST_CASE_001")