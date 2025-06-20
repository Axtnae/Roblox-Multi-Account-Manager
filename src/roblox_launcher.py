import os
import time
import threading
import subprocess
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.firefox import GeckoDriverManager
class RobloxLauncher:
    """Firefox-based Roblox launcher with cookie authentication."""
    def __init__(self, status_callback=None):
        """Initialize the launcher with optional status callback."""
        self.status_callback = status_callback
        self.active_drivers = []
        self.launch_threads = []
    def _update_status(self, message):
        """Update status via callback if available."""
        if self.status_callback:
            self.status_callback(message)
        print(f"[RobloxLauncher] {message}")
    def _count_roblox_processes(self):
        """Count running Roblox processes."""
        try:
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq RobloxPlayerBeta.exe'], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                process_lines = [line for line in lines if 'RobloxPlayerBeta.exe' in line]
                return len(process_lines)
            return 0
        except Exception as e:
            self._update_status(f"Failed to count Roblox processes: {str(e)}")
            return 0
    def _setup_firefox_driver(self):
        """Set up Firefox webdriver with proper options."""
        try:
            options = Options()
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
            service = Service(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
            driver.set_page_load_timeout(30)
            self.active_drivers.append(driver)
            return driver
        except Exception as e:
            self._update_status(f"Failed to setup Firefox driver: {str(e)}")
            return None
    def _clean_roblosecurity_cookie(self, cookie):
        """Remove Roblox WARNING prefix if present."""
        warning_prefix = "_|WARNING"
        if cookie.startswith(warning_prefix):
            parts = cookie.split("|_")
            if len(parts) >= 2:
                return parts[-1]
        return cookie
    def _inject_cookie(self, driver, roblosecurity_cookie):
        """Inject .ROBLOSECURITY cookie into the browser."""
        try:
            self._update_status("Navigating to Roblox.com...")
            driver.get("https://www.roblox.com")
            time.sleep(2)
            driver.delete_all_cookies()
            clean_cookie = self._clean_roblosecurity_cookie(roblosecurity_cookie)
            self._update_status("Adding authentication cookie...")
            cookie_data = {
                'name': '.ROBLOSECURITY',
                'value': clean_cookie,
                'domain': '.roblox.com',
                'path': '/',
                'secure': True,
                'httpOnly': True
            }
            driver.add_cookie(cookie_data)
            self._update_status("Cookie injected successfully")
            cookies = driver.get_cookies()
            roblosecurity_present = any(c['name'] == '.ROBLOSECURITY' for c in cookies)
            self._update_status(f".ROBLOSECURITY present after injection: {roblosecurity_present}")
            return True
        except Exception as e:
            self._update_status(f"Cookie injection failed: {str(e)}")
            return False
    def _click_play_button(self, driver, server_link):
        """Navigate to server link and click play button."""
        try:
            self._update_status("Navigating to server link...")
            driver.get(server_link)
            time.sleep(3)
            play_selectors = [
                "button[data-testid='play-button']",
                "button.btn-primary-md",
                "button.btn-full-width",
                "a.btn-primary-md", 
                ".game-play-button",
                "#game-play-button",
                "button[class*='play']",
                "a[class*='play']"
            ]
            self._update_status("Looking for play button...")
            for selector in play_selectors:
                try:
                    play_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    self._update_status(f"Found play button with selector: {selector}")
                    driver.execute_script("arguments[0].click();", play_button)
                    self._update_status("Play button clicked - Roblox should be launching...")
                    time.sleep(3)
                    return True
                except TimeoutException:
                    continue
                except Exception as e:
                    self._update_status(f"Error with selector {selector}: {str(e)}")
                    continue
            self._update_status("No play button found with any selector")
            return False
        except Exception as e:
            self._update_status(f"Play button click failed: {str(e)}")
            return False
    def launch_account(self, account_name, roblosecurity_cookie, server_link):
        """Launch a single account in a separate thread."""
        def launch_thread():
            driver = None
            try:
                self._update_status(f"Starting launch for {account_name}...")
                driver = self._setup_firefox_driver()
                if not driver:
                    self._update_status(f"Failed to setup driver for {account_name}")
                    return
                if not self._inject_cookie(driver, roblosecurity_cookie):
                    self._update_status(f"Cookie injection failed for {account_name}")
                    return
                if self._click_play_button(driver, server_link):
                    self._update_status(f"Launch completed for {account_name}")
                else:
                    self._update_status(f"Play button click failed for {account_name}")
            except Exception as e:
                self._update_status(f"Launch failed for {account_name}: {str(e)}")
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
    def launch_account_direct_protocol(self, account_name, roblosecurity_cookie, server_link):
        """Launch account using direct protocol (no Play button click) - for private server links."""
        def launch_thread():
            driver = None
            try:
                self._update_status(f"Starting direct protocol launch for {account_name}...")
                driver = self._setup_firefox_driver()
                if not driver:
                    self._update_status(f"Failed to setup driver for {account_name}")
                    return
                if not self._inject_cookie(driver, roblosecurity_cookie):
                    self._update_status(f"Cookie injection failed for {account_name}")
                    return
                self._update_status(f"Loading private server link for {account_name}...")
                initial_processes = self._count_roblox_processes()
                self._update_status(f"Roblox processes before launch: {initial_processes}")
                driver.get(server_link)
                self._update_status(f"Waiting for Roblox protocol to trigger for {account_name}...")
                time.sleep(8)  # Initial wait for protocol handler
                current_processes = self._count_roblox_processes()
                if current_processes > initial_processes:
                    self._update_status(f"✓ New Roblox process detected for {account_name} (total: {current_processes})")
                else:
                    self._update_status(f"⚠ No new Roblox process detected for {account_name}")
                self._update_status(f"Allowing additional time for Roblox to start for {account_name}...")
                time.sleep(7)  # Additional buffer time
                final_processes = self._count_roblox_processes()
                self._update_status(f"Final Roblox processes: {final_processes}")
                if driver:
                    try:
                        for handle in driver.window_handles:
                            driver.switch_to.window(handle)
                            driver.close()
                    except:
                        pass
                self._update_status(f"Direct protocol launch completed for {account_name}")
            except Exception as e:
                self._update_status(f"Direct protocol launch failed for {account_name}: {str(e)}")
            finally:
                if driver:
                    try:
                        driver.quit()
                        if driver in self.active_drivers:
                            self.active_drivers.remove(driver)
                    except:
                        pass                # Kill any remaining Firefox processes that might be hanging
                try:
                    self._update_status(f"Cleaning up browser processes for {account_name}...")
                    subprocess.run(['taskkill', '/F', '/IM', 'firefox.exe'], 
                                 capture_output=True, shell=True)
                    subprocess.run(['taskkill', '/F', '/IM', 'geckodriver.exe'], 
                                 capture_output=True, shell=True)
                    self._update_status(f"Browser cleanup completed for {account_name}")
                except:
                    pass
        thread = threading.Thread(target=launch_thread, daemon=True)
        thread.start()
        self.launch_threads.append(thread)
        self._update_status(f"Direct protocol launch thread started for {account_name}")
        return thread
    def stop_all_instances(self):
        """Stop all active browser instances."""
        try:
            self._update_status("Stopping all browser instances...")
            for driver in self.active_drivers.copy():
                try:
                    driver.quit()
                except:
                    pass
            self.active_drivers.clear()
            for thread in self.launch_threads:
                if thread.is_alive():
                    thread.join(timeout=5)
            self.launch_threads.clear()
            self._update_status("All browser instances stopped")
        except Exception as e:
            self._update_status(f"Error stopping instances: {str(e)}")
    def get_status(self):
        """Get current launcher status."""
        active_count = len([d for d in self.active_drivers if d])
        thread_count = len([t for t in self.launch_threads if t.is_alive()])
        return f"Active browsers: {active_count}, Running threads: {thread_count}"