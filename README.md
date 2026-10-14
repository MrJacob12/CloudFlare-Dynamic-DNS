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

2. Install the required Python packages:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project directory and populate it with your CloudFlare API key:

```
CF_API_KEY="KEY"
```

4. Create a `config.json` file in the project directory. Use the provided template in the example below:

```json
{
  "email": "your-email@example.com",
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

`zone_id` and `rec_id` are optional: when missing or left as placeholders, the script looks them up automatically via the CloudFlare API. Records are only updated when the public IP actually changed.

### Public IP providers

The public IP is fetched over HTTPS from the first working provider, in order: `api.ipify.org`, `icanhazip.com`, `ifconfig.me/ip`, `ipinfo.io/ip`. The response is validated as an IPv4 address; IPv6-only replies and failures fall through to the next provider.

### Linux scheduler (cron)

A helper script installs a cron entry that runs the updater periodically:

```bash
./scheduler-linux.sh install        # create .venv, install deps, add cron entry (every 5 min)
INTERVAL_MINUTES=15 ./scheduler-linux.sh install   # custom interval (1-59)
./scheduler-linux.sh remove         # remove the cron entry
./scheduler-linux.sh run            # run one update now
```

Output is appended to `ddns.log` in the project directory. Requires `python3`, `venv` and a working `crontab`. The script can be run from any working directory.

### Docker

```bash
docker compose up -d --build
```

The container runs the updater in a loop, re-checking every `UPDATE_INTERVAL` seconds (default 300):

```bash
UPDATE_INTERVAL=900 docker compose up -d --build
```

Configuration comes from `./config.json` (mounted read-only) and `.env` (`env_file`), both relative to the project directory. Console colors are disabled automatically when output is not a terminal (e.g. Docker logs or cron).

### Contributing

If you'd like to contribute to this project, please open an issue or submit a pull request with your proposed changes.

### License

This project is licensed under the [MIT](/LICENSE) License - see the LICENSE file for details.
