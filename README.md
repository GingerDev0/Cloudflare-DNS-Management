# Cloudflare DNS Management Script

This Python script provides a comprehensive tool for managing Cloudflare DNS records, including support for dynamic IP updates, notifications, and bulk operations. It can be used in both interactive and command-line modes.

## Features
- **Interactive Mode**: Manage DNS records through an interactive menu.
- **Command-line Mode**: Perform operations via command-line arguments.
- **Auto-update IP**: Automatically update DNS records with the current public IP.
- **Notifications**: Send email and Discord notifications for DNS changes.
- **Bulk Operations**: Add multiple DNS records from a JSON file.
- **Backup**: Save DNS records to a JSON file.
- **Search and Resolve**: Search DNS records and check resolution.
- **Statistics and Charts**: Display zone statistics and generate Chart.js-compatible pie charts for record types.
- **Dry Run**: Simulate actions without making API calls.
- **Setup Wizard**: Interactive configuration for Cloudflare and notification settings.

## Requirements
- Python 3.6+
- Required Python packages:
  - `requests`
  - `tabulate`
  - `colorama`
  - `apscheduler`
  - `dnspython`

## Installation
1. Clone or download the script.
2. Install dependencies:
   ```bash
   pip install requests tabulate colorama apscheduler dnspython
   ```
3. Run the setup wizard to configure Cloudflare and notification settings:
   ```bash
   python cloudflare_dns_manager.py --setup
   ```

## Configuration
The script uses the following configuration files:
- `cloudflare_config.json`: Stores Cloudflare API token, account ID, and notification settings.
- `auto_update_config.json`: Stores settings for auto-updating DNS records.
- `ip_cache.json`: Caches the public IP address.
- `ip_history.json`: Tracks IP changes over time.
- `dns_change_history.log`: Logs DNS changes.
- `cloudflare_dns.log`: Logs script activity.

## Usage

### Interactive Mode
Run the script without arguments to enter interactive mode:
```bash
python cloudflare_dns_manager.py
```
Follow the prompts to manage domains, list records, add/edit/delete records, and configure auto-updates.

### Command-line Mode
Use command-line arguments to perform specific actions. Examples:

- **List Records**:
  ```bash
  python cloudflare_dns_manager.py --domain example.com --action list
  ```

- **Add Record**:
  ```bash
  python cloudflare_dns_manager.py --domain example.com --action add --type A --name www --content 192.0.2.1 --ttl 300 --proxied
  ```

- **Edit Record**:
  ```bash
  python cloudflare_dns_manager.py --domain example.com --action edit --record-id <record_id> --content 192.0.2.2 --ttl 600
  ```

- **Delete Record**:
  ```bash
  python cloudflare_dns_manager.py --domain example.com --action delete --record-id <record_id> --name www
  ```

- **Backup Records**:
  ```bash
  python cloudflare_dns_manager.py --domain example.com --action backup
  ```

- **Bulk Add Records**:
  ```bash
  python cloudflare_dns_manager.py --domain example.com --action bulk-add --file records.json
  ```

- **Auto-update IP**:
  ```bash
  python cloudflare_dns_manager.py --domain example.com --action auto-update-ip --record-id <record_id> --name www --auto-update-ip
  ```

- **Search Records**:
  ```bash
  python cloudflare_dns_manager.py --domain example.com --action search --search-term www
  ```

- **Check Resolution**:
  ```bash
  python cloudflare_dns_manager.py --domain example.com --action resolve --name www.example.com --type A
  ```

- **Show Zone Stats**:
  ```bash
  python cloudflare_dns_manager.py --domain example.com --action stats
  ```

- **Create Record Type Chart**:
  ```bash
  python cloudflare_dns_manager.py --domain example.com --action chart
  ```

- **List All Zones and Records**:
  ```bash
  python cloudflare_dns_manager.py --action list-all
  ```

### Setup Wizard
Run the setup wizard to configure Cloudflare and notification settings:
```bash
python cloudflare_dns_manager.py --setup
```

### Auto-update Scheduling
To enable periodic auto-updates for configured records:
```bash
python cloudflare_dns_manager.py
```
Select the "schedule updates" option in interactive mode.

## JSON File Format for Bulk Add
Example `records.json` for bulk adding records:
```json
[
    {
        "type": "A",
        "name": "www",
        "content": "192.0.2.1",
        "ttl": 300,
        "proxied": false
    },
    {
        "type": "CNAME",
        "name": "blog",
        "content": "example.com",
        "ttl": 300,
        "proxied": true
    }
]
```

## Logging
- **Script Logs**: Saved to `cloudflare_dns.log`.
- **DNS Change Logs**: Saved to `dns_change_history.log`.
- **IP History**: Saved to `ip_history.json`.

## Notifications
- **Email**: Configured via the setup wizard (SMTP server, port, credentials).
- **Discord**: Configured via the setup wizard (Webhook URL).
Notifications are sent for DNS record changes (add, update, delete, proxy toggle, auto-update).

## Testing
The script includes a basic unit test for checking public IP retrieval:
```bash
python -m unittest cloudflare_dns_manager.py
```

## Notes
- Ensure the Cloudflare API token has the necessary permissions (DNS Edit, Zone Read).
- The `--dry-run` flag simulates API calls without making changes.
- Auto-update is only supported for A records.
- Proxy status is only supported for A and CNAME records.

## License
This project is licensed under the MIT License.
