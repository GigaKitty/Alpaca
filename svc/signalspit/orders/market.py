@app.route('/market', methods=['POST'])
def order():
    """
    Places a simple market order or BUY or SELL based on TradingView WebHook
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    data = data.sync_time(request.json)
    
    if (utils.auth.validate_signature(data) == True):
        try:
            action = data.get('action')
            contracts = data.get('contracts')
            order_id = utils.order.generate_order_id(data, 10)
            ticker = data.get('ticker')
            time_in_force = "ioc" # supports ioc|gtc

            print(f"Data: {data}")

            #  Setup Price
            price = utils.calc.price(data.get('price'))

            # check if there's a current position
            position = utils.position.get(data)
            ##########################################
            # if we have a position then we need to figure out what to do with it.
            if position is not False:
                ap = utils.position.anal(data, position)
            else:
                ap = True
    
            if ap is True:
                print(f"Placing {order_id} {action} order for {contracts} contracts on ${ticker} @ ${price}USD ")
                market_order_data = MarketOrderRequest(
                    symbol=ticker,
                    qty=contracts,
                    side=action,
                    time_in_force=TimeInForce.IOC,
                    client_order_id=order_id
                )
                print(market_order_data)
                market_order = api.submit_order(
                    order_data=market_order_data
                )
                print(market_order)
            ############################################################################
            response_data = {"message": "Webhook received and processed successfully"}

            return jsonify(response_data), 200

        except Exception as e:

            error_message = {"error": "Failed to process webhook request"}

            return jsonify(error_message), 400
