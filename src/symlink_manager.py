import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple
import platform
class SymlinkManager:
    """
    Manages symbolic link creation and cleanup for Roblox LocalStorage isolation.
    Provides safe symlink operations with proper error handling and rollback.
    """
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.instances_dir = self.base_dir / "roblox_instances"
        self.instances_dir.mkdir(exist_ok=True)
        self.roblox_localappdata = Path(os.environ.get('LOCALAPPDATA', '')) / "Roblox"
        self.roblox_localstorage = self.roblox_localappdata / "LocalStorage"
        self.active_symlinks = {}  # {account_name: original_path}
    def _is_windows(self) -> bool:
        """Check if running on Windows."""
        return platform.system().lower() == 'windows'
    def _sanitize_account_name(self, account_name: str) -> str:
        """
        Sanitize account name for safe filesystem usage.
        Args:
            account_name: Raw account name
        Returns:
            Sanitized account name safe for directories
        """
        invalid_chars = '<>:"/\\|?*'
        sanitized = account_name
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        sanitized = sanitized.strip()[:50]
        if not sanitized:
            sanitized = "account"
        return sanitized
    def _backup_existing_localstorage(self, account_name: str) -> Optional[Path]:
        """
        No longer creates backups. Returns None.
        """
        return None
    def _create_isolated_directory(self, account_name: str) -> Path:
        """
        Create isolated directory structure for an account.
        Args:
            account_name: Name of the account
        Returns:
            Path to the account's isolated directory
        """
        sanitized_name = self._sanitize_account_name(account_name)
        account_dir = self.instances_dir / sanitized_name
        account_dir.mkdir(exist_ok=True)
        localstorage_dir = account_dir / "LocalStorage"
        localstorage_dir.mkdir(exist_ok=True)
        for subdir in ["logs", "cache", "content", "versions"]:
            (account_dir / subdir).mkdir(exist_ok=True)
        return account_dir
    def _create_symlink_windows(self, target: Path, link: Path) -> bool:
        """
        Create symbolic link on Windows using mklink command.
        Args:
            target: Path to target directory
            link: Path where symlink should be created
        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = f'mklink /D "{link}" "{target}"'
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                check=True
            )
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"Windows symlink creation failed: {e}")
            print(f"   Command: {cmd}")
            print(f"   Error output: {e.stderr}")
            return False
        except Exception as e:
            print(f"Unexpected error creating Windows symlink: {e}")
            return False
    def _create_symlink_unix(self, target: Path, link: Path) -> bool:
        """
        Create symbolic link on Unix-like systems using os.symlink.
        Args:
            target: Path to target directory
            link: Path where symlink should be created
        Returns:
            True if successful, False otherwise
        """
        try:
            os.symlink(str(target), str(link))
            return True
        except OSError as e:
            print(f"Unix symlink creation failed: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error creating Unix symlink: {e}")
            return False
    def create_storage_isolation(self, account_name: str) -> Tuple[bool, Optional[Path]]:
        """
        Create LocalStorage isolation for a specific account using symbolic links.
        This function:
        1. Creates isolated directory for the account
        2. Backs up existing LocalStorage if present
        3. Removes original LocalStorage
        4. Creates symlink from LocalStorage to isolated directory
        Args:
            account_name: Name of the account to isolate
        Returns:
            Tuple of (success: bool, backup_path: Optional[Path])
        """
        try:
            print(f"Creating storage isolation for account: {account_name}")
            account_dir = self._create_isolated_directory(account_name)
            isolated_localstorage = account_dir / "LocalStorage"
            print(f"Isolated directory created: {account_dir}")
            backup_path = None
            if self.roblox_localstorage.exists():
                backup_path = self._backup_existing_localstorage(account_name)
                try:
                    if self.roblox_localstorage.is_symlink():
                        self.roblox_localstorage.unlink()
                    else:
                        shutil.rmtree(self.roblox_localstorage)
                    print(f"🗑️ Removed existing LocalStorage")
                except Exception as e:
                    print(f"Failed to remove existing LocalStorage: {e}")
                    return False, backup_path
            self.roblox_localstorage.parent.mkdir(parents=True, exist_ok=True)
            success = False
            if self._is_windows():
                success = self._create_symlink_windows(isolated_localstorage, self.roblox_localstorage)
            else:
                success = self._create_symlink_unix(isolated_localstorage, self.roblox_localstorage)
            if success:
                self.active_symlinks[account_name] = str(isolated_localstorage)
                print(f"Symlink created successfully")
                print(f"   {self.roblox_localstorage} → {isolated_localstorage}")
                return True, backup_path
            else:
                print(f"Failed to create symlink")
                if backup_path and backup_path.exists():
                    try:
                        shutil.copytree(backup_path, self.roblox_localstorage)
                        print(f"🔄 Restored backup from: {backup_path}")
                    except Exception as e:
                        print(f"Warning: Could not restore backup: {e}")
                return False, backup_path
        except Exception as e:
            print(f"Storage isolation failed for {account_name}: {e}")
            return False, None
    def remove_storage_isolation(self, account_name: str, restore_backup: bool = False, backup_path: Optional[Path] = None) -> bool:
        """
        Remove LocalStorage isolation by removing the symlink.
        Args:
            account_name: Name of the account to clean up
            restore_backup: Whether to restore original LocalStorage from backup
            backup_path: Path to backup to restore (if restore_backup is True)
        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            print(f"Removing storage isolation for account: {account_name}")
            if self.roblox_localstorage.exists() and self.roblox_localstorage.is_symlink():
                self.roblox_localstorage.unlink()
                print(f"Removed symlink: {self.roblox_localstorage}")
            if account_name in self.active_symlinks:
                del self.active_symlinks[account_name]
            if restore_backup and backup_path and backup_path.exists():
                try:
                    shutil.copytree(backup_path, self.roblox_localstorage)
                    print(f"🔄 Restored LocalStorage from backup: {backup_path}")
                except Exception as e:
                    print(f"Warning: Could not restore backup: {e}")
            print(f"Storage isolation cleanup completed for {account_name}")
            return True
        except Exception as e:
            print(f"Cleanup failed for {account_name}: {e}")
            return False
    def cleanup_all_isolations(self) -> int:
        """
        Clean up all active storage isolations.
        Returns:
            Number of isolations cleaned up
        """
        cleaned_count = 0
        account_names = list(self.active_symlinks.keys())
        for account_name in account_names:
            if self.remove_storage_isolation(account_name):
                cleaned_count += 1
        return cleaned_count
    def is_isolation_active(self, account_name: str) -> bool:
        """
        Check if storage isolation is currently active for an account.
        Args:
            account_name: Name of the account to check
        Returns:
            True if isolation is active, False otherwise
        """
        return (account_name in self.active_symlinks and 
                self.roblox_localstorage.exists() and 
                self.roblox_localstorage.is_symlink())
    def get_isolation_status(self) -> dict:
        """
        Get status of all active isolations.
        Returns:
            Dictionary with isolation status information
        """
        status = {
            'active_isolations': len(self.active_symlinks),
            'roblox_localstorage_exists': self.roblox_localstorage.exists(),
            'roblox_localstorage_is_symlink': (self.roblox_localstorage.exists() and 
                                             self.roblox_localstorage.is_symlink()),
            'isolations': {}
        }
        for account_name, target_path in self.active_symlinks.items():
            status['isolations'][account_name] = {
                'target_path': target_path,
                'target_exists': Path(target_path).exists(),
                'is_active': self.is_isolation_active(account_name)
            }
        return status
    def cleanup_old_backups(self, max_age_hours: int = 168) -> int:
        """
        No longer needed. Returns 0.
        """
        return 0
    def _get_roblox_localstorage_path(self) -> Path:
        """
        Get the path to the Roblox LocalStorage directory.
        Returns:
            Path to the Roblox LocalStorage directory
        """
        return self.roblox_localstorage
    def get_isolation_info(self, account_name: str) -> dict:
        """
        Get detailed information about an account's isolation.
        Args:
            account_name: Name of the account to get info for
        Returns:
            Dictionary with isolation information
        """
        sanitized_name = self._sanitize_account_name(account_name)
        account_dir = self.instances_dir / sanitized_name
        isolated_localstorage = account_dir / "LocalStorage"
        return {
            'account_name': account_name,
            'sanitized_name': sanitized_name,
            'account_dir': str(account_dir),
            'isolated_localstorage': str(isolated_localstorage),
            'target_path': self.active_symlinks.get(account_name, ''),
            'target_exists': isolated_localstorage.exists(),
            'is_active': self.is_isolation_active(account_name),
            'symlink_exists': self.roblox_localstorage.exists(),
            'symlink_is_link': self.roblox_localstorage.is_symlink() if self.roblox_localstorage.exists() else False
        }
