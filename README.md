# Alpaca
Portable collection of tools for Alpaca trading that deploy to AWS ECS using Copilot.

## Webhooks/API
Endpoints for TradingView webhooks to execute orders on Alpaca. Each endpoint is a different strategy that can be used to execute orders.

## Tasks
Background tasks that execute orders in realtime. Uses AWS SQS with Celery to execute tasks. Some tasks are just background tasks that run continuously, while others are triggered on a schedule.

## Deploying

### Prerequisites

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- [AWS Copilot](https://aws.github.io/copilot-cli/docs/getting-started/install/)
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Python 3.8](https://www.python.org/downloads/)
- [Pipenv](https://pipenv.pypa.io/en/latest/install/#installing-pipenv)

### TradingView WebHook Alerts
These are the alerts that are configured in TradingView to send webhooks to the API. The alerts are configured to send a POST request to the API with the following JSON payload.
```{
    "action": "{{strategy.order.action}}",
    "alert_message": "{{strategy.order.alert_message}}",
    "close": "{{close}}",
    "comment": "{{strategy.order.comment}}",
    "contracts": "{{strategy.order.contracts}}",
    "exchange": "{{exchange}}",
    "high": "{{high}}",
    "id": "{{strategy.order.id}}",
    "interval": "{{interval}}",
    "low": "{{low}}",
    "open": "{{open}}",
    "position_size": "{{strategy.position_size}}",
    "prev_market_position": "{{strategy.prev_market_position}}",
    "prev_market_position_size": "{{strategy.prev_market_position_size}}",
    "price": "{{strategy.order.price}}",
    "ticker": "{{ticker}}",
    "time": "{{time}}",
    "signature": "REPLACE_ME"
}
```
the `signature` field is a HMAC signature of the payload using the secret key. The secret key is stored in AWS Secrets Manager and is used to verify the payload is coming from TradingView.

You paste this JSON into the alert settings "Message" field in TradingView. You will also need to directly edit the "Webhook URL" field in TradingView to include the name of the endpoint you want to trigger. The URL should look like this: `https://api.example.com/webhooks/endpoint-name/`. The endpoint name is the name of the endpoint you want to trigger. For example, if you want to trigger the `buy` endpoint, the URL would be `https://api.example.com/webhooks/buy/`.
