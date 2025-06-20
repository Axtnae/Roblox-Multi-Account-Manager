"""
Unified Roblox Launcher with full LocalStorage isolation and multi-browser support.
Combines functionality from isolated_launcher, improved_launcher, and roblox_launcher.
"""

import os
import time
import threading
import subprocess
import webbrowser
import tempfile
import random
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from storage import StorageManager
from encryption import EncryptionManager


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


class RobloxLauncher:
    """
    Unified Roblox launcher with LocalStorage isolation, multi-browser support,
    and enhanced process verification.
    
    Features:
    - Full LocalStorage isolation using symbolic links
    - Multi-browser support (Chrome, Edge, Firefox, Brave, Opera)
    - Process verification for reliable launch detection
    - Improved error handling and retry logic
    - Multiple launch methods for different server types
    """
    
    def __init__(self, callback=None, preferred_browser=None):
        """
        Initialize the unified launcher.
        Args:
            callback: Optional callback function for status updates
            preferred_browser: Preferred browser for automation
        """
        self.callback = callback
        self.storage_manager = StorageManager()
        
        # Browser setup
        self.active_drivers = []
        self.launch_threads = []
        self.preferred_browser = preferred_browser or self._detect_default_browser()
        self.supported_browsers = ['chrome', 'edge', 'firefox', 'brave', 'opera']
        
        # Launch tracking
        self.active_sessions = []  # Track browser sessions
        self.active_launches = {}  # Track active Roblox launches {account_name: launch_info}
        
        # Process limits
        self.max_concurrent_launches = 2  # Limit concurrent launches
        self.max_roblox_processes = 999   # Unlimited Roblox processes
        
    def _log_status(self, message: str) -> None:
        """Log status with callback or print."""
        if self.callback:
            self.callback(message)
        else:
            print(f"[RobloxLauncher] {message}")
    
    def _count_roblox_processes(self) -> int:
        """Count running Roblox processes with better error handling."""
        try:
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq RobloxPlayerBeta.exe'], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                process_lines = [line for line in lines if 'RobloxPlayerBeta.exe' in line]
                return len(process_lines)
            return 0
        except Exception as e:
            self._log_status(f"Failed to count Roblox processes: {str(e)}")
            return 0

    def _wait_for_process_limit(self) -> None:
        """Wait if too many Roblox processes are running."""
        while True:
            current_count = self._count_roblox_processes()
            if current_count < self.max_roblox_processes:
                break
            self._log_status(f"⚠ Too many Roblox processes ({current_count}), waiting 5 seconds...")
            time.sleep(5)

    def _detect_default_browser(self):
        """Detect the default browser for automation."""
        browsers_to_check = ['chrome', 'edge', 'firefox']
        for browser in browsers_to_check:
            if self._is_browser_available(browser):
                return browser
        return 'firefox'  # Fallback

    def _is_browser_available(self, browser_type):
        """Check if a specific browser is available."""
        try:
            if browser_type == 'chrome':
                ChromeDriverManager().install()
                return True
            elif browser_type == 'edge':
                EdgeChromiumDriverManager().install()
                return True
            elif browser_type == 'firefox':
                GeckoDriverManager().install()
                return True
        except:
            return False
        return False

    def _setup_firefox_driver(self):
        """Set up Firefox webdriver with proper options."""
        try:
            options = FirefoxOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-java")
            options.add_argument("--no-first-run")
            options.add_argument("--disable-default-apps")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            # Roblox protocol handling
            options.set_preference("network.protocol-handler.external.roblox", True)
            options.set_preference("network.protocol-handler.external.roblox-player", True)
            options.set_preference("network.protocol-handler.warn-external.roblox", False)
            options.set_preference("network.protocol-handler.warn-external.roblox-player", False)
            options.set_preference("security.external_protocol_requires_permission", False)
            options.set_preference("dom.disable_open_during_load", False)
            options.set_preference("network.protocol-handler.expose-all", False)
            options.set_preference("network.protocol-handler.expose.roblox", True)
            options.set_preference("network.protocol-handler.expose.roblox-player", True)
            options.set_preference("browser.safebrowsing.enabled", False)
            options.set_preference("browser.safebrowsing.malware.enabled", False)
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)
            options.set_preference("general.useragent.override", 
                                 "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
            options.set_preference("dom.webnotifications.enabled", False)
            options.set_preference("dom.push.enabled", False)
            
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
            driver.set_page_load_timeout(30)
            self.active_drivers.append(driver)
            return driver
        except Exception as e:
            self._log_status(f"Failed to setup Firefox driver: {str(e)}")
            return None

    def _setup_chrome_driver(self):
        """Set up Chrome webdriver with proper options."""
        try:
            options = ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--no-first-run")
            options.add_argument("--disable-default-apps")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(30)
            self.active_drivers.append(driver)
            return driver
        except Exception as e:
            self._log_status(f"Failed to setup Chrome driver: {str(e)}")
            return None

    def _setup_edge_driver(self):
        """Set up Edge webdriver with proper options."""
        try:
            options = EdgeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--no-first-run")
            options.add_argument("--disable-default-apps")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=options)
            driver.set_page_load_timeout(30)
            self.active_drivers.append(driver)
            return driver
        except Exception as e:
            self._log_status(f"Failed to setup Edge driver: {str(e)}")
            return None

    def _setup_browser_driver(self, browser_type=None):
        """Set up browser driver with fallback options."""
        browser_type = browser_type or self.preferred_browser
        
        if browser_type == 'firefox':
            return self._setup_firefox_driver()
        elif browser_type == 'chrome':
            return self._setup_chrome_driver()
        elif browser_type == 'edge':
            return self._setup_edge_driver()
        else:
            # Try fallback browsers
            for fallback in ['firefox', 'chrome', 'edge']:
                if fallback != browser_type:
                    self._log_status(f"Trying fallback browser: {fallback}")
                    if fallback == 'firefox':
                        driver = self._setup_firefox_driver()
                    elif fallback == 'chrome':
                        driver = self._setup_chrome_driver()
                    elif fallback == 'edge':
                        driver = self._setup_edge_driver()
                    
                    if driver:
                        return driver
        
        return None

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
            
            # Verify cookie injection
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

    def _extract_place_id(self, url: str) -> Optional[str]:
        """
        Extract place ID from various Roblox URL formats.
        Args:
            url: The Roblox game/server URL
        Returns:
            Place ID string or special marker for private servers
        """
        try:
            # Handle private server URLs
            if 'roblox.com/share' in url.lower() and 'code=' in url.lower():
                return "PRIVATE_SERVER"  # Special marker for private server URLs
            
            # Extract from regular game URLs
            if 'roblox.com/games/' in url.lower():
                parts = url.split('/games/')
                if len(parts) > 1:
                    place_id = parts[1].split('/')[0].split('?')[0]
                    if place_id.isdigit():
                        return place_id
        except Exception as e:
            self._log_status(f"Error extracting place ID: {e}")
        
        return None

    def _create_isolation_with_retry(self, account_name: str) -> Tuple[bool, Optional[Path]]:
        """Create storage isolation with retry logic for Windows symlink limitations."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Add small random delay to prevent conflicts
                if attempt > 0:
                    delay = 1 + random.uniform(0.5, 2.0)
                    self._log_status(f"Retrying isolation creation for {account_name} (attempt {attempt + 1}) after {delay:.1f}s...")
                    time.sleep(delay)
                
                # Clean up any existing isolation first
                if account_name in self.storage_manager.active_symlinks:
                    self._log_status(f"Cleaning up existing isolation for {account_name}...")
                    self.storage_manager.remove_storage_isolation(account_name)
                    time.sleep(0.5)
                
                success, backup_path = self.storage_manager.create_storage_isolation(account_name)
                if success:
                    self._log_status(f"✓ Isolation created successfully for {account_name}")
                    return True, backup_path
                else:
                    self._log_status(f"✗ Isolation creation failed for {account_name} (attempt {attempt + 1})")
                    
            except Exception as e:
                self._log_status(f"Isolation attempt {attempt + 1} failed for {account_name}: {e}")
        
        self._log_status(f"✗ All isolation attempts failed for {account_name}")
        return False, None

    def _launch_with_process_verification(self, account_name: str, cookie: str, server_link: str) -> bool:
        """Launch account with actual process verification instead of just thread completion."""
        driver = None
        try:
            self._log_status(f"Setting up browser driver for {account_name}...")
            driver = self._setup_browser_driver()
            if not driver:
                raise Exception("Failed to setup browser driver")
            
            # Navigate and inject cookie
            self._log_status("Navigating to Roblox.com...")
            driver.get("https://www.roblox.com")
            time.sleep(2)
            
            driver.delete_all_cookies()
            
            # Clean cookie
            clean_cookie = _clean_roblosecurity_cookie(cookie)
            
            self._log_status("Adding authentication cookie...")
            driver.add_cookie({
                'name': '.ROBLOSECURITY',
                'value': clean_cookie,
                'domain': '.roblox.com',
                'path': '/',
                'secure': True,
                'httpOnly': True
            })
            
            # Verify cookie injection
            cookies = driver.get_cookies()
            cookie_present = any(c['name'] == '.ROBLOSECURITY' for c in cookies)
            self._log_status(f".ROBLOSECURITY present after injection: {cookie_present}")
            
            if not cookie_present:
                raise Exception("Cookie injection failed")
            
            # Load the private server link and trigger protocol
            self._log_status(f"Loading private server link for {account_name}...")
            initial_processes = self._count_roblox_processes()
            self._log_status(f"Roblox processes before launch: {initial_processes}")
            
            driver.get(server_link)
            self._log_status(f"Waiting for Roblox protocol to trigger for {account_name}...")
            
            # Better process detection with incremental checks
            max_wait_time = 25
            check_interval = 2
            new_process_detected = False
            
            for elapsed in range(0, max_wait_time, check_interval):
                time.sleep(check_interval)
                current_processes = self._count_roblox_processes()
                if current_processes > initial_processes:
                    new_process_detected = True
                    self._log_status(f"✓ New Roblox process detected for {account_name} after {elapsed + check_interval}s")
                    break
                elif elapsed >= 15:  # After 15 seconds, try fallback
                    self._log_status(f"⚠ No process detected yet, trying fallback method...")
                    try:
                        import webbrowser
                        webbrowser.open(server_link)
                        time.sleep(3)
                        fallback_check = self._count_roblox_processes()
                        if fallback_check > initial_processes:
                            new_process_detected = True
                            self._log_status(f"✓ Fallback method worked for {account_name}")
                            break
                    except:
                        pass
            
            if not new_process_detected:
                self._log_status(f"⚠ No new Roblox process detected for {account_name}")
                # Final attempt with direct protocol
                try:
                    roblox_protocol = f"roblox-player:1+launchmode:play+gameinfo:{server_link}"
                    subprocess.run(['cmd', '/c', 'start', '', roblox_protocol], shell=True)
                    time.sleep(5)
                    final_check = self._count_roblox_processes()
                    if final_check > initial_processes:
                        new_process_detected = True
                        self._log_status(f"✓ Direct protocol launch worked for {account_name}")
                except:
                    pass
            
            # Additional wait for Roblox to fully initialize
            if new_process_detected:
                self._log_status(f"Waiting for Roblox to initialize for {account_name}...")
                time.sleep(5)
            
            final_processes = self._count_roblox_processes()
            self._log_status(f"Final process count: {final_processes} (started with {initial_processes})")
            
            return new_process_detected
            
        except Exception as e:
            self._log_status(f"Launch verification failed for {account_name}: {str(e)}")
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                    if driver in self.active_drivers:
                        self.active_drivers.remove(driver)
                except:
                    pass

    def launch_account_direct_protocol(self, account_name: str, roblosecurity_cookie: str, server_link: str):
        """Launch account using direct protocol method (for improved launcher compatibility)."""
        def launch_thread():
            try:
                self._log_status(f"Starting direct protocol launch for {account_name}...")
                
                # Extract place ID or handle private server
                place_id = self._extract_place_id(server_link)
                if not place_id:
                    self._log_status(f"Could not extract place ID from URL: {server_link}")
                    return False
                
                if place_id == "PRIVATE_SERVER":
                    launch_url = server_link
                    self._log_status(f"Launching private server URL directly for {account_name}: {server_link}")
                else:
                    launch_url = f"roblox://placeID={place_id}"
                    self._log_status(f"Launching place ID {place_id} for {account_name} via protocol")
                
                # Launch via protocol
                process = subprocess.Popen(
                    ['cmd', '/c', 'start', '', launch_url],
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                self.active_launches[account_name] = {
                    'process': process,
                    'server_url': server_link,
                    'launched_at': time.time(),
                    'method': 'direct_protocol'
                }
                
                self._log_status(f"Direct protocol launch initiated for {account_name}")
                return True
                
            except Exception as e:
                self._log_status(f"Direct protocol launch failed for {account_name}: {e}")
                return False
        
        thread = threading.Thread(target=launch_thread, daemon=True)
        thread.start()
        self.launch_threads.append(thread)
        return thread

    def launch_account(self, account_name: str, roblosecurity_cookie: str, server_link: str):
        """Launch account using browser automation method."""
        def launch_thread():
            try:
                self._log_status(f"Starting browser automation launch for {account_name}...")
                driver = self._setup_browser_driver()
                if not driver:
                    raise Exception("Failed to setup browser driver")
                
                # Inject cookie and navigate
                if not self._inject_cookie(driver, roblosecurity_cookie):
                    raise Exception("Failed to inject authentication cookie")
                
                self._log_status(f"Navigating to game page for {account_name}...")
                driver.get(server_link)
                time.sleep(3)
                
                # Try to click play button if it exists
                try:
                    play_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-primary-md') or contains(text(), 'Play')]"))
                    )
                    play_button.click()
                    self._log_status(f"Play button clicked for {account_name}")
                except TimeoutException:
                    self._log_status(f"No play button found for {account_name}, protocol should auto-trigger")
                
                time.sleep(5)  # Wait for Roblox to launch
                
                self.active_launches[account_name] = {
                    'process': None,
                    'server_url': server_link,
                    'launched_at': time.time(),
                    'method': 'browser_automation'
                }
                
                self._log_status(f"Browser automation launch completed for {account_name}")
                return True
                
            except Exception as e:
                self._log_status(f"Browser automation launch failed for {account_name}: {e}")
                return False
            finally:
                if driver:
                    try:
                        driver.quit()
                        if driver in self.active_drivers:
                            self.active_drivers.remove(driver)
                    except:
                        pass
        
        thread = threading.Thread(target=launch_thread, daemon=True)
        thread.start()
        self.launch_threads.append(thread)
        return thread

    def launch_account_improved(self, account_name: str, cookie: str, server_link: str) -> bool:
        """Launch account with improved process verification and isolation."""
        try:
            # Wait for process limit
            self._wait_for_process_limit()
            
            # Create isolation with retry
            isolation_success, backup_path = self._create_isolation_with_retry(account_name)
            if not isolation_success:
                self._log_status(f"Failed to create isolation for {account_name}")
                return False
            
            # Launch with process verification
            success = self._launch_with_process_verification(account_name, cookie, server_link)
            
            if success:
                self._log_status(f"✓ {account_name} launched successfully with process verification")
                
                # Wait for Roblox to initialize and cache session
                self._log_status(f"Waiting for Roblox to initialize for {account_name}...")
                time.sleep(10)
                
                # Remove isolation after launch
                self._log_status(f"Removing temporary isolation for {account_name}...")
                self.storage_manager.remove_storage_isolation(account_name, restore_backup=True, backup_path=backup_path)
                
                return True
            else:
                self._log_status(f"✗ {account_name} launch failed")
                # Clean up isolation on failure
                if self.storage_manager.is_isolation_active(account_name):
                    self.storage_manager.remove_storage_isolation(account_name, restore_backup=True, backup_path=backup_path)
                return False
                
        except Exception as e:
            self._log_status(f"Improved launch failed for {account_name}: {str(e)}")
            return False

    def launch_multiple_accounts_improved(self, accounts_data: list, server_link: str) -> None:
        """Launch multiple accounts using the improved method with better rate limiting."""
        def batch_launch():
            self._log_status(f"Starting improved batch launch for {len(accounts_data)} accounts...")
            success_count = 0
            
            for i, (account_name, cookie) in enumerate(accounts_data):
                self._log_status(f"Launching account {i+1}/{len(accounts_data)}: {account_name}")
                
                success = self.launch_account_improved(account_name, cookie, server_link)
                if success:
                    success_count += 1
                    self._log_status(f"✓ {account_name} launched successfully")
                else:
                    self._log_status(f"✗ {account_name} launch failed")
                
                # Delay between launches
                if i < len(accounts_data) - 1:
                    delay = 3 + random.uniform(1, 3)  # 3-6 second random delay
                    self._log_status(f"Waiting {delay:.1f} seconds before next launch...")
                    time.sleep(delay)
            
            self._log_status(f"Batch launch completed: {success_count}/{len(accounts_data)} successful")
        
        thread = threading.Thread(target=batch_launch, daemon=True)
        thread.start()
        self.launch_threads.append(thread)

    def launch_account_with_temporary_isolation(self, account_name: str, roblosecurity_cookie: str, server_url: str) -> bool:
        """
        Launch account with temporary symlink isolation that gets removed after authentication caching.
        """
        backup_path = None
        try:
            self._log_status(f"Starting temporary isolation launch for {account_name}...")
            self._log_status(f"Creating temporary LocalStorage isolation for {account_name}...")
            isolation_success, backup_path = self.storage_manager.create_storage_isolation(account_name)
            if not isolation_success:
                raise Exception("Failed to create LocalStorage isolation")
            
            self._log_status(f"Launching Roblox with browser automation for {account_name}...")
            self._log_status(f"Detected browser: {self.preferred_browser}")
            launch_thread = self.launch_account(account_name, roblosecurity_cookie, server_url)
            if not launch_thread:
                raise Exception("Failed to start browser automation (no supported browser found)")
            
            # Wait for the launch thread to complete and check if it was successful
            launch_thread.join(timeout=60)  # Wait up to 60 seconds for launch to complete
            
            # Check if any drivers were actually created (indicates success)
            if not self.active_drivers:
                raise Exception("Browser automation failed - no active browser sessions created")
                
            self._log_status(f"Launch thread completed for {account_name}")
            self._log_status(f"Waiting for Roblox to initialize for {account_name}...")
            time.sleep(10)  # Give Roblox time to start and cache the session
            
            self._log_status(f"Removing temporary isolation for {account_name}...")
            self.storage_manager.remove_storage_isolation(account_name, restore_backup=True, backup_path=backup_path)
            
            self._log_status(f"✓ {account_name} launched successfully with temporary isolation")
            return True
            
        except Exception as e:
            error_msg = f"{account_name} temporary isolation launch failed: {str(e)}"
            self._log_status(error_msg)
            if self.storage_manager.is_isolation_active(account_name):
                self.storage_manager.remove_storage_isolation(
                    account_name, 
                    restore_backup=True, 
                    backup_path=backup_path
                )
            return False

    def stop_all_instances(self) -> int:
        """
        Stop all active browser instances and cleanup sessions.
        Returns:
            Number of instances stopped
        """
        stopped_count = 0
        
        # Stop all active browser sessions
        for driver in self.active_sessions.copy():
            try:
                driver.quit()
                stopped_count += 1
            except:
                pass
        self.active_sessions.clear()
        
        # Stop all active drivers
        for driver in self.active_drivers.copy():
            try:
                driver.quit()
                stopped_count += 1
            except:
                pass
        self.active_drivers.clear()
        
        # Clean up launch threads
        for thread in self.launch_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        self.launch_threads.clear()
        
        # Clean up active launches
        self.active_launches.clear()
        
        self._log_status(f"Stopped {stopped_count} instances")
        return stopped_count

    def get_isolation_status(self) -> dict:
        """
        Get status of all isolations and launches.
        Returns:
            Dictionary with comprehensive status information
        """
        symlink_status = self.storage_manager.get_isolation_status()
        
        # Add launch information
        launches = {}
        for account_name, info in self.active_launches.items():
            runtime = time.time() - info.get('launched_at', 0)
            launches[account_name] = {
                'server_url': info.get('server_url', ''),
                'running_time': int(runtime),
                'launch_method': info.get('method', 'unknown'),
                'fishtrap_used': 'fishtrap_exe' in info
            }
        
        return {
            **symlink_status,
            'active_launches': len(self.active_launches),
            'active_browser_sessions': len(self.active_sessions),
            'active_launch_threads': len([t for t in self.launch_threads if t.is_alive()]),
            'launches': launches
        }

    def cleanup_all_sessions(self) -> None:
        """
        Clean up all active sessions and isolations.
        """
        # Stop all instances
        self.stop_all_instances()
        
        # Clean up all isolations
        self.storage_manager.cleanup_all_isolations()
        
        self._log_status("All sessions and isolations cleaned up")

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
        results['backups_cleaned'] = self.storage_manager.cleanup_old_backups(max_age_hours)
        self._log_status(f"Cleanup completed: {results['backups_cleaned']} backups removed")
        return results

    def get_status(self):
        """Get current launcher status."""
        active_count = len([d for d in self.active_drivers if d])
        thread_count = len([t for t in self.launch_threads if t.is_alive()])
        return f"Active browsers: {active_count}, Running threads: {thread_count}"


# Legacy compatibility aliases
IsolatedRobloxLauncher = RobloxLauncher
ImprovedRobloxLauncher = RobloxLauncher
