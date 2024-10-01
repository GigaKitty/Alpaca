import requests
import os

# Replace with your LIFX API token
LIFX_API_TOKEN = os.getenv("LIFX_API_TOKEN")

# LIFX API endpoint to toggle the lights
url = 'https://api.lifx.com/v1/lights/all/toggle'

# Set up the headers with your API token
headers = {
    "Authorization": f"Bearer {LIFX_API_TOKEN}"
}

# Make the POST request to toggle the lights
response = requests.post(url, headers=headers)

# Check the response status
if response.status_code == 200:
    print("Lights toggled successfully!")
else:
    print(f"Failed to toggle lights: {response.status_code}")