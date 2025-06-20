import time
import threading
import subprocess
import os
from pathlib import Path
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
from symlink_manager import SymlinkManager
from roblox_launcher import RobloxLauncher
def _clean_roblosecurity_cookie(cookie: str) -> str:
    """
    Clean the .ROBLOSECURITY cookie by removing warning prefixes.
    Args:
        cookie: Raw cookie string that may contain warning prefixes
    Returns:
        Cleaned cookie value
    """
    warning_prefix = "_|WARNING"
    if cookie.startswith(warning_prefix):
        return cookie.split('|_')[-1]
    return cookie
class IsolatedRobloxLauncher:
    """
    Enhanced Roblox launcher with full LocalStorage isolation using symbolic links.
    Integrates with Fishtrap for multi-instance launching while maintaining data isolation.
    """
    def __init__(self, callback=None):
        """
        Initialize the isolated launcher.
        Args:
            callback: Optional callback function for status updates
        """
        self.callback = callback
        self.symlink_manager = SymlinkManager()
        self.roblox_launcher = RobloxLauncher(status_callback=callback)  # Original launcher for browser automation
        self.active_sessions = []  # Track browser sessions
        self.launch_threads = []   # Track launch threads
        self.active_launches = {}  # Track active Roblox launches {account_name: launch_info}
    def _log_status(self, message: str) -> None:
        """
        Log a status message through the callback if available.
        Args:
            message: Status message to log
        """
        if self.callback:
            self.callback(message)
        else:
            print(message)
    def _setup_firefox_options(self) -> Options:
        """
        Configure Firefox options for automation with minimal resource usage.
        Returns:
            Configured Firefox options
        """
        firefox_options = Options()
        firefox_options.add_argument("--headless")
        firefox_options.add_argument("--no-sandbox")
        firefox_options.add_argument("--disable-dev-shm-usage")
        firefox_options.add_argument("--disable-gpu")
        firefox_options.add_argument("--disable-extensions")
        firefox_options.add_argument("--disable-images")
        firefox_options.set_preference("dom.webdriver.enabled", False)
        firefox_options.set_preference("useAutomationExtension", False)
        firefox_options.set_preference("general.useragent.override", 
                                     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
        firefox_options.set_preference("network.protocol-handler.external.roblox", True)
        firefox_options.set_preference("network.protocol-handler.external.roblox-player", True)
        firefox_options.set_preference("network.protocol-handler.warn-external.roblox", False)
        firefox_options.set_preference("network.protocol-handler.warn-external.roblox-player", False)
        firefox_options.set_preference("dom.webnotifications.enabled", False)
        firefox_options.set_preference("dom.push.enabled", False)
        return firefox_options
    def _inject_cookie(self, driver, roblosecurity_cookie: str) -> bool:
        """
        Inject .ROBLOSECURITY cookie into the browser session.
        Args:
            driver: Selenium WebDriver instance
            roblosecurity_cookie: The .ROBLOSECURITY cookie value
        Returns:
            True if injection was successful, False otherwise
        """
        try:
            self._log_status("Navigating to Roblox for cookie injection...")
            driver.get("https://www.roblox.com")
            time.sleep(2)
            driver.delete_all_cookies()
            clean_cookie = _clean_roblosecurity_cookie(roblosecurity_cookie)
            driver.add_cookie({
                'name': '.ROBLOSECURITY',
                'value': clean_cookie,
                'domain': '.roblox.com',
                'path': '/',
                'secure': True,
                'httpOnly': True
            })
            self._log_status("Authentication cookie injected successfully")
            driver.get("https://www.roblox.com/home")
            time.sleep(2)
            cookies = driver.get_cookies()
            cookie_present = any(c['name'] == '.ROBLOSECURITY' for c in cookies)
            if cookie_present:
                self._log_status("Cookie verification successful")
            else:
                self._log_status("Warning: Cookie verification failed")
            return cookie_present
        except Exception as e:
            error_msg = f"Cookie injection failed: {e}"
            self._log_status(error_msg)
            return False
    def _find_roblox_executable(self) -> Optional[Path]:
        """
        Find the Roblox executable path in the system.
        Returns:
            Path to RobloxPlayerBeta.exe or None if not found
        """
        possible_paths = [
            Path(os.environ.get('LOCALAPPDATA', '')) / "Roblox" / "Versions",
            Path(os.environ.get('PROGRAMFILES', '')) / "Roblox" / "Versions",
            Path(os.environ.get('PROGRAMFILES(X86)', '')) / "Roblox" / "Versions",
        ]
        for base_path in possible_paths:
            if base_path.exists():
                for version_dir in base_path.iterdir():
                    if version_dir.is_dir():
                        roblox_exe = version_dir / "RobloxPlayerBeta.exe"
                        if roblox_exe.exists():
                            return roblox_exe
        return None
    def _find_fishtrap_executable(self) -> Optional[Path]:
        """
        Find Fishtrap executable for multi-instance launching.
        Returns:
            Path to Fishtrap executable or None if not found
        """
        possible_paths = [
            Path("C:/Fishtrap/Fishtrap.exe"),
            Path("C:/Program Files/Fishtrap/Fishtrap.exe"),
            Path("C:/Program Files (x86)/Fishtrap/Fishtrap.exe"),
            Path(os.environ.get('USERPROFILE', '')) / "Desktop" / "Fishtrap.exe",
            Path(os.environ.get('USERPROFILE', '')) / "Documents" / "Fishtrap" / "Fishtrap.exe",        ]
        for path in possible_paths:
            if path.exists():
                return path
        return None
    def _extract_place_id(self, url: str) -> Optional[str]:
        """
        Extract place ID from various Roblox URL formats.
        Args:
            url: The Roblox server/game URL
        Returns:
            Place ID string or None if not found
        """
        import re
        patterns = [
            r'roblox\.com/games/(\d+)',           # Standard game URL
            r'placeId=(\d+)',                     # Direct place ID
            r'placeid=(\d+)',                     # Case insensitive
            r'/games/(\d+)/',                     # Games with additional paths
            r'share\?id=(\d+)',                   # Share URLs with id parameter
        ]
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
        if 'roblox.com/share?' in url.lower() and 'code=' in url.lower():
            self._log_status("Detected private server share URL - will launch directly")
            return "PRIVATE_SERVER"  # Special marker for private server URLs
        return None
    def _launch_roblox_with_fishtrap(self, server_url: str, account_name: str) -> bool:
        """
        Launch Roblox using Fishtrap multi-instance tool.
        Args:
            server_url: The server/game URL to join
            account_name: Name of the account (for logging)
        Returns:
            True if launch was successful, False otherwise
        """
        try:
            fishtrap_exe = self._find_fishtrap_executable()
            if not fishtrap_exe:
                self._log_status("Fishtrap not found, trying direct Roblox launch...")
                return self._launch_roblox_direct(server_url, account_name)
            self._log_status(f"Launching Roblox via Fishtrap for {account_name}...")
            place_id = self._extract_place_id(server_url)
            if not place_id:
                self._log_status(f"Could not extract place ID from URL: {server_url}")
                return False
            if place_id == "PRIVATE_SERVER":
                roblox_protocol_url = server_url
                self._log_status(f"Using private server URL directly: {server_url}")
            else:
                roblox_protocol_url = f"roblox://placeID={place_id}"
            process = subprocess.Popen(
                [str(fishtrap_exe), "--game-url", roblox_protocol_url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.active_launches[account_name] = {
                'process': process,
                'fishtrap_exe': fishtrap_exe,
                'server_url': server_url,
                'launched_at': time.time()
            }
            self._log_status(f"Fishtrap launch initiated for {account_name}")
            return True
        except Exception as e:
            self._log_status(f"Fishtrap launch failed for {account_name}: {e}")
            return False
    def _launch_roblox_direct(self, server_url: str, account_name: str) -> bool:
        """
        Launch Roblox directly using protocol handler.
        Args:
            server_url: The server/game URL to join
            account_name: Name of the account (for logging)
        Returns:
            True if launch was successful, False otherwise
        """
        try:
            self._log_status(f"Launching Roblox directly for {account_name}...")
            place_id = self._extract_place_id(server_url)
            if not place_id:
                self._log_status(f"Could not extract place ID from URL: {server_url}")
                return False
            if place_id == "PRIVATE_SERVER":
                launch_url = server_url
                self._log_status(f"Launching private server URL directly: {server_url}")
            else:
                launch_url = f"roblox://placeID={place_id}"
                self._log_status(f"Launching place ID {place_id} via protocol")
            if place_id == "PRIVATE_SERVER":
                process = subprocess.Popen(
                    ['cmd', '/c', 'start', '', launch_url],
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                process = subprocess.Popen(
                    ['cmd', '/c', 'start', '', launch_url],
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            self.active_launches[account_name] = {
                'process': process,
                'server_url': server_url,
                'launched_at': time.time()
            }
            self._log_status(f"Direct Roblox launch initiated for {account_name}")
            return True
        except Exception as e:
            self._log_status(f"Direct Roblox launch failed for {account_name}: {e}")
            return False
    def launch_account_isolated(self, account_name: str, roblosecurity_cookie: str, server_url: str) -> bool:
        """
        Launch a single account with full LocalStorage isolation using symbolic links.
        This method:
        1. Creates symlink isolation for LocalStorage
        2. Authenticates via browser automation
        3. Launches Roblox via Fishtrap or direct protocol
        4. Maintains isolation during gameplay
        Args:
            account_name: Name of the account to launch
            roblosecurity_cookie: The .ROBLOSECURITY cookie for authentication
            server_url: The server/game URL to join
        Returns:
            True if launch was successful, False otherwise
        """
        driver = None
        backup_path = None
        try:
            self._log_status(f"Starting isolated launch for {account_name}...")
            self._log_status(f"Creating LocalStorage isolation for {account_name}...")
            isolation_success, backup_path = self.symlink_manager.create_storage_isolation(account_name)
            if not isolation_success:
                raise Exception("Failed to create LocalStorage isolation")
            self._log_status(f"Setting up browser session for {account_name}...")
            firefox_options = self._setup_firefox_options()
            service = Service(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=firefox_options)
            self.active_sessions.append(driver)
            if not self._inject_cookie(driver, roblosecurity_cookie):
                raise Exception("Failed to inject authentication cookie")
            self._log_status(f"Navigating to game page for {account_name}...")
            driver.get(server_url)
            time.sleep(3)
            driver.quit()
            if driver in self.active_sessions:
                self.active_sessions.remove(driver)
            driver = None
            self._log_status(f"Launching Roblox instance for {account_name}...")
            launch_success = self._launch_roblox_with_fishtrap(server_url, account_name)
            if launch_success:
                self._log_status(f"{account_name} launched successfully with LocalStorage isolation")
                return True
            else:
                raise Exception("Failed to launch Roblox instance")
        except Exception as e:
            error_msg = f"{account_name} launch failed: {str(e)}"
            self._log_status(error_msg)
            if self.symlink_manager.is_isolation_active(account_name):
                self.symlink_manager.remove_storage_isolation(
                    account_name, 
                    restore_backup=True, 
                    backup_path=backup_path
                )
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                    if driver in self.active_sessions:
                        self.active_sessions.remove(driver)
                except:
                    pass
    def launch_multiple_accounts(self, accounts_data: list, server_url: str, delay_between_launches: int = 5) -> list:
        """
        Launch multiple accounts with LocalStorage isolation using sequential method.
        Due to Windows symlink limitations, accounts are launched one at a time:
        1. Create isolation for account
        2. Launch account with authentication
        3. Wait for Roblox to cache session data
        4. Remove isolation
        5. Repeat for next account
        Args:
            accounts_data: List of tuples (account_name, roblosecurity_cookie)
            server_url: The server/game URL to join
            delay_between_launches: Delay in seconds between launching each account
        Returns:
            List of threading.Thread objects for the launch operations
        """
        self._log_status(f"Starting sequential multi-account launch for {len(accounts_data)} accounts...")
        self._log_status("Note: Accounts will launch one at a time due to symlink limitations")
        def sequential_launch():
            for i, (account_name, cookie) in enumerate(accounts_data):
                try:
                    self._log_status(f"Launching account {i+1}/{len(accounts_data)}: {account_name}")
                    success = self.launch_account_with_temporary_isolation(account_name, cookie, server_url)
                    if success:
                        self._log_status(f"Successfully launched {account_name}")
                    else:
                        self._log_status(f"Failed to launch {account_name}")
                    if i < len(accounts_data) - 1:
                        self._log_status(f"Waiting {delay_between_launches} seconds before next launch...")
                        time.sleep(delay_between_launches)
                except Exception as e:
                    self._log_status(f"Error launching {account_name}: {e}")
                    continue
            self._log_status("Multi-account launch sequence completed")
        thread = threading.Thread(target=sequential_launch, daemon=True)
        thread.start()
        self.launch_threads.append(thread)
        return [thread]
    def launch_account_with_temporary_isolation(self, account_name: str, roblosecurity_cookie: str, server_url: str) -> bool:
        """
        Launch account with temporary symlink isolation that gets removed after authentication caching.
        This method:
        1. Creates temporary symlink isolation
        2. Uses original RobloxLauncher for browser automation and Roblox launching
        3. Removes symlink isolation after launch
        Args:
            account_name: Name of the account to launch
            roblosecurity_cookie: The .ROBLOSECURITY cookie for authentication
            server_url: The server/game URL to join
        Returns:
            True if launch was successful, False otherwise
        """
        backup_path = None
        try:
            self._log_status(f"Starting temporary isolation launch for {account_name}...")
            self._log_status(f"Creating temporary LocalStorage isolation for {account_name}...")
            isolation_success, backup_path = self.symlink_manager.create_storage_isolation(account_name)
            if not isolation_success:
                raise Exception("Failed to create LocalStorage isolation")
            self._log_status(f"Launching Roblox with browser automation for {account_name}...")
            launch_thread = self.roblox_launcher.launch_account(account_name, roblosecurity_cookie, server_url)
            if launch_thread:
                launch_thread.join(timeout=60)  # Wait up to 60 seconds for launch to complete
                self._log_status(f"Launch thread completed for {account_name}")
            self._log_status(f"Waiting for Roblox to initialize for {account_name}...")
            time.sleep(10)  # Give Roblox time to start and cache the session
            self._log_status(f"Removing temporary isolation for {account_name}...")
            self.symlink_manager.remove_storage_isolation(account_name, restore_backup=True, backup_path=backup_path)
            self._log_status(f"{account_name} launched successfully with temporary isolation")
            return True
        except Exception as e:
            error_msg = f"{account_name} temporary isolation launch failed: {str(e)}"
            self._log_status(error_msg)
            if self.symlink_manager.is_isolation_active(account_name):
                self.symlink_manager.remove_storage_isolation(
                    account_name, 
                    restore_backup=True, 
                    backup_path=backup_path
                )
            return False
    def launch_account_direct_only(self, account_name: str, roblosecurity_cookie: str, server_url: str) -> bool:
        """
        Launch account using direct protocol join only (no browser automation).
        This method:
        1. Creates temporary symlink isolation
        2. Directly launches Roblox via protocol handler (no browser)
        3. Removes symlink isolation after launch
        This prevents double-launching by skipping browser automation entirely.
        Args:
            account_name: Name of the account to launch
            roblosecurity_cookie: The .ROBLOSECURITY cookie for authentication
            server_url: The server/game URL to join
        Returns:
            True if launch was successful, False otherwise
        """
        backup_path = None
        try:
            self._log_status(f"Starting direct-only launch for {account_name}...")
            self._log_status(f"Creating temporary LocalStorage isolation for {account_name}...")
            isolation_success, backup_path = self.symlink_manager.create_storage_isolation(account_name)
            if not isolation_success:
                raise Exception("Failed to create LocalStorage isolation")
            place_id = self._extract_place_id(server_url)
            if not place_id:
                self._log_status(f"Could not extract place ID from URL: {server_url}")
                return False
            if place_id == "PRIVATE_SERVER":
                launch_url = server_url
                self._log_status(f"Launching private server URL directly for {account_name}: {server_url}")
            else:
                launch_url = f"roblox://placeID={place_id}"
                self._log_status(f"Launching place ID {place_id} for {account_name} via protocol")
            process = subprocess.Popen(
                ['cmd', '/c', 'start', '', launch_url],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.active_launches[account_name] = {
                'process': process,
                'server_url': server_url,
                'launched_at': time.time(),
                'method': 'direct_only'
            }
            self._log_status(f"Waiting for Roblox to initialize for {account_name}...")
            time.sleep(5)  # Give Roblox time to start
            self._log_status(f"Removing temporary isolation for {account_name}...")
            self.symlink_manager.remove_storage_isolation(account_name, restore_backup=True, backup_path=backup_path)
            self._log_status(f"{account_name} launched successfully with direct-only method")
            return True
        except Exception as e:
            error_msg = f"{account_name} direct-only launch failed: {str(e)}"
            self._log_status(error_msg)
            if self.symlink_manager.is_isolation_active(account_name):
                self.symlink_manager.remove_storage_isolation(
                    account_name, 
                    restore_backup=True, 
                    backup_path=backup_path
                )
            return False
    def launch_private_server_headless(self, account_name: str, roblosecurity_cookie: str, server_url: str) -> bool:
        """
        Launch account for private server using headless browser with cookie injection.
        This method specifically for private server links:
        1. Creates temporary symlink isolation
        2. Opens headless browser with cookie injection
        3. Loads the private server URL
        4. Does NOT click Play button - waits for protocol handler to trigger
        5. Closes browser and removes isolation
        Args:
            account_name: Name of the account to launch
            roblosecurity_cookie: The .ROBLOSECURITY cookie for authentication
            server_url: The private server URL to join
        Returns:
            True if launch was successful, False otherwise
        """
        backup_path = None
        driver = None
        try:
            self._log_status(f"Starting private server headless launch for {account_name}...")
            self._log_status(f"Creating temporary LocalStorage isolation for {account_name}...")
            isolation_success, backup_path = self.symlink_manager.create_storage_isolation(account_name)
            if not isolation_success:
                raise Exception("Failed to create LocalStorage isolation")
            self._log_status(f"Setting up headless browser for {account_name}...")
            firefox_options = Options()
            firefox_options.add_argument("--headless")
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")
            firefox_options.add_argument("--disable-gpu")
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)
            service = Service(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=firefox_options)
            self._log_status(f"Navigating to Roblox and injecting cookies for {account_name}...")
            driver.get("https://www.roblox.com")
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            cleaned_cookie = _clean_roblosecurity_cookie(roblosecurity_cookie)
            driver.add_cookie({
                'name': '.ROBLOSECURITY',
                'value': cleaned_cookie,
                'domain': '.roblox.com',
                'path': '/',
                'secure': True,
                'httpOnly': True
            })
            self._log_status(f"Loading private server URL for {account_name}: {server_url}")
            driver.get(server_url)
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            self._log_status(f"Waiting for Roblox protocol to trigger for {account_name}...")
            time.sleep(8)  # Give time for protocol handler and Roblox to start
            self.active_launches[account_name] = {
                'process': None,  # No direct process for protocol launches
                'server_url': server_url,
                'launched_at': time.time(),
                'method': 'private_server_headless'
            }
            self._log_status(f"{account_name} private server launched successfully via protocol")
            return True
        except Exception as e:
            error_msg = f"{account_name} private server headless launch failed: {str(e)}"
            self._log_status(error_msg)
            return False
        finally:
            try:
                if driver:
                    self._log_status(f"Closing browser for {account_name}...")
                    driver.quit()
            except:
                pass  # Ignore browser cleanup errors
            try:
                if self.symlink_manager.is_isolation_active(account_name):
                    self._log_status(f"Removing temporary isolation for {account_name}...")
                    self.symlink_manager.remove_storage_isolation(
                        account_name, 
                        restore_backup=True, 
                        backup_path=backup_path
                    )
            except Exception as e:
                self._log_status(f"Warning: Could not remove isolation for {account_name}: {e}")
    def cleanup_old_data(self, max_age_hours: int = 168) -> dict:
        """
        Clean up old data including backups and unused instance directories.
        Args:
            max_age_hours: Maximum age in hours before cleanup
        Returns:
            Dictionary with cleanup results
        """
        results = {
            'backups_cleaned': 0,
            'instances_cleaned': 0
        }
        results['backups_cleaned'] = self.symlink_manager.cleanup_old_backups(max_age_hours)
        self._log_status(f"Cleanup completed: {results['backups_cleaned']} backups removed")
        return results
