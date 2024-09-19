VolatilityVultre is a screening service which queries the top active stocks and adds them to redis.

That list information can be used by other services.

Once list is created the symbols are added to redis and also the websocket service so that the data can be monitored and ta can be applied.

https://docs.alpaca.markets/reference/mostactives-1
https://docs.alpaca.markets/reference/movers-1