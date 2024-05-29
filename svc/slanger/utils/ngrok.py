import os
from pyngrok import ngrok


def main():
    ngrok_auth_token = os.getenv("NGROK_AUTH_TOKEN")
    ngrok_domain = os.getenv("NGROK_DOMAIN")

    ngrok.set_auth_token(ngrok_auth_token)
    url = ngrok.connect(5000, hostname=ngrok_domain, bind_tls=True)
    print(f" * Ngrok tunnel available at {url}")
