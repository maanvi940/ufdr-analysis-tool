# ============================================================
# UFDR Analysis Tool - Windows Backup Script
# ============================================================
#
# Automated backup script for Windows environments.
#
# Features:
# - Full backup of data, config, and logs
# - Compressed archives
# - Rotation (keeps last N backups)
# - Timestamp-based naming
# - Integrity verification
#
# Usage:
#   .\backup_windows.ps1
#   .\backup_windows.ps1 -BackupPath "D:\Backups"
#   .\backup_windows.ps1 -RetentionDays 30
#
# ============================================================

param(
    [string]$BackupPath = "C:\UFDR-Backups",
    [string]$InstallPath = "C:\UFDR-Analysis-Tool",
    [int]$RetentionDays = 30,
    [switch]$VerifyIntegrity,
    [switch]$Verbose
)

# ============================================================
# Configuration
# ============================================================

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupName = "ufdr_backup_$timestamp"
$backupDir = Join-Path $BackupPath $backupName

# Directories to backup
$dirsToBackup = @(
    "data",
    "logs",
    "exports",
    "vector"
)

# Files to backup
$filesToBackup = @(
    "config.env",
    "README.md"
)

# ============================================================
# Functions
# ============================================================

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    switch ($Level) {
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        "WARN"  { Write-Host $logMessage -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        default { Write-Host $logMessage }
    }
}

function Test-Prerequisites {
    Write-Log "Checking prerequisites..."
    
    # Check if installation directory exists
    if (-not (Test-Path $InstallPath)) {
        Write-Log "Installation directory not found: $InstallPath" "ERROR"
        return $false
    }
    
    # Check if backup directory can be created
    try {
        if (-not (Test-Path $BackupPath)) {
            New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
            Write-Log "Created backup directory: $BackupPath" "SUCCESS"
        }
    } catch {
        Write-Log "Failed to create backup directory: $_" "ERROR"
        return $false
    }
    
    Write-Log "Prerequisites check passed" "SUCCESS"
    return $true
}

function Backup-Directories {
    Write-Log "Backing up directories..."
    
    $currentDir = Get-Location
    Set-Location $InstallPath
    
    foreach ($dir in $dirsToBackup) {
        $sourcePath = Join-Path $InstallPath $dir
        $destPath = Join-Path $backupDir $dir
        
        if (Test-Path $sourcePath) {
            Write-Log "Backing up directory: $dir"
            
            try {
                # Create destination directory
                New-Item -ItemType Directory -Path $destPath -Force | Out-Null
                
                # Copy directory contents
                Copy-Item -Path "$sourcePath\*" -Destination $destPath -Recurse -Force
                
                # Get size
                $size = (Get-ChildItem -Path $destPath -Recurse | Measure-Object -Property Length -Sum).Sum
                $sizeMB = [math]::Round($size / 1MB, 2)
                
                Write-Log "  Backed up $dir ($sizeMB MB)" "SUCCESS"
            } catch {
                Write-Log "  Failed to backup $dir : $_" "ERROR"
            }
        } else {
            Write-Log "  Directory not found, skipping: $dir" "WARN"
        }
    }
    
    Set-Location $currentDir
}

function Backup-Files {
    Write-Log "Backing up configuration files..."
    
    foreach ($file in $filesToBackup) {
        $sourcePath = Join-Path $InstallPath $file
        $destPath = Join-Path $backupDir $file
        
        if (Test-Path $sourcePath) {
            Write-Log "Backing up file: $file"
            
            try {
                Copy-Item -Path $sourcePath -Destination $destPath -Force
                Write-Log "  Backed up $file" "SUCCESS"
            } catch {
                Write-Log "  Failed to backup $file : $_" "ERROR"
            }
        } else {
            Write-Log "  File not found, skipping: $file" "WARN"
        }
    }
}

function Compress-Backup {
    Write-Log "Compressing backup..."
    
    $archivePath = "$backupDir.zip"
    
    try {
        # Compress backup directory
        Compress-Archive -Path $backupDir -DestinationPath $archivePath -CompressionLevel Optimal -Force
        
        # Get archive size
        $archiveSize = (Get-Item $archivePath).Length
        $archiveSizeMB = [math]::Round($archiveSize / 1MB, 2)
        
        Write-Log "Backup compressed: $archivePath ($archiveSizeMB MB)" "SUCCESS"
        
        # Remove uncompressed backup directory
        Remove-Item -Path $backupDir -Recurse -Force
        Write-Log "Removed uncompressed backup directory"
        
        return $archivePath
    } catch {
        Write-Log "Failed to compress backup: $_" "ERROR"
        return $null
    }
}

function Test-BackupIntegrity {
    param([string]$ArchivePath)
    
    Write-Log "Verifying backup integrity..."
    
    try {
        # Test archive by extracting to temp
        $tempPath = Join-Path $env:TEMP "ufdr_verify_$timestamp"
        Expand-Archive -Path $ArchivePath -DestinationPath $tempPath -Force
        
        # Check if key files exist
        $verified = $true
        foreach ($dir in $dirsToBackup) {
            $checkPath = Join-Path $tempPath "$backupName\$dir"
            if (-not (Test-Path $checkPath)) {
                Write-Log "  Missing directory in backup: $dir" "WARN"
                $verified = $false
            }
        }
        
        # Clean up temp
        Remove-Item -Path $tempPath -Recurse -Force
        
        if ($verified) {
            Write-Log "Backup integrity verified" "SUCCESS"
        } else {
            Write-Log "Backup integrity check failed" "ERROR"
        }
        
        return $verified
    } catch {
        Write-Log "Failed to verify backup: $_" "ERROR"
        return $false
    }
}

function Remove-OldBackups {
    Write-Log "Cleaning up old backups (retention: $RetentionDays days)..."
    
    $cutoffDate = (Get-Date).AddDays(-$RetentionDays)
    $backups = Get-ChildItem -Path $BackupPath -Filter "ufdr_backup_*.zip"
    
    $removedCount = 0
    foreach ($backup in $backups) {
        if ($backup.LastWriteTime -lt $cutoffDate) {
            Write-Log "Removing old backup: $($backup.Name)"
            Remove-Item -Path $backup.FullName -Force
            $removedCount++
        }
    }
    
    if ($removedCount -eq 0) {
        Write-Log "No old backups to remove"
    } else {
        Write-Log "Removed $removedCount old backup(s)" "SUCCESS"
    }
}

function Write-BackupManifest {
    param([string]$ArchivePath)
    
    $manifestPath = "$ArchivePath.manifest.txt"
    
    $manifest = @"
UFDR Analysis Tool - Backup Manifest
=====================================

Backup Name: $backupName
Timestamp: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Archive: $ArchivePath
Size: $([math]::Round((Get-Item $ArchivePath).Length / 1MB, 2)) MB
Installation Path: $InstallPath

Backed up directories:
$(($dirsToBackup | ForEach-Object { "  - $_" }) -join "`n")

Backed up files:
$(($filesToBackup | ForEach-Object { "  - $_" }) -join "`n")

Retention: $RetentionDays days
"@

    $manifest | Out-File -FilePath $manifestPath -Encoding UTF8
    Write-Log "Backup manifest created: $manifestPath"
}

# ============================================================
# Main Execution
# ============================================================

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   UFDR Analysis Tool - Backup Script (Windows)          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Log "Starting backup process..."
Write-Log "Installation Path: $InstallPath"
Write-Log "Backup Path: $BackupPath"
Write-Log "Retention: $RetentionDays days"
Write-Host ""

# Step 1: Prerequisites
if (-not (Test-Prerequisites)) {
    Write-Log "Backup failed: Prerequisites check failed" "ERROR"
    exit 1
}

# Step 2: Create backup directory
Write-Log "Creating backup directory: $backupDir"
try {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
} catch {
    Write-Log "Failed to create backup directory: $_" "ERROR"
    exit 1
}

# Step 3: Backup directories
Backup-Directories

# Step 4: Backup files
Backup-Files

# Step 5: Compress backup
$archivePath = Compress-Backup
if (-not $archivePath) {
    Write-Log "Backup failed: Compression failed" "ERROR"
    exit 1
}

# Step 6: Verify integrity (optional)
if ($VerifyIntegrity) {
    if (-not (Test-BackupIntegrity -ArchivePath $archivePath)) {
        Write-Log "Backup failed: Integrity check failed" "ERROR"
        exit 1
    }
}

# Step 7: Write manifest
Write-BackupManifest -ArchivePath $archivePath

# Step 8: Clean up old backups
Remove-OldBackups

Write-Host ""
Write-Log "Backup completed successfully!" "SUCCESS"
Write-Log "Backup archive: $archivePath"

# Step 9: Summary
$totalBackups = (Get-ChildItem -Path $BackupPath -Filter "ufdr_backup_*.zip").Count
Write-Log "Total backups in storage: $totalBackups"

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

exit 0