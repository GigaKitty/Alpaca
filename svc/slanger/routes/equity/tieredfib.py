

from flask import Blueprint, request, jsonify, g
from alpaca.trading.requests import LimitOrderRequest, TakeProfitRequest, MarketOrderRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from config import api, app
from utils import position

equity_tieredfib = Blueprint('equity_tieredfib', __name__)

def fibonacci_sequence(n):
    fib_sequence = [1, 2]
    while len(fib_sequence) < n:
        fib_sequence.append(fib_sequence[-1] + fib_sequence[-2])
    return fib_sequence[:n]

def define_fibonacci_tiered_strategy(base_price, tiers, base_quantity, price_increment):
    fib_sequence = fibonacci_sequence(tiers)
    orders = []
    for i in range(tiers):
        buy_price = float(base_price) + (fib_sequence[i] * price_increment)
        sell_price = float(base_price) - (fib_sequence[i] * price_increment)
        quantity = base_quantity * fib_sequence[i]
        orders.append({
            'buy_price': round(buy_price, 2),
            'sell_price': round(sell_price, 2),
            'quantity': round(quantity)
        })
    return orders


@equity_tieredfib.route("/tieredfib", methods=["POST"])
def order():
    # Define the tiered order strategy based on Fibonacci sequence
    tiers=5  # Number of tiers
    base_quantity = 1  # Base quantity for the first tier
    price_increment = 0.1  # Price increment per Fibonacci level

    if g.data.get("pos") is not False and g.data.get("side") != g.data.get("action"):
        app.logger.debug("Closing Position: %s", g.data.get("ticker"))
        try:
            api.close_position(g.data.get("ticker"))
            position.wait_position_close(g.data, api)
        except Exception as e:
            app.logger.error(f"Failed to close position for {g.data.get('ticker')}: {e}")
    

    orders = define_fibonacci_tiered_strategy(g.data.get("price"), tiers, base_quantity, price_increment)

    app.logger.debug(orders)

    # Place tiered buy orders with take profit and stop loss
    try: 
        market_order = MarketOrderRequest(
            symbol=g.data.get("ticker"),
            qty=g.data.get("qty"),
            side=OrderSide.BUY,
            time_in_force=TimeInForce.GTC,
        )
        api.submit_order(market_order)
        app.logger.debug(f"Placed market order for {g.data.get('qty')} shares")
    except Exception as e:
        app.logger.error(f"Failed to place market order for {g.data.get('ticker')}: {e}")

    for order in orders:
        try: 
            # Primary limit order
            buy_order = LimitOrderRequest(
                symbol=g.data.get("ticker"),
                qty=g.data.get("qty"),
                side=OrderSide.BUY,
                type="limit",
                time_in_force=TimeInForce.GTC,
                limit_price=order['buy_price']
            )
            api.submit_order(buy_order)
            app.logger.debug(f"Placed buy order for {order['quantity']} shares at ${order['buy_price']}")

            # # Take profit order
            # take_profit_order = TakeProfitRequest(
            #     symbol=g.data.get("ticker"),
            #     qty=g.data.get("qty"),
            #     side=OrderSide.SELL,
            #     type="limit",
            #     time_in_force=TimeInForce.GTC,
            #     limit_price=order['sell_price']
            # )
            # api.submit_order(take_profit_order)
            # app.logger.debug(f"Placed take profit order for {order['quantity']} shares at ${order['sell_price']}")

            # # Stop loss order
            # stop_loss_price = order['buy_price'] - (order['buy_price'] * 0.05)  # Example: 5% stop loss
            # stop_loss_order = StopLossRequest(
            #     symbol=g.data.get("ticker"),
            #     qty=g.data.get("qty"),
            #     side=OrderSide.SELL,
            #     type="stop",
            #     time_in_force=TimeInForce.GTC,
            #     stop_price=round(stop_loss_price, 2)
            # )
            # api.submit_order(stop_loss_order)
            # app.logger.debug(f"Placed stop loss order for {order['quantity']} shares at ${round(stop_loss_price, 2)}")
        except Exception as e:
            app.logger.error(f"Failed to place order for {g.data.get('ticker')}: {e}")

    return jsonify({"message": "Orders placed successfully", "orders": orders})