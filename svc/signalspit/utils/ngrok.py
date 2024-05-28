import os
from pyngrok import ngrok

init():
    ngrok_auth_token = os.getenv('NGROK_AUTH_TOKEN')
    ngrok_domain = os.getenv('NGROK_DOMAIN')

    ngrok.set_auth_token(ngrok_auth_token)
    url = ngrok.connect(5000, subdomain=ngrok_domain)
    print(f' * Ngrok tunnel available at {url}')