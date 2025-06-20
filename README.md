# Roblox Multi-Account Manager - Enhanced Edition

A secure Python application for managing and launching multiple Roblox accounts with full instance isolation. Built with Tkinter for the GUI and Selenium for browser automation.

## Features

- Isolated data directories for each account
- No session conflicts between accounts
- Encrypted storage of account cookies and sensitive data
- Modern, minimal interface
- Multi-account launching with configurable delays
- Real-time status and instance monitoring

## Requirements

- Windows 10 or 11
- Python 3.8 or higher
- Firefox browser (for Selenium automation)
- Roblox installed on your system

## Installation

1. Download or clone this repository to your computer.
2. Open a terminal or command prompt in the project directory.
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the setup script (Windows):
   ```
   setup.bat
   ```
5. Start the application:
   ```
   start.bat
   ```

## Usage

1. Obtain your .ROBLOSECURITY cookie:
   - Log into Roblox in Firefox or Chrome.
   - Open Developer Tools (F12).
   - Go to the Application or Storage tab.
   - Find Cookies for roblox.com and copy the .ROBLOSECURITY value.
2. Add your account in the application and paste the cookie when prompted.
3. Select one or more accounts to launch.
4. Enter a Roblox game or server link if desired.
5. Set a launch delay if needed (default is 5 seconds).
6. Click Launch to start Roblox clients in isolated instances.

## Security Notes

- Never share your .ROBLOSECURITY cookies. Treat them like passwords.
- Use a strong, unique master password for encryption.
- Keep your dependencies up to date for security.

## Support

For issues or questions, see the troubleshooting section in the full documentation or open an issue on the repository.
