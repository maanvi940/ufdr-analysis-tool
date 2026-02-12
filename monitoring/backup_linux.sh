#!/bin/bash
# ============================================================
# UFDR Analysis Tool - Linux Backup Script
# ============================================================
#
# Automated backup script for Linux environments.
#
# Features:
# - Full backup of data, config, and logs
# - Compressed tar.gz archives
# - Rotation (keeps last N backups)
# - Timestamp-based naming
# - Integrity verification
#
# Usage:
#   sudo ./backup_linux.sh
#   sudo ./backup_linux.sh /opt/custom-backup-path
#   sudo ./backup_linux.sh --retention-days 30
#
# ============================================================

set -e  # Exit on error

# ============================================================
# Configuration
# ============================================================

BACKUP_PATH="${1:-/opt/ufdr-backups}"
INSTALL_PATH="/opt/ufdr-analysis-tool"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="ufdr_backup_$TIMESTAMP"
BACKUP_DIR="$BACKUP_PATH/$BACKUP_NAME"
LOG_FILE="$BACKUP_PATH/backup_$TIMESTAMP.log"

# Directories to backup
DIRS_TO_BACKUP=(
    "data"
    "logs"
    "exports"
    "vector"
)

# Files to backup
FILES_TO_BACKUP=(
    "config.env"
    "README.md"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================
# Functions
# ============================================================

log() {
    local level="$1"
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        ERROR)
            echo -e "${RED}[$timestamp] [ERROR] $message${NC}" | tee -a "$LOG_FILE"
            ;;
        WARN)
            echo -e "${YELLOW}[$timestamp] [WARN] $message${NC}" | tee -a "$LOG_FILE"
            ;;
        SUCCESS)
            echo -e "${GREEN}[$timestamp] [SUCCESS] $message${NC}" | tee -a "$LOG_FILE"
            ;;
        *)
            echo "[$timestamp] [INFO] $message" | tee -a "$LOG_FILE"
            ;;
    esac
}

check_prerequisites() {
    log INFO "Checking prerequisites..."
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        log ERROR "This script must be run as root"
        exit 1
    fi
    
    # Check if installation directory exists
    if [ ! -d "$INSTALL_PATH" ]; then
        log ERROR "Installation directory not found: $INSTALL_PATH"
        exit 1
    fi
    
    # Check if backup directory can be created
    if [ ! -d "$BACKUP_PATH" ]; then
        mkdir -p "$BACKUP_PATH"
        log SUCCESS "Created backup directory: $BACKUP_PATH"
    fi
    
    # Check required commands
    for cmd in tar gzip date; do
        if ! command -v $cmd &> /dev/null; then
            log ERROR "Required command not found: $cmd"
            exit 1
        fi
    done
    
    log SUCCESS "Prerequisites check passed"
}

backup_directories() {
    log INFO "Backing up directories..."
    
    for dir in "${DIRS_TO_BACKUP[@]}"; do
        source_path="$INSTALL_PATH/$dir"
        dest_path="$BACKUP_DIR/$dir"
        
        if [ -d "$source_path" ]; then
            log INFO "Backing up directory: $dir"
            
            # Create destination directory
            mkdir -p "$dest_path"
            
            # Copy directory contents
            cp -r "$source_path"/* "$dest_path"/ 2>/dev/null || true
            
            # Get size
            size=$(du -sh "$dest_path" | cut -f1)
            log SUCCESS "  Backed up $dir ($size)"
        else
            log WARN "  Directory not found, skipping: $dir"
        fi
    done
}

backup_files() {
    log INFO "Backing up configuration files..."
    
    for file in "${FILES_TO_BACKUP[@]}"; do
        source_path="$INSTALL_PATH/$file"
        dest_path="$BACKUP_DIR/$file"
        
        if [ -f "$source_path" ]; then
            log INFO "Backing up file: $file"
            cp "$source_path" "$dest_path"
            log SUCCESS "  Backed up $file"
        else
            log WARN "  File not found, skipping: $file"
        fi
    done
}

compress_backup() {
    log INFO "Compressing backup..."
    
    archive_path="$BACKUP_DIR.tar.gz"
    
    cd "$BACKUP_PATH"
    tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME" 2>&1 | tee -a "$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        # Get archive size
        size=$(du -sh "$archive_path" | cut -f1)
        log SUCCESS "Backup compressed: $archive_path ($size)"
        
        # Remove uncompressed backup directory
        rm -rf "$BACKUP_DIR"
        log INFO "Removed uncompressed backup directory"
        
        echo "$archive_path"
        return 0
    else
        log ERROR "Failed to compress backup"
        return 1
    fi
}

verify_backup_integrity() {
    local archive_path="$1"
    
    log INFO "Verifying backup integrity..."
    
    # Test archive by listing contents
    if tar -tzf "$archive_path" > /dev/null 2>&1; then
        log SUCCESS "Backup integrity verified"
        return 0
    else
        log ERROR "Backup integrity check failed"
        return 1
    fi
}

remove_old_backups() {
    log INFO "Cleaning up old backups (retention: $RETENTION_DAYS days)..."
    
    # Find and remove backups older than retention period
    removed_count=0
    
    find "$BACKUP_PATH" -name "ufdr_backup_*.tar.gz" -type f -mtime +$RETENTION_DAYS | while read backup; do
        log INFO "Removing old backup: $(basename $backup)"
        rm -f "$backup"
        ((removed_count++))
    done
    
    if [ $removed_count -eq 0 ]; then
        log INFO "No old backups to remove"
    else
        log SUCCESS "Removed $removed_count old backup(s)"
    fi
}

write_backup_manifest() {
    local archive_path="$1"
    local manifest_path="$archive_path.manifest.txt"
    
    cat > "$manifest_path" <<EOF
UFDR Analysis Tool - Backup Manifest
=====================================

Backup Name: $BACKUP_NAME
Timestamp: $(date '+%Y-%m-%d %H:%M:%S')
Archive: $archive_path
Size: $(du -sh "$archive_path" | cut -f1)
Installation Path: $INSTALL_PATH

Backed up directories:
EOF

    for dir in "${DIRS_TO_BACKUP[@]}"; do
        echo "  - $dir" >> "$manifest_path"
    done

    cat >> "$manifest_path" <<EOF

Backed up files:
EOF

    for file in "${FILES_TO_BACKUP[@]}"; do
        echo "  - $file" >> "$manifest_path"
    done

    echo "" >> "$manifest_path"
    echo "Retention: $RETENTION_DAYS days" >> "$manifest_path"
    
    log INFO "Backup manifest created: $manifest_path"
}

# ============================================================
# Main Execution
# ============================================================

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   UFDR Analysis Tool - Backup Script (Linux)            ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create log file
mkdir -p "$BACKUP_PATH"
touch "$LOG_FILE"

log INFO "Starting backup process..."
log INFO "Installation Path: $INSTALL_PATH"
log INFO "Backup Path: $BACKUP_PATH"
log INFO "Retention: $RETENTION_DAYS days"
echo ""

# Step 1: Prerequisites
check_prerequisites

# Step 2: Create backup directory
log INFO "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Step 3: Backup directories
backup_directories

# Step 4: Backup files
backup_files

# Step 5: Compress backup
archive_path=$(compress_backup)
if [ -z "$archive_path" ]; then
    log ERROR "Backup failed: Compression failed"
    exit 1
fi

# Step 6: Verify integrity
if ! verify_backup_integrity "$archive_path"; then
    log ERROR "Backup failed: Integrity check failed"
    exit 1
fi

# Step 7: Write manifest
write_backup_manifest "$archive_path"

# Step 8: Clean up old backups
remove_old_backups

echo ""
log SUCCESS "Backup completed successfully!"
log INFO "Backup archive: $archive_path"

# Step 9: Summary
total_backups=$(find "$BACKUP_PATH" -name "ufdr_backup_*.tar.gz" -type f | wc -l)
log INFO "Total backups in storage: $total_backups"

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

exit 0