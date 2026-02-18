diff --git a/cloudflare_dns_manager.py b/cloudflare_dns_manager.py
index cd83f95b6d02ec0b5acb0041e533a95ea8420877..7adb0637fe12447eaba17af5758b37dbb3eb0dc0 100644
--- a/cloudflare_dns_manager.py
+++ b/cloudflare_dns_manager.py
@@ -1,45 +1,59 @@
 import os
 import sys
 import json
 import logging
 import argparse
 import subprocess
 from datetime import datetime
 import time
 import requests
 from tabulate import tabulate
 from colorama import init, Fore, Style
 from apscheduler.schedulers.blocking import BlockingScheduler
 import dns.resolver
 from requests.adapters import HTTPAdapter
 from urllib3.util.retry import Retry
 from concurrent.futures import ThreadPoolExecutor
 import smtplib
 from email.message import EmailMessage
 import unittest
 
+
+def prompt_yes_no(message, default=False):
+    """Prompt for a yes/no answer with a default option."""
+    suffix = "Y/n" if default else "y/N"
+    while True:
+        answer = input(f"{message} ({suffix}): ").strip().lower()
+        if not answer:
+            return default
+        if answer in ['y', 'yes']:
+            return True
+        if answer in ['n', 'no']:
+            return False
+        print_error("Please answer with 'y' or 'n'.")
+
 # Initialize colorama for colored output
 init()
 
 # Setup logging
 logging.basicConfig(
     filename='cloudflare_dns.log',
     level=logging.INFO,
     format='%(asctime)s - %(levelname)s - %(message)s'
 )
 
 # Configuration files
 CONFIG_FILE = 'cloudflare_config.json'
 AUTO_UPDATE_CONFIG_FILE = 'auto_update_config.json'
 CACHE_FILE = 'ip_cache.json'
 HISTORY_FILE = 'ip_history.json'
 CHANGE_LOG_FILE = 'dns_change_history.log'
 CACHE_TIMEOUT = 300  # 5 minutes
 
 # List of required packages
 REQUIRED_PACKAGES = ['requests', 'tabulate', 'colorama', 'apscheduler']
 
 # Valid DNS record types
 VALID_RECORD_TYPES = ['A', 'CNAME', 'TXT', 'MX', 'AAAA', 'NS', 'SRV']
 
 def load_config():
@@ -53,81 +67,81 @@ def load_config():
         logging.error(f"Failed to load config file: {e}")
         print_error(f"Error: Could not load configuration: {e}")
         return {}
 
 def save_config(config):
     """Save configuration to JSON file."""
     try:
         with open(CONFIG_FILE, 'w') as f:
             json.dump(config, f, indent=4)
         logging.info("Configuration saved.")
         print_success("Configuration saved successfully.")
     except Exception as e:
         logging.error(f"Failed to save config file: {e}")
         print_error(f"Error: Could not save configuration: {e}")
 
 def setup_wizard():
     """Interactive setup wizard to configure Cloudflare and notification settings."""
     print("Welcome to the Cloudflare DNS Setup Wizard")
     config = load_config()
     
     # Cloudflare API settings
     config['CLOUDFLARE_API_TOKEN'] = input("Enter Cloudflare API Token: ").strip()
     config['CLOUDFLARE_ACCOUNT_ID'] = input("Enter Cloudflare Account ID: ").strip()
     
     # Email settings
-    enable_email = input("Configure email notifications? (y/n): ").lower() == 'y'
+    enable_email = prompt_yes_no("Configure email notifications?", default=False)
     if enable_email:
         config['EMAIL_FROM'] = input("Enter sender email address: ").strip()
         config['SMTP_SERVER'] = input("Enter SMTP server (e.g., smtp.gmail.com): ").strip()
         config['SMTP_PORT'] = input("Enter SMTP port (default 587): ").strip() or '587'
         config['EMAIL_PASSWORD'] = input("Enter SMTP password: ").strip()
     
     # Discord settings
-    enable_discord = input("Configure Discord notifications? (y/n): ").lower() == 'y'
+    enable_discord = prompt_yes_no("Configure Discord notifications?", default=False)
     if enable_discord:
         config['DISCORD_WEBHOOK_URL'] = input("Enter Discord Webhook URL: ").strip()
     
     save_config(config)
     print_success("Setup completed. Configuration saved to cloudflare_config.json")
 
 def print_success(message):
     """Print a success message in green."""
     print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
 
 def print_error(message):
     """Print an error message in red."""
     print(f"{Fore.RED}{message}{Style.RESET_ALL}")
 
 def check_python_environment():
     """Check the Python environment and pip version."""
     python_version = sys.version
     try:
         pip_version = subprocess.check_output([sys.executable, '-m', 'pip', '--version']).decode().strip()
         logging.info(f"Python version: {python_version}")
         logging.info(f"Pip version: {pip_version}")
-        print_success(f"Usinguvi Python: {python_version}")
+        print_success(f"Using Python: {python_version}")
         print_success(f"Using Pip: {pip_version}")
     except subprocess.CalledProcessError as e:
         logging.error(f"Failed to check pip version: {e}")
         print_error("Error: Could not verify pip version. Ensure pip is installed and accessible.")
         sys.exit(1)
 
 def install_dependencies():
     """Check and install required Python packages if not present."""
     check_python_environment()
     for package in REQUIRED_PACKAGES:
         try:
             __import__(package)
             logging.info(f"Package {package} is already installed.")
             print_success(f"Package {package} is already installed.")
         except ImportError:
             print(f"Installing {package}...")
             for attempt in range(2):  # Retry once
                 try:
                     subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '--user'])
                     logging.info(f"Successfully installed {package}.")
                     print_success(f"{package} installed successfully.")
                     break
                 except subprocess.CalledProcessError as e:
                     logging.error(f"Attempt {attempt + 1} failed to install {package}: {e}")
                     if attempt == 1:
@@ -735,240 +749,255 @@ def manage_domain(zone_id, domain_name, dry_run=False):
         print("5. Enable proxy")
         print("6. Disable proxy")
         print("7. Auto-update IP")
         print("8. Search records")
         print("9. Check record resolution")
         print("10. Backup records")
         print("11. Show zone stats")
         print("12. Create record type chart")
         print("13. Back")
         choice = input("Select an action: ")
         records = list_records(zone_id)
         
         if choice == '1':
             if records:
                 print("\nDNS Records:")
                 print(tabulate(records, headers=['Name', 'Type', 'Content', 'TTL', 'Proxied', 'ID'], tablefmt='grid'))
             else:
                 print_error("No records found.")
         
         elif choice == '2':
             try:
                 record_type = input("Enter record type (e.g., A, CNAME, TXT): ").upper()
                 name = input("Enter record name (e.g., www): ")
                 content = input("Enter content (e.g., 192.0.2.1): ")
                 ttl = int(input("Enter TTL (e.g., 300): ") or 300)
-                proxied = input("Enable proxy? (y/n): ").lower() == 'y'
+                proxied = prompt_yes_no("Enable proxy?", default=False)
                 add_record(zone_id, record_type, name, content, ttl, proxied, dry_run)
-                if record_type == 'A' and input("Enable auto-update for this record? (y/n): ").lower() == 'y':
+                if record_type == 'A' and prompt_yes_no("Enable auto-update for this record?", default=False):
                     new_record = list_records(zone_id)[-1]
                     auto_update_config[f"{domain_name}:{name}"] = {'zone_id': zone_id, 'record_id': new_record[5]}
                     save_auto_update_config(auto_update_config)
             except ValueError as e:
                 print_error(str(e))
         
         elif choice in ['3', '5', '6', '7']:
             if not records:
                 print_error("No records to manage.")
                 continue
             print("\nSelect a record:")
             for i, (name, rtype, content, ttl, proxied, rid) in enumerate(records, 1):
                 print(f"{i}. {name} ({rtype}) -> {content}")
             try:
                 index = int(input("Enter record number: ")) - 1
                 if 0 <= index < len(records):
                     name, rtype, content, ttl, proxied, record_id = records[index]
                     if choice == '3':
                         new_content = input(f"Enter new content (current: {content}): ") or content
                         new_ttl = int(input(f"Enter new TTL (current: {ttl}): ") or ttl)
-                        new_proxied = input(f"Enable proxy? (current: {proxied}) (y/n): ").lower() == 'y'
+                        new_proxied = prompt_yes_no(f"Enable proxy? (current: {proxied})", default=proxied)
                         update_record(zone_id, record_id, rtype, name, new_content, new_ttl, new_proxied, dry_run)
                     elif choice == '5':
                         toggle_proxy(zone_id, record_id, True, dry_run)
                     elif choice == '6':
                         toggle_proxy(zone_id, record_id, False, dry_run)
                     elif choice == '7':
                         auto_update_ip(zone_id, record_id, domain_name, name, dry_run)
-                        if input("Enable auto-update for this record? (y/n): ").lower() == 'y':
+                        if prompt_yes_no("Enable auto-update for this record?", default=False):
                             auto_update_config[f"{domain_name}:{name}"] = {'zone_id': zone_id, 'record_id': record_id}
                             save_auto_update_config(auto_update_config)
             except ValueError:
                 print_error("Invalid input.")
         
         elif choice == '4':
             if not records:
                 print_error("No records to delete.")
                 continue
             print("\nSelect a record to delete:")
             for i, (name, rtype, content, _, _, rid) in enumerate(records, 1):
                 print(f"{i}. {name} ({rtype}) -> {content}")
             try:
                 index = int(input("Enter record number: ")) - 1
                 if 0 <= index < len(records):
-                    if input(f"Confirm deletion of {records[index][0]}? (y/n): ").lower() == 'y':
+                    if prompt_yes_no(f"Confirm deletion of {records[index][0]}?", default=False):
                         delete_record(zone_id, records[index][5], domain_name, records[index][0], dry_run)
                         key = f"{domain_name}:{records[index][0]}"
                         if key in auto_update_config:
                             del auto_update_config[key]
                             save_auto_update_config(auto_update_config)
             except ValueError:
                 print_error("Invalid input.")
         
         elif choice == '8':
             search_term = input("Enter search term (name or content): ")
             search_records(zone_id, search_term)
         
         elif choice == '9':
             record_name = input("Enter record name to resolve: ")
             record_type = input("Enter record type (e.g., A, CNAME): ").upper()
             check_record_resolution(record_name, record_type)
         
         elif choice == '10':
             backup_records(zone_id, domain_name)
         
         elif choice == '11':
             show_zone_stats(zone_id)
         
         elif choice == '12':
             chart = create_record_type_chart(zone_id)
             print(json.dumps(chart, indent=4))
         
         elif choice == '13':
             break
         else:
             print_error("Invalid choice.")
 
 def command_line_mode(args):
     """Handle command-line arguments."""
     if not os.path.exists(CONFIG_FILE):
         print_error("Configuration file not found. Running setup wizard...")
         setup_wizard()
     validate_api_token()
     domains = list_domains()
     domain_map = {d[0]: d[1] for d in domains}
-    
-    if args.domain not in domain_map:
-        print_error(f"Error: Domain {args.domain} not found.")
-        sys.exit(1)
-    
-    zone_id = domain_map[args.domain]
+
+    domain_optional_actions = {'list-all'}
+    if args.action not in domain_optional_actions:
+        if not args.domain:
+            print_error("Error: --domain is required for this action.")
+            if domain_map:
+                print("Available domains:")
+                for domain in sorted(domain_map):
+                    print(f"- {domain}")
+            sys.exit(1)
+        if args.domain not in domain_map:
+            print_error(f"Error: Domain {args.domain} not found.")
+            if domain_map:
+                print("Available domains:")
+                for domain in sorted(domain_map):
+                    print(f"- {domain}")
+            sys.exit(1)
+
+    zone_id = domain_map.get(args.domain)
     auto_update_config = load_auto_update_config()
-    
+
     if args.action == 'list':
         records = list_records(zone_id)
         if records:
             if args.json:
                 print(json.dumps(records, indent=4))
             else:
                 print(tabulate(records, headers=['Name', 'Type', 'Content', 'TTL', 'Proxied', 'ID'], tablefmt='grid'))
         else:
             print_error("No records found.")
     
     elif args.action == 'add':
         add_record(zone_id, args.type, args.name, args.content, args.ttl, args.proxied, args.dry_run)
         if args.auto_update_ip:
             records = list_records(zone_id)
             for r in records:
                 if r[0] == args.name and r[1] == args.type:
                     auto_update_config[f"{args.domain}:{args.name}"] = {'zone_id': zone_id, 'record_id': r[5]}
                     save_auto_update_config(auto_update_config)
                     break
     
     elif args.action in ['edit', 'enable-proxy', 'disable-proxy', 'auto-update-ip']:
         records = list_records(zone_id)
         record_id = None
         for r in records:
             if r[5] == args.record_id or (r[0] == args.name and r[1] == args.type):
                 record_id = r[5]
                 record = r
                 break
         if not record_id:
             print_error("Error: Record not found.")
             sys.exit(1)
         
         if args.action == 'edit':
             update_record(zone_id, record_id, record[1], record[0], args.content or record[2], args.ttl or record[3], args.proxied if args.proxied is not None else record[4], args.dry_run)
         elif args.action == 'enable-proxy':
             toggle_proxy(zone_id, record_id, True, args.dry_run)
         elif args.action == 'disable-proxy':
             toggle_proxy(zone_id, record_id, False, args.dry_run)
         elif args.action == 'auto-update-ip':
             auto_update_ip(zone_id, record_id, args.domain, record[0], args.dry_run)
             if args.auto_update_ip:
                 auto_update_config[f"{args.domain}:{record[0]}"] = {'zone_id': zone_id, 'record_id': record_id}
                 save_auto_update_config(auto_update_config)
     
     elif args.action == 'delete':
-        if input(f"Confirm deletion of record ID {args.record_id}? (y/n): ").lower() == 'y':
+        if args.yes or prompt_yes_no(f"Confirm deletion of record ID {args.record_id}?", default=False):
             delete_record(zone_id, args.record_id, args.domain, args.name, args.dry_run)
             key = f"{args.domain}:{args.name}"
             if key in auto_update_config:
                 del auto_update_config[key]
                 save_auto_update_config(auto_update_config)
     
     elif args.action == 'backup':
         backup_records(zone_id, args.domain)
     
     elif args.action == 'bulk-add':
-        bulk_add_records(zoid, args.file, args.dry_run)
+        bulk_add_records(zone_id, args.file, args.dry_run)
     
     elif args.action == 'search':
         search_records(zone_id, args.search_term)
     
     elif args.action == 'resolve':
         check_record_resolution(args.name, args.type)
     
     elif args.action == 'stats':
         show_zone_stats(zone_id)
     
     elif args.action == 'chart':
         chart = create_record_type_chart(zone_id)
         print(json.dumps(chart, indent=4))
     
     elif args.action == 'list-all':
         list_all_zones_records()
 
 def main():
     """Main function to parse arguments and start the script."""
     parser = argparse.ArgumentParser(
         description="Cloudflare DNS Management Script",
+        formatter_class=argparse.RawTextHelpFormatter,
         epilog="Examples:\n"
                "  List records: python cloudflare_dns_manager.py --domain example.com --action list\n"
                "  Add record: python cloudflare_dns_manager.py --domain example.com --action add --type A --name www --content 192.0.2.1 --ttl 300 --proxied\n"
                "  Backup records: python cloudflare_dns_manager.py --domain example.com --action backup\n"
                "  Bulk add: python cloudflare_dns_manager.py --domain example.com --action bulk-add --file records.json\n"
                "  Run setup wizard: python cloudflare_dns_manager.py --setup"
     )
     parser.add_argument('--domain', help="Domain name to manage")
     parser.add_argument('--action', choices=['list', 'add', 'edit', 'delete', 'enable-proxy', 'disable-proxy', 'auto-update-ip', 'backup', 'bulk-add', 'search', 'resolve', 'stats', 'chart', 'list-all'], help="Action to perform")
     parser.add_argument('--type', help="Record type (e.g., A, CNAME, TXT)")
     parser.add_argument('--name', help="Record name (e.g., www)")
     parser.add_argument('--content', help="Record content (e.g., 192.0.2.1)")
     parser.add_argument('--ttl', type=int, default=300, help="TTL for the record")
     parser.add_argument('--proxied', action='store_true', help="Enable Cloudflare proxy")
     parser.add_argument('--record-id', help="Record ID for edit/delete/proxy actions")
     parser.add_argument('--auto-update-ip', action='store_true', help="Enable auto-update for dynamic IP")
     parser.add_argument('--json', action='store_true', help="Output in JSON format")
     parser.add_argument('--dry-run', action='store_true', help="Simulate actions without making API calls")
     parser.add_argument('--file', help="JSON file for bulk operations")
     parser.add_argument('--search-term', help="Search term for record search")
     parser.add_argument('--setup', action='store_true', help="Run setup wizard")
+    parser.add_argument('--yes', action='store_true', help="Skip confirmation prompts for destructive actions")
     parser.add_argument('--version', action='version', version='Cloudflare DNS Script v1.1.0')
     
     args = parser.parse_args()
     
     if args.setup:
         setup_wizard()
     elif args.action:
         command_line_mode(args)
     else:
         interactive_mode()
 
 class TestDNSScript(unittest.TestCase):
     """Unit tests for DNS script."""
     def test_get_public_ip(self):
         ip = get_public_ip()
         self.assertIsNotNone(ip)
         self.assertRegex(ip, r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
 
 if __name__ == "__main__":
     main()
