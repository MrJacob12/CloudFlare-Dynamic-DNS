import json, requests, os

from dotenv import load_dotenv
load_dotenv()


def get_public_ip():
    return requests.get('http://ipv4.icanhazip.com').text.strip()

def get_existing_content(hostname, type):
    response = requests.get(f'http://myexternalip.com/raw')
    if response.status_code == 200:
        return response.text.strip()

    response = requests.get(f'http://ipinfo.io/{hostname}/{type}')
    if response.status_code == 200:
        return response.json()['ip'].strip()

    return None

def update_dns_record(email, key, zone_id, rec_id, type, name, content, ttl=1, proxied=True):
    url = f'https://api.cloudflare.com/client/v4/zones?name={zone}'
    headers = {
        'X-Auth-Email': email,
        'X-Auth-Key': key,
        'Content-Type': 'application/json'
    }

    zone_response = requests.get(url, headers=headers)
    zone_id = zone_response.json()['result'][0]['id']

    hostname = f'{name}.{zone}' if name != zone else name
    url = f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={hostname}&type={type}'

    rec_response = requests.get(url, headers=headers)
    rec_id = rec_response.json()['result'][0]['id']

    payload = {
        'id': rec_id,
        'type': type,
        'name': hostname,
        'content': content,
        'ttl': ttl,
        'proxied': proxied
    }
    update_response = requests.put(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{rec_id}', headers=headers, json=payload)

    return update_response.json()['success']

def secret_handler():
    key = os.getenv('CF_API_KEY')
    return key

def config_handler():
    if not os.path.exists('config.json'):
        print('Config file not found. Please create a config.json file in the same directory as this script.')
        exit(1)
    with open('config.json', 'r') as file:
        config = json.load(file)
    email = config['email']
    key = secret_handler()
    zones = config['zones']
    return email, key, zones

if __name__ == '__main__':
    # Load parameters and records from JSON file
    email, key, zones = config_handler()
    for zone_config in zones:
        zone = zone_config['zone']
        zone_id = zone_config['zone_id']
        records = zone_config['records']

        for record in records:
            type = record['type']
            rec_id = record['rec_id']
            name = record['name']
            proxied = record['proxied']
            ttl = record.get('ttl', 1)

            public_ip = get_public_ip()
            existing_content = get_existing_content(name, type)
            success = update_dns_record(email, key, zone_id, rec_id, type, name, public_ip, ttl, proxied)

            if success:
                print(f'Record Updated: {name}.{zone}')
            else:
                print(f'Record update failed: {name}.{zone}')
