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


python -m pip install awscli

curl -Lo copilot https://github.com/aws/copilot-cli/releases/latest/download/copilot-linux && chmod +x copilot && sudo mv copilot /usr/local/bin/copilot && copilot --help


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

Now, you can configure y
aws iam create-role --role-name CopilotProvisioningRole --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy --role-name CopilotProvisioningRole --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
