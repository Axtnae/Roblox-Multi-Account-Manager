import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import sys
import os
import json
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from security_manager import SecurityManager
from isolated_launcher import IsolatedRobloxLauncher
class AccountManager:
    def __init__(self):
        self.root = tk.Tk()
        self.security_manager = SecurityManager()
        self.roblox_launcher = IsolatedRobloxLauncher(callback=self.update_status)
        self.accounts_data = {}
        self.saved_links = {}  # Store loaded links
        self.master_password = None
        self._last_save_time = 0
        self._save_delay = 1.0  # Delay saves to batch them
        self.setup_ui()
        self.authenticate()
    def setup_ui(self):
        """Setup the main UI interface."""
        self.root.title("Roblox Multi-Account Manager - Symlink Isolation")
        self.root.geometry("800x700")  # Increased size to accommodate all elements
        self.root.minsize(750, 650)    # Set minimum size to prevent elements from being cut off
        self.root.resizable(True, True)
        self.root.configure(bg='#f8f9fa')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Card.TFrame', background='#ffffff', relief='flat', borderwidth=1)
        style.configure('Header.TLabel', font=('Segoe UI', 11, 'bold'), background='#ffffff', foreground='#2c3e50')
        style.configure('Body.TLabel', font=('Segoe UI', 9), background='#ffffff', foreground='#34495e')
        style.configure('Modern.TButton', font=('Segoe UI', 9), padding=(8, 4), width=8)  # Fixed width for consistency
        style.configure('Primary.TButton', font=('Segoe UI', 9, 'bold'), padding=(12, 6), width=12)
        style.configure('Small.TButton', font=('Segoe UI', 8), padding=(6, 3), width=10)  # For smaller buttons
        style.map('Primary.TButton', background=[('active', '#3498db')])
        main_frame = ttk.Frame(self.root, style='Card.TFrame', padding="12")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        header_frame = ttk.Frame(main_frame, style='Card.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 12))
        title_label = ttk.Label(header_frame, text="Roblox Multi-Account Manager", 
                               font=('Segoe UI', 14, 'bold'), background='#ffffff', foreground='#2c3e50')
        title_label.pack(side=tk.LEFT)
        subtitle_label = ttk.Label(header_frame, text="with LocalStorage Isolation", 
                                  font=('Segoe UI', 10), background='#ffffff', foreground='#6c757d')
        subtitle_label.pack(side=tk.LEFT, padx=(8, 0))
        accounts_section = ttk.Frame(main_frame, style='Card.TFrame')
        accounts_section.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        accounts_header = ttk.Frame(accounts_section, style='Card.TFrame')
        accounts_header.pack(fill=tk.X, padx=8, pady=(8, 6))
        ttk.Label(accounts_header, text="Accounts", style='Header.TLabel').pack(side=tk.LEFT)
        controls_frame = ttk.Frame(accounts_header, style='Card.TFrame')
        controls_frame.pack(side=tk.RIGHT)
        ttk.Button(controls_frame, text="Add", command=self.add_account, 
                  style='Small.TButton').pack(side=tk.RIGHT, padx=(2, 0))
        ttk.Button(controls_frame, text="Remove", command=self.remove_selected_accounts,
                  style='Small.TButton').pack(side=tk.RIGHT, padx=(2, 0))        # Modern accounts list with better sizing
        list_frame = ttk.Frame(accounts_section, style='Card.TFrame')
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.accounts_tree = ttk.Treeview(list_frame, columns=('status',), show='tree headings', 
                                         height=8, selectmode='extended')  # Increased height
        self.accounts_tree.heading('#0', text='Account Name')
        self.accounts_tree.heading('status', text='Status')
        self.accounts_tree.column('#0', width=250, minwidth=200)  # Increased width
        self.accounts_tree.column('status', width=100, minwidth=80)
        self.accounts_tree.bind('<<TreeviewSelect>>', self.toggle_account_selection)
        accounts_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.accounts_tree.yview)
        self.accounts_tree.configure(yscrollcommand=accounts_scrollbar.set)
        self.accounts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        accounts_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        select_frame = ttk.Frame(accounts_section, style='Card.TFrame')
        select_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(select_frame, text="Select All", command=self.select_all_accounts,
                  style='Small.TButton').pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(select_frame, text="Clear", command=self.deselect_all_accounts,
                  style='Small.TButton').pack(side=tk.LEFT)        # Enhanced Server section with better layout
        server_section = ttk.Frame(main_frame, style='Card.TFrame')
        server_section.pack(fill=tk.X, pady=(0, 8))
        server_inner = ttk.Frame(server_section, style='Card.TFrame')
        server_inner.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(server_inner, text="Server Configuration", style='Header.TLabel').pack(anchor=tk.W, pady=(0, 6))
        link_row1 = ttk.Frame(server_inner, style='Card.TFrame')
        link_row1.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(link_row1, text="Saved Links:", style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 6))
        self.saved_links_var = tk.StringVar(value="Select saved link...")
        self.saved_links_combo = ttk.Combobox(link_row1, textvariable=self.saved_links_var, 
                                             font=('Segoe UI', 9), state='readonly', width=25)
        self.saved_links_combo.pack(side=tk.LEFT, padx=(0, 6))
        self.saved_links_combo.bind('<<ComboboxSelected>>', self.on_saved_link_selected)
        button_frame1 = ttk.Frame(link_row1, style='Card.TFrame')
        button_frame1.pack(side=tk.LEFT)
        ttk.Button(button_frame1, text="Save", command=self.save_current_link,
                  style='Small.TButton').pack(side=tk.LEFT, padx=(2, 2))
        ttk.Button(button_frame1, text="Delete", command=self.delete_saved_link,
                  style='Small.TButton').pack(side=tk.LEFT, padx=(2, 0))
        link_row2 = ttk.Frame(server_inner, style='Card.TFrame')
        link_row2.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(link_row2, text="Server Link:", style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 6))
        self.server_entry = ttk.Entry(link_row2, font=('Segoe UI', 9))
        self.server_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.server_entry.insert(0, "Enter game/private server link...")
        method_row = ttk.Frame(server_inner, style='Card.TFrame')
        method_row.pack(fill=tk.X, pady=(0, 0))
        ttk.Label(method_row, text="Launch Method:", style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 6))
        self.launch_method_var = tk.StringVar(value="Direct Join")
        method_buttons = ttk.Frame(method_row, style='Card.TFrame')
        method_buttons.pack(side=tk.LEFT)
        ttk.Radiobutton(method_buttons, text="Direct Join (PS links)", variable=self.launch_method_var, 
                       value="Direct Join", style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(method_buttons, text="Browser + Play Button", variable=self.launch_method_var, 
                       value="Browser", style='Body.TLabel').pack(side=tk.LEFT)
        self.load_saved_links()
        launch_section = ttk.Frame(main_frame, style='Card.TFrame')
        launch_section.pack(fill=tk.X, pady=(0, 8))
        launch_inner = ttk.Frame(launch_section, style='Card.TFrame')
        launch_inner.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(launch_inner, text="Launch Controls", style='Header.TLabel').pack(anchor=tk.W, pady=(0, 6))
        primary_row = ttk.Frame(launch_inner, style='Card.TFrame')
        primary_row.pack(fill=tk.X, pady=(0, 6))
        self.launch_button = ttk.Button(primary_row, text="Launch Selected", 
                                       command=self.launch_selected_accounts, style='Primary.TButton')
        self.launch_button.pack(side=tk.LEFT, padx=(0, 8))
        delay_frame = ttk.Frame(primary_row, style='Card.TFrame')
        delay_frame.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(delay_frame, text="Delay:", style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 2))
        self.delay_var = tk.StringVar(value="3")
        delay_spinbox = ttk.Spinbox(delay_frame, from_=0, to=30, textvariable=self.delay_var, 
                                   width=5, font=('Segoe UI', 9))
        delay_spinbox.pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(delay_frame, text="sec", style='Body.TLabel').pack(side=tk.LEFT)
        secondary_row = ttk.Frame(launch_inner, style='Card.TFrame')
        secondary_row.pack(fill=tk.X)
        ttk.Button(secondary_row, text="Stop All", command=self.stop_all_sessions,
                  style='Small.TButton').pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(secondary_row, text="Cleanup", command=self.cleanup_old_instances,
                  style='Small.TButton').pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(secondary_row, text="Status", command=self.show_instance_status,
                  style='Small.TButton').pack(side=tk.LEFT)
        status_section = ttk.Frame(main_frame, style='Card.TFrame')
        status_section.pack(fill=tk.BOTH, expand=False, pady=(0, 0))
        status_header = ttk.Frame(status_section, style='Card.TFrame')
        status_header.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Label(status_header, text="Status", style='Header.TLabel').pack(side=tk.LEFT)
        status_frame = ttk.Frame(status_section, style='Card.TFrame')
        status_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.status_text = tk.Text(status_frame, height=6, wrap=tk.WORD, state=tk.DISABLED,
                                  font=('Segoe UI', 8), bg='#f8f9fa', fg='#6c757d', relief='flat',
                                  borderwidth=1, highlightthickness=0)
        status_scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scrollbar.set)
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.accounts_tree.bind('<Double-1>', self.toggle_account_selection)
        self.server_entry.bind('<FocusIn>', self.clear_placeholder)
        self.update_status("Ready to manage accounts")
    def clear_placeholder(self, event):
        """Clear placeholder text when entry is focused."""
        if self.server_entry.get() == "Enter game/private server link...":
            self.server_entry.delete(0, tk.END)
    def authenticate(self):
        """Handle master password authentication."""
        if self.security_manager.data_exists():
            while True:
                password = simpledialog.askstring("Authentication", 
                                                "Enter master password:", show='*')
                if password is None:  # User cancelled
                    self.root.destroy()
                    return
                self.accounts_data = self.security_manager.decrypt_data(password)
                if self.accounts_data is not None:
                    self.master_password = password
                    self.refresh_accounts_list()
                    self.update_status("Authentication successful. Data loaded.")
                    break
                else:
                    messagebox.showerror("Error", "Invalid password. Please try again.")
        else:
            while True:
                password = simpledialog.askstring("Setup", 
                                                "Create a master password for encryption:", show='*')
                if password is None:  # User cancelled
                    self.root.destroy()
                    return
                if len(password) < 6:
                    messagebox.showwarning("Warning", "Password must be at least 6 characters long.")
                    continue
                confirm = simpledialog.askstring("Confirm", 
                                               "Confirm master password:", show='*')
                if confirm != password:
                    messagebox.showerror("Error", "Passwords do not match.")
                    continue
                self.master_password = password
                self.accounts_data = {}
                self.save_data()
                self.update_status("Master password set. You can now add accounts.")
                break
    def add_account(self):
        """Add a new account with .ROBLOSECURITY cookie."""
        dialog = AccountDialog(self.root)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            account_name, cookie = dialog.result
            if account_name in self.accounts_data:
                if not messagebox.askyesno("Duplicate Account", 
                                         f"Account '{account_name}' already exists. Overwrite?"):
                    return
            self.accounts_data[account_name] = cookie
            self.save_data_debounced()
            self.refresh_accounts_list()
            self.update_status(f"Account '{account_name}' added successfully.")
    def remove_selected_accounts(self):
        """Remove selected accounts from the list."""
        selected_items = []
        for item in self.accounts_tree.get_children():
            tags = self.accounts_tree.item(item, 'tags')
            if 'selected' in tags:
                selected_items.append(item)
        if not selected_items:
            messagebox.showinfo("Info", "No accounts selected for removal.")
            return
        account_names = [self.accounts_tree.item(item, 'text') for item in selected_items]
        if messagebox.askyesno("Confirm Removal", 
                              f"Remove {len(account_names)} selected account(s)?"):
            for name in account_names:
                if name in self.accounts_data:
                    del self.accounts_data[name]
            self.save_data_debounced()
            self.refresh_accounts_list()
            self.update_status(f"Removed {len(account_names)} account(s).")
    def select_all_accounts(self):
        """Select all accounts in the list."""
        all_items = self.accounts_tree.get_children()
        self.accounts_tree.selection_set(all_items)
        for item in all_items:
            self.accounts_tree.set(item, 'status', '✓')
    def deselect_all_accounts(self):
        """Deselect all accounts in the list."""
        self.accounts_tree.selection_remove(self.accounts_tree.get_children())
        for item in self.accounts_tree.get_children():
            self.accounts_tree.set(item, 'status', '')
    def toggle_account_selection(self, event):
        """Handle account selection changes."""
        selected_items = self.accounts_tree.selection()
        for item in self.accounts_tree.get_children():
            if item in selected_items:
                self.accounts_tree.set(item, 'status', '✓')
            else:
                self.accounts_tree.set(item, 'status', '')
    def refresh_accounts_list(self):
        """Refresh the accounts display list."""        # Clear existing items
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)
        for account_name in sorted(self.accounts_data.keys()):
            item = self.accounts_tree.insert('', 'end', text=account_name, values=('',))
    def launch_selected_accounts(self):
        """Launch Roblox for all selected accounts with instance isolation and correct method."""
        selected_items = self.accounts_tree.selection()
        selected_accounts = []
        for item in selected_items:
            account_name = self.accounts_tree.item(item, 'text')
            if account_name in self.accounts_data:
                cookie = self.accounts_data[account_name]
                selected_accounts.append((account_name, cookie))
        if not selected_accounts:
            messagebox.showinfo("No Selection", "Please select accounts to launch.")
            return
        server_link = self.server_entry.get().strip()
        if not server_link or server_link == "Enter game/private server link...":
            messagebox.showwarning("Missing Link", "Please enter a valid server link.")
            return
        if not any(x in server_link.lower() for x in ['roblox.com/games/', 'roblox.com/share']):
            if not messagebox.askyesno("Confirm", 
                                     "Server link doesn't appear to be a valid Roblox game URL. Continue anyway?"):                return
        try:
            delay = max(8, int(self.delay_var.get()))  # Minimum 8 seconds for Direct Join stability
        except ValueError:
            delay = 12  # Default to 12 seconds for better protocol handler stability
        self.launch_button.config(state='disabled')
        self.update_status(f"Starting LocalStorage isolated launch sequence for {len(selected_accounts)} account(s)...")
        is_private_server = 'roblox.com/share' in server_link.lower() and 'code=' in server_link.lower()
        launch_method = "Direct Join" if is_private_server else "Browser + Play Button"
        self.update_status(f"Auto-selected launch method: {launch_method}")
        if launch_method == "Direct Join":
            self.update_status("Note: Direct Join uses longer delays between accounts to ensure proper protocol handling")
        if not hasattr(self, 'active_account_launches'):
            self.active_account_launches = set()
        launching_accounts = [name for name, _ in selected_accounts if name in self.active_account_launches]
        if launching_accounts:
            self.update_status(f"Skipping {len(launching_accounts)} accounts already launching: {', '.join(launching_accounts)}")
            selected_accounts = [(name, cookie) for name, cookie in selected_accounts if name not in self.active_account_launches]
        if not selected_accounts:
            self.launch_button.config(state='normal')
            return
        def launch_thread():
            try:
                for account_name, _ in selected_accounts:
                    self.active_account_launches.add(account_name)
                if launch_method == "Direct Join":
                    self.update_status(f"Using Direct Join method for {len(selected_accounts)} PS links...")
                    for i, (account_name, cookie) in enumerate(selected_accounts):
                        self.update_status(f"Direct joining {account_name} ({i+1}/{len(selected_accounts)})...")
                        isolation_success, backup_path = self.roblox_launcher.symlink_manager.create_storage_isolation(account_name)
                        if isolation_success:
                            self.update_status(f"Temporary isolation created for {account_name}")                            # Use the RobloxLauncher's direct protocol method (no Play button click)
                            launch_thread = self.roblox_launcher.roblox_launcher.launch_account_direct_protocol(
                                account_name, cookie, server_link
                            )
                            if launch_thread:
                                launch_thread.join(timeout=30)  # Reduced timeout to prevent hanging
                                if launch_thread.is_alive():
                                    self.update_status(f"Warning: Launch thread for {account_name} is still running")
                                else:
                                    self.update_status(f"Direct protocol launch thread completed for {account_name}")# Wait longer for Roblox to initialize and fully load
                            self.update_status(f"Waiting for Roblox to initialize for {account_name}...")
                            time.sleep(20)  # Increased from 15 to 20 seconds for better stability
                            self.roblox_launcher.symlink_manager.remove_storage_isolation(
                                account_name, restore_backup=True, backup_path=backup_path
                            )
                            self.update_status(f"Temporary isolation removed for {account_name}")
                            success = True
                        else:
                            self.update_status(f"Failed to create isolation for {account_name}")
                            success = False
                        if success:
                            self.update_status(f"✓ {account_name} launched directly via protocol")
                        else:
                            self.update_status(f"✗ {account_name} direct launch failed")
                        if i < len(selected_accounts) - 1:
                            self.update_status(f"Waiting {delay + 5} seconds before next Direct Join launch...")
                            time.sleep(delay + 5)  # Extra time for protocol handler stability
                    self.update_status(f"Direct join completed for {len(selected_accounts)} accounts")
                else:
                    self.update_status(f"Using Browser + Play Button method for {len(selected_accounts)} accounts...")
                    success_count = 0
                    for i, (account_name, cookie) in enumerate(selected_accounts):
                        self.update_status(f"Launching {account_name} with browser method ({i+1}/{len(selected_accounts)})...")
                        success = self.roblox_launcher.launch_account_with_temporary_isolation(
                            account_name, cookie, server_link
                        )
                        if success:
                            self.update_status(f"✓ {account_name} launched with Play button click")
                            success_count += 1
                        else:
                            self.update_status(f"✗ {account_name} browser launch failed")
                        if i < len(selected_accounts) - 1:
                            self.update_status(f"Waiting {delay} seconds before next launch...")
                            time.sleep(delay)
                    self.update_status(f"Browser method completed: {success_count}/{len(selected_accounts)} successful")
            except Exception as e:
                self.update_status(f"Launch error: {str(e)}")
            finally:
                time.sleep(1)
                for account_name, _ in selected_accounts:
                    self.active_account_launches.discard(account_name)
                self.root.after(0, lambda: self.launch_button.config(state='normal'))
        threading.Thread(target=launch_thread, daemon=True).start()
    def stop_all_sessions(self):
        """Stop all active Roblox instances and clean up LocalStorage isolations."""
        stopped_count = self.roblox_launcher.stop_all_instances()
        self.update_status(f"Stopped {stopped_count} instances and cleaned up LocalStorage isolations")
    def cleanup_old_instances(self):
        """Clean up old instance directories and backups."""
        try:
            results = self.roblox_launcher.cleanup_old_data(24)  # 24 hours
            backups_cleaned = results.get('backups_cleaned', 0)
            if backups_cleaned > 0:
                self.update_status(f"🧹 Cleaned up {backups_cleaned} old backups")
            else:
                self.update_status("🧹 No old data to clean up")
        except Exception as e:
            self.update_status(f"Cleanup error: {e}")
    def show_instance_status(self):
        """Show detailed instance and isolation status in a dialog."""
        try:
            status = self.roblox_launcher.get_isolation_status()
            status_dialog = tk.Toplevel(self.root)
            status_dialog.title("Instance & Isolation Status")
            status_dialog.geometry("600x500")
            status_dialog.transient(self.root)
            status_dialog.grab_set()
            text_frame = ttk.Frame(status_dialog, padding="16")
            text_frame.pack(fill=tk.BOTH, expand=True)
            status_text = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 9))
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=status_text.yview)
            status_text.configure(yscrollcommand=scrollbar.set)
            status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)            # Format status information
            status_info = f"""Instance & LocalStorage Isolation Status
=========================================
Active Launches: {status.get('active_launches', 0)}
Active Isolations: {status.get('active_isolations', 0)}
Browser Sessions: {status.get('active_browser_sessions', 0)}
Launch Threads: {status.get('active_launch_threads', 0)}
LocalStorage Status:
Exists: {status.get('roblox_localstorage_exists', False)}
Is Symlink: {status.get('roblox_localstorage_is_symlink', False)}
Active Isolations:
"""
            if status.get('isolations'):
                for account_name, info in status['isolations'].items():
                    status_info += f"""
{account_name}
  Target: {info.get('target_path', 'Unknown')}
  Active: {info.get('is_active', False)}
  Target Exists: {info.get('target_exists', False)}
"""
            else:
                status_info += "\nNo active isolations"
            if status.get('launches'):
                status_info += f"\nActive Launches:\n"
                for account_name, info in status['launches'].items():
                    running_time = int(info.get('running_time', 0))
                    hours = running_time // 3600
                    minutes = (running_time % 3600) // 60
                    seconds = running_time % 60
                    launch_method = info.get('launch_method', 'unknown')
                    fishtrap_used = "Yes" if info.get('fishtrap_used', False) else "No"
                    status_info += f"""
{account_name}
  Server: {info.get('server_url', 'Unknown')}
  Running Time: {hours:02d}:{minutes:02d}:{seconds:02d}
  Launch Method: {launch_method}
  Fishtrap: {fishtrap_used}
"""
            else:
                status_info += f"\nActive Launches:\nNo active launches"
            status_text.insert(tk.END, status_info)
            status_text.config(state=tk.DISABLED)
            ttk.Button(status_dialog, text="Close", 
                      command=status_dialog.destroy).pack(pady=10)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get status: {e}")
    def load_saved_links(self):
        """Load saved links from saved_links.json and update dropdown."""
        path = os.path.join(os.path.dirname(__file__), 'saved_links.json')
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.saved_links = json.load(f)
            else:
                self.saved_links = {}
        except Exception as e:
            self.saved_links = {}
            self.update_status(f"Failed to load saved links: {e}")
        self.saved_links_combo['values'] = list(self.saved_links.keys())
        if self.saved_links:
            self.saved_links_var.set(list(self.saved_links.keys())[0])
        else:
            self.saved_links_var.set('Select saved link...')
    def save_current_link(self):
        """Save the current link with a name to saved_links.json."""
        link = self.server_entry.get().strip()
        if not link or link == "Enter game/private server link...":
            messagebox.showwarning("Missing Link", "Please enter a valid server link to save.")
            return
        name = simpledialog.askstring("Save Link", "Enter a name for this link:")
        if not name:
            return
        if name in self.saved_links and not messagebox.askyesno("Overwrite?", f"Link '{name}' already exists. Overwrite?"):
            return
        self.saved_links[name] = link
        self._write_saved_links()
        self.load_saved_links()
        self.saved_links_var.set(name)
        self.update_status(f"Saved link '{name}'.")
    def delete_saved_link(self):
        """Delete the selected saved link."""
        name = self.saved_links_var.get()
        if name not in self.saved_links:
            messagebox.showinfo("Delete Link", "No saved link selected.")
            return
        if not messagebox.askyesno("Delete Link", f"Delete saved link '{name}'?"):
            return
        del self.saved_links[name]
        self._write_saved_links()
        self.load_saved_links()
        self.server_entry.delete(0, tk.END)
        self.update_status(f"Deleted link '{name}'.")
    def on_saved_link_selected(self, event=None):
        """Update the server entry when a saved link is selected."""
        name = self.saved_links_var.get()
        link = self.saved_links.get(name, "")
        self.server_entry.delete(0, tk.END)
        self.server_entry.insert(0, link)
    def _write_saved_links(self):
        """Write the saved links to saved_links.json."""
        path = os.path.join(os.path.dirname(__file__), 'saved_links.json')
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.saved_links, f, indent=2)
        except Exception as e:
            self.update_status(f"Failed to save links: {e}")
    def save_data_debounced(self):
        """Save data with debouncing to avoid excessive saves."""
        current_time = time.time()
        self._last_save_time = current_time
        def delayed_save():
            time.sleep(self._save_delay)
            if time.time() - self._last_save_time >= self._save_delay:
                self.save_data()
        threading.Thread(target=delayed_save, daemon=True).start()
    def save_data(self):
        """Save accounts data with encryption."""
        if self.master_password:
            success = self.security_manager.encrypt_data(self.accounts_data, self.master_password)
            if not success:
                messagebox.showerror("Error", "Failed to save account data.")
    def update_status(self, message):
        """Update status text area."""
        def update():
            self.status_text.config(state=tk.NORMAL)
            self.status_text.insert(tk.END, f"{message}\n")
            self.status_text.see(tk.END)
            self.status_text.config(state=tk.DISABLED)
        if threading.current_thread() == threading.main_thread():
            update()
        else:
            self.root.after(0, update)
    def _launch_direct_join(self, account_name: str, roblosecurity_cookie: str, server_link: str) -> bool:
        """
        Launch account using Direct Join method (for PS links).
        Uses headless browser with cookie injection but NO Play button clicking.
        """
        driver = None
        try:
            self.update_status(f"Setting up headless browser for {account_name}...")
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-images")
            options.set_preference("network.protocol-handler.external.roblox", True)
            options.set_preference("network.protocol-handler.external.roblox-player", True)
            options.set_preference("network.protocol-handler.warn-external.roblox", False)
            options.set_preference("network.protocol-handler.warn-external.roblox-player", False)
            from selenium.webdriver.firefox.service import Service
            from webdriver_manager.firefox import GeckoDriverManager
            service = Service(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
            driver.set_page_load_timeout(30)
            self.update_status(f"Injecting authentication cookie for {account_name}...")
            driver.get("https://www.roblox.com")
            time.sleep(2)
            driver.delete_all_cookies()
            clean_cookie = self._clean_roblosecurity_cookie(roblosecurity_cookie)
            driver.add_cookie({
                'name': '.ROBLOSECURITY',
                'value': clean_cookie,
                'domain': '.roblox.com',
                'path': '/',
                'secure': True,
                'httpOnly': True
            })
            cookies = driver.get_cookies()
            cookie_present = any(c['name'] == '.ROBLOSECURITY' for c in cookies)
            if not cookie_present:
                self.update_status(f"Warning: Cookie verification failed for {account_name}")
                return False
            self.update_status(f"Cookie injected successfully for {account_name}")
            self.update_status(f"Loading private server link for {account_name}...")
            driver.get(server_link)
            time.sleep(5)
            self.update_status(f"Private server protocol triggered for {account_name}")
            driver.quit()
            return True
        except Exception as e:
            self.update_status(f"Direct join failed for {account_name}: {str(e)}")
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    def _clean_roblosecurity_cookie(self, cookie: str) -> str:
        """Clean the .ROBLOSECURITY cookie by removing warning prefixes."""
        warning_prefix = "_|WARNING"
        if cookie.startswith(warning_prefix):
            return cookie.split('|_')[-1]
        return cookie
    def run(self):
        """Start the application."""
        self.root.mainloop()
    def __del__(self):
        """Cleanup on destruction."""
        if hasattr(self, 'roblox_launcher'):
            self.roblox_launcher.cleanup_all_sessions()
class AccountDialog:
    """Dialog for adding new accounts."""
    def __init__(self, parent):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Account")
        self.dialog.geometry("500x400")  # Increased size for better layout
        self.dialog.minsize(480, 380)    # Prevent shrinking too much
        self.dialog.resizable(True, True)  # Allow resizing
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        self.setup_dialog()
    def setup_dialog(self):
        """Setup the dialog interface."""
        self.dialog.configure(bg='#f8f9fa')
        style = ttk.Style()
        style.configure('Dialog.TButton', font=('Segoe UI', 9), padding=(10, 5), width=12)
        style.configure('Primary.TButton', font=('Segoe UI', 9, 'bold'), padding=(12, 6), width=15)
        style.map('Primary.TButton', background=[('active', '#3498db')])
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        title_label = ttk.Label(main_frame, text="Add Account", 
                               font=('Segoe UI', 14, 'bold'))
        title_label.pack(pady=(0, 16))
        name_section = ttk.Frame(main_frame)
        name_section.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(name_section, text="Account Name", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 4))
        self.name_entry = ttk.Entry(name_section, font=('Segoe UI', 9))
        self.name_entry.pack(fill=tk.X, pady=(0, 0))
        cookie_section = ttk.Frame(main_frame)
        cookie_section.pack(fill=tk.BOTH, expand=True, pady=(0, 16))
        ttk.Label(cookie_section, text="Cookie (.ROBLOSECURITY)", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 4))
        instruction_text = "F12 → Application → Cookies → roblox.com → Copy .ROBLOSECURITY value"
        instruction_label = ttk.Label(cookie_section, text=instruction_text, 
                                     font=('Segoe UI', 8), foreground='#6c757d', wraplength=400)
        instruction_label.pack(anchor=tk.W, pady=(0, 6))
        cookie_frame = ttk.Frame(cookie_section)
        cookie_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        self.cookie_text = tk.Text(cookie_frame, height=6, wrap=tk.WORD, font=('Segoe UI', 9),
                                  bg='#ffffff', fg='#495057', relief='solid', borderwidth=1)
        cookie_scrollbar = ttk.Scrollbar(cookie_frame, orient=tk.VERTICAL, command=self.cookie_text.yview)
        self.cookie_text.configure(yscrollcommand=cookie_scrollbar.set)
        self.cookie_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cookie_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(16, 0))
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=self.cancel,
                              style='Dialog.TButton')
        cancel_btn.pack(side=tk.RIGHT, padx=(8, 0))
        add_btn = ttk.Button(button_frame, text="Add Account", command=self.add_account,
                           style='Primary.TButton')
        add_btn.pack(side=tk.RIGHT, padx=(0, 0))
        self.name_entry.focus()
    def add_account(self):
        """Validate and add the account."""
        name = self.name_entry.get().strip()
        cookie = self.cookie_text.get("1.0", tk.END).strip()
        if not name:
            messagebox.showerror("Error", "Please enter an account name.")
            return
        if not cookie:
            messagebox.showerror("Error", "Please enter the .ROBLOSECURITY cookie.")
            return
        if len(cookie) < 100:
            if not messagebox.askyesno("Confirm", 
                                     "Cookie seems too short. Are you sure this is a valid .ROBLOSECURITY cookie?"):
                return
        import re
        if not re.match(r'^[A-Fa-f0-9]+$', cookie):
            if not messagebox.askyesno("Confirm", 
                                     "Cookie doesn't appear to be in the expected hexadecimal format. Continue anyway?"):
                return
        self.result = (name, cookie)
        self.dialog.destroy()
    def cancel(self):
        """Cancel dialog."""
        self.dialog.destroy()
if __name__ == "__main__":
    app = AccountManager()
    app.run()
