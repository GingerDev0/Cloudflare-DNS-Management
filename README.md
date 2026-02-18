diff --git a/README.md b/README.md
index 566450592c95ce3976cfe20358085cba18ff9964..048b3444051566acfcc68cbc630bb1125f956bc5 100644
--- a/README.md
+++ b/README.md
@@ -12,50 +12,72 @@ This Python script provides a comprehensive tool for managing Cloudflare DNS rec
 - **Search and Resolve** 🔍: Search DNS records and check resolution.
 - **Statistics and Charts** 📊: Display zone statistics and generate Chart.js-compatible pie charts for record types.
 - **Dry Run** 🧪: Simulate actions without making API calls.
 - **Setup Wizard** 🧙‍♂️: Interactive configuration for Cloudflare and notification settings.
 
 ## Requirements 🛠️
 - Python 3.6+ 🐍
 - Required Python packages:
   - `requests` 📡
   - `tabulate` 📋
   - `colorama` 🎨
   - `apscheduler` ⏰
   - `dnspython` 🌍
 
 ## Installation 🚀
 1. Clone or download the script.
 2. Install dependencies:
    ```bash
    pip install requests tabulate colorama apscheduler dnspython
    ```
 3. Run the setup wizard to configure Cloudflare and notification settings:
    ```bash
    python cloudflare_dns_manager.py --setup
    ```
 
+## Quick Start ⚡
+If you just want to get running quickly:
+
+1. Install dependencies:
+   ```bash
+   pip install requests tabulate colorama apscheduler dnspython
+   ```
+2. Run setup once:
+   ```bash
+   python cloudflare_dns_manager.py --setup
+   ```
+3. List all zones and records:
+   ```bash
+   python cloudflare_dns_manager.py --action list-all
+   ```
+4. List records for one domain:
+   ```bash
+   python cloudflare_dns_manager.py --domain example.com --action list
+   ```
+
+Tip: for delete operations in command-line mode, use `--yes` to skip the confirmation prompt.
+
 ## Setting Up Cloudflare API 🔑
 To use this script, you need a Cloudflare API token with appropriate permissions. Follow these steps to create and configure the API token:
 
 1. **Log in to Cloudflare** 🌩️:
    - Go to [Cloudflare's dashboard](https://dash.cloudflare.com/) and log in to your account.
 
 2. **Navigate to API Tokens** 🛡️:
    - Click on "My Profile" in the top-right corner.
    - Select "API Tokens" from the left-hand menu.
 
 3. **Create an API Token** 🆕:
    - Click the "Create Token" button.
    - Choose the "Create Custom Token" option and click "Get Started."
 
 4. **Configure Token Permissions** ⚙️:
    - Give the token a descriptive name (e.g., "DNS Manager Token").
    - Under **Permissions**, add the following:
      - **Zone:Zone:Read** 📖 - Allows reading zone details.
      - **Zone:DNS:Edit** ✏️ - Allows managing DNS records.
    - Under **Zone Resources**, select "All zones" or specific zones you want the script to manage.
    - Optionally, set an expiration date for the token.
 
 5. **Generate and Save the Token** 💾:
    - Click "Continue to Summary" and review the permissions.
    - Click "Create Token" to generate the token.
