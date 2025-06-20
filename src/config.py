"""
Configuration settings for the Enhanced Roblox Multi-Account Manager.
Contains settings for security, automation, instance isolation, and UI.
"""
import os
BROWSER_SETTINGS = {
    'headless': True,
    'window_size': '1920,1080',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
    'page_load_timeout': 30,
    'element_wait_timeout': 15,
    'cookie_injection_delay': 2,
    'protocol_trigger_delay': 2
}
SECURITY_SETTINGS = {
    'pbkdf2_iterations': 100000,
    'salt_length': 16,
    'min_password_length': 6,
    'key_length': 32,
    'cookie_min_length': 100
}
INSTANCE_SETTINGS = {
    'instances_dir': 'roblox_instances',
    'cleanup_age_hours': 24,
    'required_dirs': [
        'LocalStorage',
        'logs', 
        'cache',
        'content',
        'versions'
    ]
}
LAUNCH_SETTINGS = {
    'default_delay_between_launches': 5,
    'max_delay_between_launches': 30,
    'max_concurrent_launches': 10,
    'roblox_launch_wait_time': 8,
    'cookie_injection_wait': 3,
    'page_navigation_wait': 3
}
UI_SETTINGS = {
    'window_title': 'Roblox Multi-Account Manager - Enhanced',
    'default_geometry': '650x500',
    'min_window_size': (500, 400),
    'theme': 'clam',
    'status_height': 4,
    'treeview_height': 6
}
FILE_PATHS = {
    'accounts_file': os.path.join(os.path.dirname(os.path.dirname(__file__)), '.data', 'accounts.json'),
    'salt_file': os.path.join(os.path.dirname(os.path.dirname(__file__)), '.data', 'security.salt')
}
PLAY_BUTTON_SELECTORS = [
    "button[data-testid='play-button']",
    "button.btn-full-width.btn-control-lg.btn-primary-lg",
    "button.play-button",
    "a.btn-full-width.btn-control-lg.btn-primary-lg",
    "[data-testid='game-detail-play-button']",
    ".game-launch-button",
    "button[class*='play']",
    "a[class*='play']"
]
ROBLOX_URL_PATTERNS = [
    'roblox.com/games/',
    'roblox.com/share',
    'placeId=',
    'placeid='
]
FIREFOX_PREFERENCES = {
    "dom.webdriver.enabled": False,
    "useAutomationExtension": False,
    "network.protocol-handler.external.roblox": True,
    "network.protocol-handler.external.roblox-player": True,
    "network.protocol-handler.warn-external.roblox": False,
    "network.protocol-handler.warn-external.roblox-player": False,
    "dom.webnotifications.enabled": False,
    "dom.push.enabled": False
}
FIREFOX_ARGUMENTS = [
    "--headless",
    "--no-sandbox", 
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-images"
]
MESSAGES = {
    'success': {
        'account_added': 'Account added successfully',
        'launch_started': 'Launch sequence initiated', 
        'instances_stopped': 'All instances stopped',
        'cleanup_completed': 'Cleanup completed'
    },
    'error': {
        'invalid_password': 'Invalid master password',
        'no_selection': 'Please select accounts to launch',        'invalid_url': 'Invalid server URL format',
        'launch_failed': 'Launch failed',
        'roblox_not_found': 'Roblox not found'
    }
}
