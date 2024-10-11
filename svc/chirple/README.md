Chirple is chirpy and likes to say things from a redis channel stream. It will output audio to the host device's speakers. For instance trade updates, or other alerts.

## Test
To test if it's listening to the redis channel, you can use the redis-cli to publish a message to the channel. The message should be a string that chirple can say. For instance: 
```
redlis-cli
PUBLISH chirple "sell 100 shares of AAPL"
```
If it's all hooked up properly to the host then it will output the message to the speakers. This relies on however a linux host that is running pulse server and has the speakers connected to it.

#TODO make chirple an environment specific service with different accents for each environment.