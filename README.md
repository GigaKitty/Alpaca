# Alpaca
## WIP in development!!
Alpaca integrations for various tools. 

Includes: 
- Webhooks for TradingView alerts to execute orders on Alpaca. 
    - Webhooks can operate with multiple strategies to execute and manage orders
- Background functions to execute orders in realtime.

### @USE:

Export AWS credentials & docker-compose up
```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

docker compose up
```
python -m pip install awscli

curl -Lo copilot https://github.com/aws/copilot-cli/releases/latest/download/copilot-linux && chmod +x copilot && sudo mv copilot /usr/local/bin/copilot && copilot --help
The error message indicates that you're trying to assume a role from the root account. AWS does not allow root accounts to assume IAM roles. You should create an IAM user, grant that user the necessary permissions, and then use that user's credentials to assume the role.

Here's how you can create a new IAM user and grant it permissions to assume the role:

    Create a new IAM user:

    Create an access key for the new user:

This command returns an Access Key ID and Secret Access Key. Make sure to save these values as you'll need them to configure your AWS CLI.

    Grant the user permissions to assume the role. First, create a policy that allows the user to assume the role. Save the following policy in a file named assume-role-policy.json:

Replace 123456789012 with your AWS account ID.

    Create the policy in IAM:

This command returns a policy ARN.

    Attach the policy to the user:

Replace 123456789012 with your AWS account ID.

Now, you can configure yo
aws iam create-role --role-name CopilotProvisioningRole --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy --role-name CopilotProvisioningRole --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
Yes, you can schedule an AWS Copilot service to only run during weekdays using Amazon CloudWatch Events (also known as Amazon EventBridge). You can create a cron schedule expression to specify the weekdays.

Here's a step-by-step guide:

    First, deploy your service using AWS Copilot. This will create an ECS service under the hood.

    Create a CloudWatch Event rule that starts your service at the beginning of the workday. The following AWS CLI command creates a rule that triggers every weekday at 8 AM:

    Add your ECS service as a target to the rule. The following command starts the my-service service in the my-app application and my-env environment:

Replace arn:aws:ecs:us-west-2:123456789012:service/my-app-my-env-my-service with the ARN of your ECS service.

    Repeat steps 2 and 3 to create a rule that stops your service at the end of the workday. The following commands create a rule that triggers every weekday at 6 PM and stops the service:

Please note that this approach only works for services with a replication count of 1. If your service has a replication count greater than 1, you need to use a Lambda function to update the desired count of the service.

## Strategies

### app/averaging-down.py
When a trader is in a losing position and decides to buy more shares of the same stock in the hope that it will turn around, this is commonly referred to as "averaging down" or "doubling down." Averaging down is a risky strategy that involves adding to a losing position by purchasing more shares at a lower price than the initial purchase price. The goal is to reduce the average cost per share and increase the chances of eventually reaching a breakeven point or realizing a profit when the stock's price rebounds.

Here's a breakdown of averaging down:

- Initial Purchase: The trader initially buys a certain number of shares at a higher price.
- Price Decline: After the initial purchase, the stock's price starts to decline, resulting in a paper loss for the trader.
- Averaging Down: Instead of cutting their losses or selling the existing position, the trader buys additional shares at a lower price, thereby lowering the average cost per share of their entire position.
- Hope for Reversal: The trader's hope is that the stock's price will eventually turn around and rise above the new, lower average cost per share, allowing them to recover their losses or make a profit.

Averaging down can be a tempting strategy because it appears to offer a chance to recover losses without admitting defeat by selling at a loss. However, it carries significant risks:

- Losses Can Magnify: If the stock's price continues to decline, the trader's losses can become even larger because they have increased their position size.
- Tying Up Capital: Averaging down ties up more capital in a losing position, preventing the trader from deploying their funds in potentially more profitable opportunities.
- No Guarantee of a Reversal: There is no guarantee that the stock will rebound, and it could continue to decline or even become worthless.
- Psychological Stress: Averaging down can lead to emotional stress and clouded judgment, as traders become emotionally attached to their losing positions.

Averaging down should be approached with caution and should be part of a well-thought-out trading or investment plan. Traders should set clear stop-loss levels to limit potential losses and have a strategy for managing risk. It's also essential to have a plan for when to exit the position, whether it turns profitable or continues to decline. Risk management and diversification are key principles to keep in mind when considering averaging down or any trading strategy.
