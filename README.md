# Alpaca

Portable collection of microservices for Alpaca trading that deploy to AWS ECS using Copilot. Services are split into different tools and strategies for trading. Some services talk to other services, while others are standalone. The project currently uses copilot to deploy microservices so they are easy to manage and scale.

## @purpose

To create microservices that can used off the shelf with minimal effort that can be deployed via docker anywhere with minimal setup.

## Contributing

You can easily contribute or request your own bots to this project or other projects on GigaKitty for other trading platforms by creating a new service. There is a step-by-step guide in the example service or you can contact us for more info just open an issue to open a comms link.

## Application

The project consists of a single application "Alpaca" that make up the project.

## Services

AWS copilot services are broken down into microservice architecture having each it's own responsibility. The services are as follows:

### svc guidelines

- Instantly deployable and usable all three envs
  - local using `docker-compose.yml`
  - GitHub codespaces
  - AWS copilot (ECS)
- Run without intervention from trader once it's going it doesn't stop or need kicked
- Have clear documentation or at least clean code to understand implementation
- Simple micro service single use
- Minimal dependencies

🟣 Idea
🟡 WIP
🟢 Production

### 🟢 beancleaner

A cleanup service that will periodically clean up trades based on a pre-determined price and time criteria.
For instance:

- Every Friday at 13:00EST close all trades profitable over a dollar
- Every Weekday at 13:00EST close all trades losing between $0-$5

### 🟢 earnyearn

Automatic earnings report bot that consumes realtime bar data on earnings tickers upcoming or passed to process algos on. When an algo triggers it sends an order request to a webhook bot.

### 🟢 slanger

TradingView webhook processing service. This service listens for webhooks from TradingView and executes orders based on the payload. Different strategies and order types can be used to execute orders on different endpoints.

## Deploying

Local:
```docker-compose up -d```

AWS:
```copilot jkqsvc```

Codespaces:

### Prerequisites

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- [AWS Copilot](https://aws.github.io/copilot-cli/docs/getting-started/install/)
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

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

You paste this JSON into the alert settings "Message" field in TradingView. You will also need to directly edit the "Webhook URL" field in TradingView to include the name of the endpoint you want to trigger. If anyone has an automated solution to creating alerts that doesn't have an ultra high overhead or violate TradingView T&C please let know.
