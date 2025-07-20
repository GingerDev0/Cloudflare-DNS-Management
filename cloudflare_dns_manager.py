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
    """Load configuration from JSON file."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
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
    enable_email = input("Configure email notifications? (y/n): ").lower() == 'y'
    if enable_email:
        config['EMAIL_FROM'] = input("Enter sender email address: ").strip()
        config['SMTP_SERVER'] = input("Enter SMTP server (e.g., smtp.gmail.com): ").strip()
        config['SMTP_PORT'] = input("Enter SMTP port (default 587): ").strip() or '587'
        config['EMAIL_PASSWORD'] = input("Enter SMTP password: ").strip()
    
    # Discord settings
    enable_discord = input("Configure Discord notifications? (y/n): ").lower() == 'y'
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
        print_success(f"Usinguvi Python: {python_version}")
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
                        logging.error(f"Failed to install {package} after retries.")
                        print_error(f"Error: Failed to install {package}. Please install it manually with '{sys.executable} -m pip install {package} --user'.")
                        print_error(f"Using Python: {sys.executable}")
                        sys.exit(1)
            # Verify import after installation
            try:
                __import__(package)
                logging.info(f"Verified {package} is importable.")
            except ImportError:
                logging.error(f"Package {package} installed but not importable.")
                print_error(f"Error: {package} installed but not importable.")
                try:
                    result = subprocess.check_output([sys.executable, '-m', 'pip', 'show', package]).decode()
                    print_error(f"Package details:\n{result}")
                except subprocess.CalledProcessError:
                    print_error(f"Could not retrieve details for {package}.")
                print_error(f"Try running: {sys.executable} -m pip install {package} --user")
                print_error("Ensure the Python environment matches the installation path.")
                sys.exit(1)

def create_session_with_retries():
    """Create a requests session with retry logic for rate limiting."""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def validate_api_token():
    """Validate the Cloudflare API token using the account-specific endpoint."""
    config = load_config()
    session = create_session_with_retries()
    account_id = config.get('CLOUDFLARE_ACCOUNT_ID')
    if not account_id:
        logging.error("No account ID provided.")
        print_error("Error: Please run the setup wizard to configure CLOUDFLARE_ACCOUNT_ID.")
        sys.exit(1)
    try:
        response = session.get(f'https://api.cloudflare.com/client/v4/accounts/{account_id}/tokens/verify', headers=get_api_headers())
        response.raise_for_status()
        if not response.json()['result']['status'] == 'active':
            logging.error("API token is invalid or inactive.")
            print_error("Error: Invalid or inactive API token.")
            sys.exit(1)
        print_success("API token validated successfully.")
    except requests.RequestException as e:
        logging.error(f"Failed to validate API token: {e}")
        print_error("Error: Could not validate API token.")
        sys.exit(1)

def get_api_headers():
    """Return headers with the Cloudflare API token."""
    config = load_config()
    api_token = config.get('CLOUDFLARE_API_TOKEN')
    if not api_token:
        logging.error("No API token provided.")
        print_error("Error: Please run the setup wizard to configure CLOUDFLARE_API_TOKEN.")
        sys.exit(1)
    return {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    }

def get_cached_public_ip():
    """Fetch or retrieve cached public IP address."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
            if time.time() - cache['timestamp'] < CACHE_TIMEOUT:
                return cache['ip']
        except Exception as e:
            logging.error(f"Failed to read IP cache: {e}")
    ip = get_public_ip()
    if ip:
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump({'ip': ip, 'timestamp': time.time()}, f)
            logging.info(f"Cached public IP: {ip}")
        except Exception as e:
            logging.error(f"Failed to cache public IP: {e}")
    return ip

def get_public_ip():
    """Fetch the current public IP address."""
    session = create_session_with_retries()
    try:
        response = session.get('https://api.ipify.org', timeout=5)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        try:
            response = session.get('https://ifconfig.me', timeout=5)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logging.error(f"Failed to fetch public IP: {e}")
            print_error("Error: Could not fetch public IP.")
            return None

def load_auto_update_config():
    """Load auto-update configuration from JSON file."""
    if os.path.exists(AUTO_UPDATE_CONFIG_FILE):
        try:
            with open(AUTO_UPDATE_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to load auto-update config file: {e}")
            return {}
    return {}

def save_auto_update_config(config):
    """Save auto-update configuration to JSON file."""
    try:
        with open(AUTO_UPDATE_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        logging.info("Auto-update config saved.")
        print_success("Auto-update config saved.")
    except Exception as e:
        logging.error(f"Failed to save auto-update config file: {e}")
        print_error("Error: Could not save auto-update config.")

def list_domains():
    """List all domains (zones) in the Cloudflare account."""
    session = create_session_with_retries()
    try:
        response = session.get('https://api.cloudflare.com/client/v4/zones', headers=get_api_headers())
        response.raise_for_status()
        zones = response.json()['result']
        return [(zone['name'], zone['id']) for zone in zones]
    except requests.RequestException as e:
        handle_api_error(e.response)
        return []

def list_records(zone_id):
    """List all DNS records for a given zone."""
    session = create_session_with_retries()
    try:
        response = session.get(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records', headers=get_api_headers())
        response.raise_for_status()
        records = response.json()['result']
        return [(r['name'], r['type'], r['content'], r['ttl'], r.get('proxied', False), r['id']) for r in records]
    except requests.RequestException as e:
        handle_api_error(e.response)
        return []

def validate_record_type(record_type):
    """Validate DNS record type."""
    if record_type.upper() not in VALID_RECORD_TYPES:
        raise ValueError(f"Invalid record type: {record_type}. Supported types: {', '.join(VALID_RECORD_TYPES)}")

def add_record(zone_id, record_type, name, content, ttl=300, proxied=False, dry_run=False):
    """Add a new DNS record."""
    try:
        validate_record_type(record_type)
        # Construct full domain name for notification
        domains = list_domains()
        domain_name = next((d[0] for d in domains if d[1] == zone_id), "unknown")
        full_name = name if name.endswith(domain_name) else f"{name}.{domain_name}"
        if dry_run:
            print(f"[Dry Run] Would add record: {full_name} ({record_type}) -> {content}")
            log_change("ADD", domain_name, name, f"Type: {record_type}, Content: {content}, TTL: {ttl}, Proxied: {proxied}")
            return
        data = {
            'type': record_type,
            'name': name,
            'content': content,
            'ttl': ttl,
            'proxied': proxied
        }
        session = create_session_with_retries()
        response = session.post(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records', headers=get_api_headers(), json=data)
        response.raise_for_status()
        logging.info(f"Added record: {full_name} ({record_type}) -> {content}")
        print_success(f"Record {full_name} added successfully.")
        log_change("ADD", domain_name, name, f"Type: {record_type}, Content: {content}, TTL: {ttl}, Proxied: {proxied}")
        send_discord_notification("DNS Record Added", f"{full_name} ({record_type}) -> {content}", 0x00FF00)  # Green color
        send_email("DNS Record Added", f"Added record: {full_name} ({record_type}) -> {content}", "admin@example.com")
    except (requests.RequestException, ValueError) as e:
        logging.error(f"Failed to add record: {e}")
        print_error(f"Error: Could not add record: {e}")

def update_record(zone_id, record_id, record_type, name, content, ttl, proxied, dry_run=False):
    """Update an existing DNS record."""
    try:
        validate_record_type(record_type)
        # Construct full domain name for notification
        domains = list_domains()
        domain_name = next((d[0] for d in domains if d[1] == zone_id), "unknown")
        full_name = name if name.endswith(domain_name) else f"{name}.{domain_name}"
        if dry_run:
            print(f"[Dry Run] Would update record: {full_name} ({record_type}) -> {content}")
            log_change("UPDATE", domain_name, name, f"Type: {record_type}, Content: {content}, TTL: {ttl}, Proxied: {proxied}")
            return
        data = {
            'type': record_type,
            'name': name,
            'content': content,
            'ttl': ttl,
            'proxied': proxied
        }
        session = create_session_with_retries()
        response = session.put(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}', headers=get_api_headers(), json=data)
        response.raise_for_status()
        logging.info(f"Updated record: {full_name} ({record_type}) -> {content}")
        print_success(f"Record {full_name} updated successfully.")
        log_change("UPDATE", domain_name, name, f"Type: {record_type}, Content: {content}, TTL: {ttl}, Proxied: {proxied}")
        send_discord_notification("DNS Record Updated", f"{full_name} ({record_type}) -> {content}", 0xFFFF00)  # Yellow color
        send_email("DNS Record Updated", f"Updated record: {full_name} ({record_type}) -> {content}", "admin@example.com")
    except (requests.RequestException, ValueError) as e:
        logging.error(f"Failed to update record: {e}")
        print_error(f"Error: Could not update record: {e}")

def delete_record(zone_id, record_id, domain_name, record_name, dry_run=False):
    """Delete a DNS record."""
    # Construct full domain name for notification
    full_name = record_name if record_name.endswith(domain_name) else f"{record_name}.{domain_name}"
    if dry_run:
        print(f"[Dry Run] Would delete record: {full_name}")
        log_change("DELETE", domain_name, record_name, f"Record ID: {record_id}")
        return
    session = create_session_with_retries()
    try:
        response = session.delete(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}', headers=get_api_headers())
        response.raise_for_status()
        logging.info(f"Deleted record ID: {record_id}")
        print_success("Record deleted successfully.")
        log_change("DELETE", domain_name, record_name, f"Record ID: {record_id}")
        send_discord_notification("DNS Record Deleted", f"Deleted record: {full_name}", 0xFF0000)  # Red color
        send_email("DNS Record Deleted", f"Deleted record: {full_name}", "admin@example.com")
    except requests.RequestException as e:
        handle_api_error(e.response)

def toggle_proxy(zone_id, record_id, enable, dry_run=False):
    """Enable or disable proxy status for a record."""
    session = create_session_with_retries()
    try:
        response = session.get(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}', headers=get_api_headers())
        response.raise_for_status()
        record = response.json()['result']
        if record['type'] not in ['A', 'CNAME']:
            print_error("Error: Proxy status only supported for A and CNAME records.")
            return
        # Construct full domain name for notification
        domains = list_domains()
        domain_name = next((d[0] for d in domains if d[1] == zone_id), "unknown")
        full_name = record['name'] if record['name'].endswith(domain_name) else f"{record['name']}.{domain_name}"
        if dry_run:
            status = "enabled" if enable else "disabled"
            print(f"[Dry Run] Would {status} proxy for record: {full_name}")
            log_change("TOGGLE_PROXY", record['name'], record['name'], f"Proxy: {status}")
            return
        data = {
            'type': record['type'],
            'name': record['name'],
            'content': record['content'],
            'ttl': record['ttl'],
            'proxied': enable
        }
        response = session.put(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}', headers=get_api_headers(), json=data)
        response.raise_for_status()
        status = "enabled" if enable else "disabled"
        logging.info(f"Proxy {status} for record ID: {record_id}")
        print_success(f"Proxy {status} successfully for {full_name}.")
        log_change("TOGGLE_PROXY", record['name'], record['name'], f"Proxy: {status}")
        send_discord_notification(f"Proxy Status Changed", f"Proxy {status} for {full_name}", 0x00FFFF)  # Cyan color
    except requests.RequestException as e:
        handle_api_error(e.response)

def auto_update_ip(zone_id, record_id, domain_name, record_name, dry_run=False):
    """Update a record with the current public IP."""
    public_ip = get_cached_public_ip()
    if not public_ip:
        return
    session = create_session_with_retries()
    try:
        response = session.get(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}', headers=get_api_headers())
        response.raise_for_status()
        record = response.json()['result']
        if record['type'] != 'A':
            print_error("Error: Auto-update only supported for A records.")
            return
        # Construct full domain name for notification
        full_name = record_name if record_name.endswith(domain_name) else f"{record_name}.{domain_name}"
        if record['content'] == public_ip:
            print(f"Record {full_name} already up-to-date with IP: {public_ip}")
            return
        if dry_run:
            print(f"[Dry Run] Would update {full_name} to IP: {public_ip}")
            log_change("AUTO_UPDATE", domain_name, record_name, f"New IP: {public_ip}")
            return
        data = {
            'type': record['type'],
            'name': record['name'],
            'content': public_ip,
            'ttl': record['ttl'],
            'proxied': record.get('proxied', False)
        }
        response = session.put(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}', headers=get_api_headers(), json=data)
        response.raise_for_status()
        logging.info(f"Auto-updated {full_name} to IP: {public_ip}")
        print_success(f"Record {full_name} updated with new IP: {public_ip}")
        log_change("AUTO_UPDATE", domain_name, record_name, f"New IP: {public_ip}")
        track_ip_changes(domain_name, record_name, public_ip)
        send_discord_notification("DNS IP Auto-Update", f"Record {full_name} updated to IP: {public_ip}", 0x0000FF)  # Blue color
        send_email("DNS IP Auto-Update", f"Record {full_name} updated to IP: {public_ip}", "admin@example.com")
    except requests.RequestException as e:
        handle_api_error(e.response)

def handle_api_error(response):
    """Handle API errors with detailed messages."""
    try:
        error_data = response.json().get('errors', [])
        for error in error_data:
            logging.error(f"API Error: {error['message']} (Code: {error['code']})")
            print_error(f"API Error: {error['message']} (Code: {error['code']})")
    except (ValueError, AttributeError):
        logging.error(f"API Error: {response.text}")
        print_error(f"API Error: {response.text}")

def log_change(action, domain_name, record_name, details):
    """Log DNS changes to a history file."""
    try:
        with open(CHANGE_LOG_FILE, 'a') as f:
            f.write(f"{datetime.now()} - {action} - {domain_name}:{record_name} - {details}\n")
    except Exception as e:
        logging.error(f"Failed to log change: {e}")

def send_email(subject, body, to_email):
    """Send email notification for DNS changes."""
    config = load_config()
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = config.get('EMAIL_FROM')
    msg['To'] = to_email
    smtp_server = config.get('SMTP_SERVER')
    smtp_port = config.get('SMTP_PORT', '587')
    smtp_user = config.get('EMAIL_FROM')
    smtp_password = config.get('EMAIL_PASSWORD')
    
    if not all([smtp_server, smtp_user, smtp_password]):
        logging.error("Missing email configuration.")
        print_error("Error: Please run the setup wizard to configure email settings.")
        return
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logging.info(f"Email sent to {to_email}: {subject}")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        print_error(f"Error: Failed to send email: {e}")

def send_discord_notification(title, description, color=0x00FF00):
    """Send Discord notification for DNS changes using an embed."""
    config = load_config()
    webhook_url = config.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        logging.error("No Discord webhook URL provided.")
        print_error("Error: Please run the setup wizard to configure DISCORD_WEBHOOK_URL.")
        return
    payload = {
        'embeds': [{
            'title': title,
            'description': description,
            'color': color,
            'timestamp': datetime.utcnow().isoformat()
        }]
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        logging.info("Discord notification sent.")
    except requests.RequestException as e:
        logging.error(f"Failed to send Discord notification: {e}")
        print_error(f"Error: Failed to send Discord notification: {e}")

def backup_records(zone_id, domain_name):
    """Backup DNS records to a JSON file."""
    records = list_records(zone_id)
    backup_file = f"{domain_name}_dns_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(backup_file, 'w') as f:
            json.dump(records, f, indent=4)
        logging.info(f"DNS records backed up to {backup_file}")
        print_success(f"Backup saved to {backup_file}")
        send_discord_notification("DNS Records Backed Up", f"Backup saved to {backup_file}", 0x00FFFF)
    except Exception as e:
        logging.error(f"Failed to backup records: {e}")
        print_error(f"Error: Could not backup records: {e}")

def bulk_add_records(zone_id, file_path, dry_run=False):
    """Add multiple DNS records from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            records = json.load(f)
        for record in records:
            add_record(
                zone_id,
                record['type'],
                record['name'],
                record['content'],
                record.get('ttl', 300),
                record.get('proxied', False),
                dry_run
            )
        print_success(f"Processed {len(records)} records from {file_path}")
        send_discord_notification("Bulk DNS Records Added", f"Processed {len(records)} records from {file_path}", 0x00FF00)
    except Exception as e:
        logging.error(f"Failed to process bulk records: {e}")
        print_error(f"Error: Could not process bulk records: {e}")

def search_records(zone_id, search_term):
    """Search DNS records by name or content."""
    records = list_records(zone_id)
    filtered = [r for r in records if search_term.lower() in r[0].lower() or search_term.lower() in r[2].lower()]
    if filtered:
        print(tabulate(filtered, headers=['Name', 'Type', 'Content', 'TTL', 'Proxied', 'ID'], tablefmt='grid'))
    else:
        print_error("No matching records found.")

def check_record_resolution(record_name, record_type):
    """Check if a DNS record resolves correctly."""
    try:
        validate_record_type(record_type)
        answers = dns.resolver.resolve(record_name, record_type)
        for rdata in answers:
            print_success(f"{record_name} ({record_type}) resolves to: {rdata}")
    except Exception as e:
        logging.error(f"Failed to resolve {record_name}: {e}")
        print_error(f"Error: Could not resolve {record_name}: {e}")

def show_zone_stats(zone_id):
    """Display statistics about DNS records in a zone."""
    records = list_records(zone_id)
    type_counts = {}
    proxied_count = 0
    for r in records:
        type_counts[r[1]] = type_counts.get(r[1], 0) + 1
        if r[4]:
            proxied_count += 1
    print_success(f"Total Records: {len(records)}")
    print_success(f"Proxied Records: {proxied_count}")
    print_success("Record Types: " + ", ".join(f"{k}: {v}" for k, v in type_counts.items()))

def create_record_type_chart(zone_id):
    """Create a Chart.js-compatible pie chart for record types."""
    records = list_records(zone_id)
    type_counts = {}
    for r in records:
        type_counts[r[1]] = type_counts.get(r[1], 0) + 1
    chart = {
        "type": "pie",
        "data": {
            "labels": list(type_counts.keys()),
            "datasets": [{
                "label": "Record Types",
                "data": list(type_counts.values()),
                "backgroundColor": ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF"],
            }]
        },
        "options": {
            "title": {
                "display": True,
                "text": "DNS Record Type Distribution"
            }
        }
    }
    print_success("Record type distribution chart created.")
    return chart

def track_ip_changes(domain_name, record_name, ip):
    """Track IP changes over time."""
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except Exception as e:
            logging.error(f"Failed to read IP history: {e}")
    history.append({
        'domain': domain_name,
        'record': record_name,
        'ip': ip,
        'timestamp': datetime.now().isoformat()
    })
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save IP history: {e}")

def list_all_zones_records():
    """List records for all zones concurrently."""
    domains = list_domains()
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(lambda d: (d[0], list_records(d[1])), domains)
    for domain_name, records in results:
        print(f"\nRecords for {domain_name}:")
        print(tabulate(records, headers=['Name', 'Type', 'Content', 'TTL', 'Proxied', 'ID'], tablefmt='grid'))

def schedule_auto_updates():
    """Schedule periodic auto-updates for configured records."""
    scheduler = BlockingScheduler()
    config = load_auto_update_config()
    for key, data in config.items():
        domain_name, record_name = key.split(':')
        scheduler.add_job(
            auto_update_ip,
            'interval',
            minutes=5,
            args=[data['zone_id'], data['record_id'], domain_name, record_name]
        )
    print_success("Starting scheduled auto-updates...")
    scheduler.start()

def configuration_wizard():
    """Interactive wizard to set up auto-update configuration."""
    print("Welcome to the Cloudflare DNS Configuration Wizard")
    auto_update_config = load_auto_update_config()
    domains = list_domains()
    if not domains:
        print_error("No domains found.")
        return
    print("\nAvailable Domains:")
    for i, (name, _) in enumerate(domains, 1):
        print(f"{i}. {name}")
    try:
        index = int(input("Select a domain (number): ")) - 1
        if 0 <= index < len(domains):
            domain_name, zone_id = domains[index]
            records = list_records(zone_id)
            print("\nAvailable Records:")
            for i, (name, rtype, content, _, _, rid) in enumerate(records, 1):
                print(f"{i}. {name} ({rtype}) -> {content}")
            record_index = int(input("Select a record for auto-update (number): ")) - 1
            if 0 <= record_index < len(records):
                name, rtype, _, _, _, record_id = records[record_index]
                if rtype != 'A':
                    print_error("Auto-update only supported for A records.")
                    return
                auto_update_config[f"{domain_name}:{name}"] = {'zone_id': zone_id, 'record_id': record_id}
                save_auto_update_config(auto_update_config)
                print_success(f"Auto-update enabled for {name}")
    except ValueError:
        print_error("Invalid input.")

class DNSProvider:
    """Base class for DNS providers."""
    def list_records(self, zone_id):
        raise NotImplementedError

class CloudflareProvider(DNSProvider):
    """Cloudflare DNS provider implementation."""
    def list_records(self, zone_id):
        return list_records(zone_id)

def interactive_mode():
    """Interactive mode for managing DNS records."""
    if not os.path.exists(CONFIG_FILE):
        print_error("Configuration file not found. Running setup wizard...")
        setup_wizard()
    validate_api_token()
    while True:
        domains = list_domains()
        if not domains:
            return
        print("\nAvailable Domains:")
        for i, (name, _) in enumerate(domains, 1):
            print(f"{i}. {name}")
        choice = input("\nSelect a domain (number), 'c' for config wizard, 's' for schedule updates, 'w' for setup wizard, or 'q' to quit: ")
        if choice.lower() == 'q':
            break
        elif choice.lower() == 'c':
            configuration_wizard()
        elif choice.lower() == 's':
            schedule_auto_updates()
        elif choice.lower() == 'w':
            setup_wizard()
        else:
            try:
                index = int(choice) - 1
                if 0 <= index < len(domains):
                    domain_name, zone_id = domains[index]
                    manage_domain(zone_id, domain_name)
                else:
                    print_error("Invalid selection.")
            except ValueError:
                print_error("Invalid input. Please enter a number, 'c', 's', 'w', or 'q'.")

def manage_domain(zone_id, domain_name, dry_run=False):
    """Manage DNS records for a specific domain."""
    auto_update_config = load_auto_update_config()
    while True:
        print(f"\nManaging {domain_name}")
        print("1. List records")
        print("2. Add record")
        print("3. Edit record")
        print("4. Delete record")
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
                proxied = input("Enable proxy? (y/n): ").lower() == 'y'
                add_record(zone_id, record_type, name, content, ttl, proxied, dry_run)
                if record_type == 'A' and input("Enable auto-update for this record? (y/n): ").lower() == 'y':
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
                        new_proxied = input(f"Enable proxy? (current: {proxied}) (y/n): ").lower() == 'y'
                        update_record(zone_id, record_id, rtype, name, new_content, new_ttl, new_proxied, dry_run)
                    elif choice == '5':
                        toggle_proxy(zone_id, record_id, True, dry_run)
                    elif choice == '6':
                        toggle_proxy(zone_id, record_id, False, dry_run)
                    elif choice == '7':
                        auto_update_ip(zone_id, record_id, domain_name, name, dry_run)
                        if input("Enable auto-update for this record? (y/n): ").lower() == 'y':
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
                    if input(f"Confirm deletion of {records[index][0]}? (y/n): ").lower() == 'y':
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
    
    if args.domain not in domain_map:
        print_error(f"Error: Domain {args.domain} not found.")
        sys.exit(1)
    
    zone_id = domain_map[args.domain]
    auto_update_config = load_auto_update_config()
    
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
        if input(f"Confirm deletion of record ID {args.record_id}? (y/n): ").lower() == 'y':
            delete_record(zone_id, args.record_id, args.domain, args.name, args.dry_run)
            key = f"{args.domain}:{args.name}"
            if key in auto_update_config:
                del auto_update_config[key]
                save_auto_update_config(auto_update_config)
    
    elif args.action == 'backup':
        backup_records(zone_id, args.domain)
    
    elif args.action == 'bulk-add':
        bulk_add_records(zoid, args.file, args.dry_run)
    
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
