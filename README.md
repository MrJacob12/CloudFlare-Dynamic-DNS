# CloudFlare Dynamic DNS Updater

This Python script allows you to update CloudFlare DNS records with the current public IP address. It supports multiple zones and records within each zone.

## Getting Started

### Prerequisites

Before running the script, you'll need:

- Python 3.x installed on your system
- Access to the CloudFlare API with a valid API key and email
- A configuration file (`config.json`) with your CloudFlare account information and the zones/records you want to update

### Installation

1. Clone the repository to your local machine:

```bash
git clone https://github.com/MrJacob12/CloudFlare-Dynamic-DNS.git
```
2. Create a config.json file in the project directory and populate it with your CloudFlare account information and the zones/records you want to update. Use the provided template in the example below:
```json
{
    "email": "your-email@example.com",
    "key": "your-cloudflare-api-key",
    "zones": [
        {
            "zone": "example.com",
            "zone_id": "your-zone-id",
            "records": [
                {
                    "type": "A",
                    "rec_id": "your-record-id",
                    "name": "api",
                    "proxied": true,
                    "ttl": 1
                }
            ]
        }
    ]
}

```
### Contributing
If you'd like to contribute to this project, please open an issue or submit a pull request with your proposed changes.

### License
This project is licensed under the [MIT](/LICENSE) License - see the LICENSE file for details.
