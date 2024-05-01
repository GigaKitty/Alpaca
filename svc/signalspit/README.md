Application


copilot/signalspit/6d98c6 [2024-04-30 15:49:15,505] DEBUG in main: Market Data: symbol='TPIC' qty=161.0 notional=None side=<OrderSide.SELL: 'sell'> type=<OrderType.MARKET: 'market'> time_in_force=<TimeInForce.IOC: 'ioc'> order_class=None extended_hours=None client_order_id='macd-earnyearn-1m-ap8xrmjmnb' take_profit=None stop_loss=None
copilot/signalspit/6d98c6 [2024-04-30 15:49:15,514] ERROR in main: Error processing request: {"available":"0","code":40310000,"existing_qty":"368","held_for_orders":"368","message":"insufficient qty available for order (requested: 161, available: 0)","symbol":"TPIC"}
copilot/signalspit/6d98c6 10.0.0.158 - - [30/Apr/2024 15:49:15] "POST /market HTTP/1.1" 400 -