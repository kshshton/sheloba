import os

import requests

domain = os.getenv('TARGET_DOMAIN')
url = os.getenv('TRAFFIC_API_URL')
auth_token = os.getenv('TRAFFIC_AUTH_TOKEN')

headers = {
    'accept': 'application/json, text/plain, */*',
    'authorization': auth_token,
}

params = {
    'domain': domain,
}

response = requests.get(url, params=params, headers=headers)
json = response.json()

print({
    'domain': json['domain'],
    'traffic': json['traffic'],
})
