# Alpaca

Portable collection of microservices for Alpaca trading that deploy to AWS ECS using Copilot. Services are split into different tools and strategies for trading. Some services talk to other services, while others are standalone. The project currently uses copilot to deploy microservices so they are easy to manage and scale.

## Application

The project consists of a single application "Alpaca" that make up the project.

## Services

AWS copilot services are broken down into microservice architecture having each it's own responsibility. The services are as follows:

### pacapredictor

A service that uses a machine learning model to predict the price of a stock. The model is trained on historical data and uses a LSTM neural network to make predictions. The service is used to predict the price of a stock at a given time and is used to make trading decisions.

### queuecria

A service that listens to a queue and executes worker tasks. It is used to execute tasks that are triggered by a schedule or by a queue. It's used for common tasks like cron jobs or background tasks and is used as a worker service to execute tasks.

### redditspreadit

Scans reddit and performs a simple sentiment scoring to buy/sell assets.

### scalapaca

Service that produces HFTesque scalp trades.

### sentimentsheperd

Uses chatgpt to analyze sentiment of news articles and social media posts. These are fed via websockets to deliver realtime data for the bot to score and ultimately make trading decisions based on the feeds coming in.

### signalspit

TradingView webhook processing service. This service listens for webhooks from TradingView and executes orders based on the payload. Different strategies and order types can be used to execute orders on different endpoints.

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
