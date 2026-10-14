import ipaddress
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import colorama
import requests
from colorama import Fore, Style
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
TIMEOUT = 10

load_dotenv(BASE_DIR / '.env')

colorama.init(autoreset=True)

# Literal placeholder IDs that mean "not configured" -> trigger API lookup fallback.
PLACEHOLDER_IDS = {'', 'zone_id', 'rec_id', 'your-zone-id', 'your-record-id'}

# Public IP providers tried in order; each returns a plain-text IPv4/IPv6 address.
IP_PROVIDERS = (
    'https://api.ipify.org',
    'https://icanhazip.com',
    'https://ifconfig.me/ip',
    'https://ipinfo.io/ip',
)


def colorize(text, color):
    """Wrap text in ANSI color; plain text when NO_COLOR is set."""
    if os.environ.get('NO_COLOR'):
        return text
    return f'{color}{text}{Style.RESET_ALL}'


def log(message, color=None):
    """Print a message prefixed with [HH:MM - DD.MM.YYYY], optionally colored."""
    stamp = datetime.now().strftime('%H:%M - %d.%m.%Y')
    line = f'[{stamp}]: {message}'
    print(colorize(line, color) if color else line)


def usable_id(value):
    """Return the config ID only when it is a real value, else None for lookup fallback."""
    return value if value not in PLACEHOLDER_IDS else None


def get_public_ip():
    """Fetch a valid public IPv4 from the first working provider."""
    failures = []
    for provider in IP_PROVIDERS:
        try:
            response = requests.get(provider, timeout=TIMEOUT)
            response.raise_for_status()
            ip = response.text.strip()
            parsed = ipaddress.ip_address(ip)
            if parsed.version != 4:
                raise RuntimeError(f'provider returned IPv6 ({ip}); only IPv4 A records are supported')
            return ip
        except Exception as error:
            failures.append(f'{provider}: {error}')
    raise RuntimeError('All IP providers failed: ' + '; '.join(failures))


def cloudflare_headers(email, key):
    return {
        'X-Auth-Email': email,
        'X-Auth-Key': key,
        'Content-Type': 'application/json',
    }


class CloudflareAPIError(RuntimeError):
    """Raised for any non-200 response or an API-level (success=false) failure."""

    def __init__(self, method, url, status, errors=None, retry_after=None, body=None):
        self.method = method
        self.url = url
        self.status = status
        details = []
        if errors:
            details.append(repr(errors))
        elif body:
            details.append(repr(body[:200]))
        if retry_after:
            details.append(f'retry after {retry_after}s')
        suffix = f' - {"; ".join(details)}' if details else ''
        super().__init__(f'Cloudflare API error: {method} {url} -> HTTP {status}{suffix}')


def api_call(method, url, email, key, **kwargs):
    """Perform a Cloudflare API request; raise CloudflareAPIError on any failure."""
    response = requests.request(method, url, headers=cloudflare_headers(email, key), timeout=TIMEOUT, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if response.status_code != 200 or not isinstance(payload, dict) or not payload.get('success'):
        raise CloudflareAPIError(
            method,
            url,
            response.status_code,
            errors=payload.get('errors') if isinstance(payload, dict) else None,
            retry_after=response.headers.get('Retry-After'),
            body=None if isinstance(payload, dict) else response.text,
        )
    return payload


def get_zone_id(email, key, zone):
    payload = api_call('GET', f'https://api.cloudflare.com/client/v4/zones?name={zone}', email, key)
    result = payload.get('result') or []
    if not result:
        raise RuntimeError(f'Zone not found: {zone}')
    return result[0]['id']


def get_record_id(email, key, zone_id, hostname, record_type):
    payload = api_call(
        'GET',
        f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={hostname}&type={record_type}',
        email,
        key,
    )
    result = payload.get('result') or []
    if not result:
        raise RuntimeError(f'DNS record not found: {hostname} ({record_type})')
    return result[0]['id']


def get_record_content(email, key, zone_id, rec_id):
    payload = api_call(
        'GET', f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{rec_id}', email, key
    )
    result = payload.get('result') or {}
    return result.get('content')


def update_dns_record(email, key, zone_id, rec_id, record_type, name, zone, content, ttl=1, proxied=True):
    """Update one DNS record to `content`; returns 'unchanged', 'updated' or 'failed'."""
    zone_id = usable_id(zone_id) or get_zone_id(email, key, zone)
    hostname = name if name == zone else f'{name}.{zone}'
    rec_id = usable_id(rec_id) or get_record_id(email, key, zone_id, hostname, record_type)

    existing = get_record_content(email, key, zone_id, rec_id)
    if existing == content:
        return 'unchanged'

    payload = {
        'type': record_type,
        'name': hostname,
        'content': content,
        'ttl': ttl,
        'proxied': proxied,
    }
    update_response = api_call(
        'PUT', f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{rec_id}', email, key, json=payload
    )
    return 'updated' if update_response.get('success') else 'failed'


def config_handler():
    config_path = BASE_DIR / 'config.json'
    if not config_path.exists():
        log(f'Config file not found: {config_path}', Fore.RED)
        sys.exit(1)
    with open(config_path, 'r') as file:
        try:
            config = json.load(file)
        except json.JSONDecodeError as error:
            log(f'Invalid JSON in {config_path}: {error}', Fore.RED)
            sys.exit(1)
    email = config.get('email')
    key = os.getenv('CF_API_KEY')
    zones = config.get('zones', [])
    if not email or not key:
        log('Missing "email" in config.json or CF_API_KEY in .env', Fore.RED)
        sys.exit(1)
    return email, key, zones


if __name__ == '__main__':
    email, key, zones = config_handler()
    if not zones:
        log('No zones configured in config.json.', Fore.YELLOW)
        sys.exit(1)

    try:
        public_ip = get_public_ip()
    except Exception as error:
        log(f'Failed to fetch public IP: {error}', Fore.RED)
        sys.exit(1)

    failures = 0
    for zone_config in zones:
        zone = zone_config['zone']
        zone_id = zone_config.get('zone_id', '')
        records = zone_config['records']

        for record in records:
            record_type = record['type']
            rec_id = record.get('rec_id', '')
            name = record['name']
            proxied = record.get('proxied', True)
            ttl = record.get('ttl', 1)

            try:
                status = update_dns_record(email, key, zone_id, rec_id, record_type, name, zone, public_ip, ttl, proxied)
                if status == 'unchanged':
                    log(f'Record unchanged: {name}.{zone}', Fore.CYAN)
                elif status == 'updated':
                    log(f'Record Updated: {name}.{zone}', Fore.GREEN)
                else:
                    log(f'Record update failed: {name}.{zone}', Fore.RED)
                    failures += 1
            except Exception as error:
                log(f'Record update failed: {name}.{zone} - {error}', Fore.RED)
                failures += 1

    if failures:
        sys.exit(1)