from flask import Blueprint, request, jsonify, g
from alpaca.trading.requests import (
    LimitOrderRequest,
    TakeProfitRequest,
    MarketOrderRequest,
    StopLossRequest,
    GetOrdersRequest,
)
from alpaca.trading.enums import QueryOrderStatus
from alpaca.trading.enums import OrderSide, TimeInForce
from config import api, app
from utils import position

# @TODO: cleanup
equity_tieredfiblimit = Blueprint("equity_tieredfiblimit", __name__)


def fibonacci_sequence(n):
    """
    - Generates a Fibonacci sequence of n numbers
    - The sequence starts with 1, 2
    - Each subsequent number is the sum of the two preceding numbers
    - The sequence is truncated to n numbers
    - Returns the Fibonacci sequence
    """
    fib_sequence = [1, 2]
    while len(fib_sequence) < n:
        fib_sequence.append(fib_sequence[-1] + fib_sequence[-2])
    return fib_sequence[:n]


def define_fibonacci_tiered_strategy(base_price, tiers, base_quantity, price_increment):
    """
    - Defines a tiered Fibonacci strategy based on the base price, number of tiers, base quantity, and price increment
    - Generates a Fibonacci sequence based on the number of tiers
    - Calculates the buy and sell prices for each tier based on the Fibonacci sequence
    - Returns a list of orders with buy price, sell price, and quantity for each tier
    - Example: define_fibonacci_tiered_strategy(100, 5, 10, 0.1)
    """
    fib_sequence = fibonacci_sequence(tiers)
    orders = []
    for i in range(tiers):
        buy_price = float(base_price) - (fib_sequence[i] * price_increment)
        sell_price = float(base_price) + (fib_sequence[i] * price_increment)
        quantity = base_quantity * fib_sequence[i]
        orders.append(
            {
                "buy_price": round(buy_price, 2),
                "sell_price": round(sell_price, 2),
                "quantity": round(quantity),
            }
        )
    return orders


def close_all_orders_and_position(symbol):
    """
    - Close all open orders and position for the specified symbol
    - Cancel all open orders for the symbol
    - Close the position for the symbol
    - Returns True if the position was closed successfully, False otherwise
    - Example: close_all_orders_and_position('AAPL')
    """
    if g.data.get("pos") is not False and g.data.get("side") != g.data.get("action"):
        try:
            api.close_position(g.data.get("ticker"))
            position.wait_position_close(g.data, api)
        except Exception as e:
            app.logger.error(
                f"Failed to close position for {g.data.get('ticker')}: {e}"
            )
        try:
            get_orders_data = GetOrdersRequest(
                status=QueryOrderStatus.OPEN,
                limit=100,
                symbols=[symbol],  # Filter by the specific ticker
                nested=True,  # show nested multi-leg orders
            )

            open_orders = api.get_orders(filter=get_orders_data)
            app.logger.debug(f"Open Orders: {open_orders}")

            for order in open_orders:
                try:
                    api.cancel_order_by_id(order.id)
                    print(
                        f"Successfully canceled order ID: {order.id}, Symbol: {order.symbol}, Qty: {order.qty}"
                    )
                except Exception as e:
                    print(f"Failed to cancel order ID: {order.id} - Error: {e}")
        except Exception as e:
            app.logger.error(
                f"Failed to cancel open orders for {g.data.get('ticker')}: {e}"
            )

        app.logger.debug("Closing Position: %s", g.data.get("ticker"))

        return True


@equity_tieredfiblimit.route("/tieredfiblimit", methods=["POST"])
def order():
    """
    - Places a tiered Fibonacci limit order based on WebHook data
    - Places a market order for the base quantity
    - Places limit orders for each Fibonacci tier with buy and sell prices
    - Example: tieredfiblimit(100, 5, 10, 0.1)
    """
    # Define the tiered order strategy based on Fibonacci sequence
    tiers = 5  # Number of tiers
    price_increment = 0.1  # Price increment per Fibonacci level

    close = close_all_orders_and_position(g.data.get("ticker"))

    if close is True:
        return jsonify({"message": "Closed all open orders and position"})

    orders = define_fibonacci_tiered_strategy(
        g.data.get("price"), tiers, g.data.get("qty"), price_increment
    )

    app.logger.debug(orders)
    try:
        market_order = MarketOrderRequest(
            symbol=g.data.get("ticker"),
            qty=g.data.get("qty"),
            side=g.data.get("action"),
            time_in_force=TimeInForce.GTC,
        )
        api.submit_order(market_order)
        app.logger.debug(f"Placed market order for {g.data.get('qty')} shares")
    except Exception as e:
        app.logger.error(
            f"Failed to place market order for {g.data.get('ticker')}: {e}"
        )

    for order in orders:
        try:
            # Primary limit order
            buy_order = LimitOrderRequest(
                symbol=g.data.get("ticker"),
                qty=order["quantity"],
                side=g.data.get("action"),
                type="limit",
                time_in_force=TimeInForce.DAY,
                limit_price=order["buy_price"],
            )
            api.submit_order(buy_order)
            app.logger.debug(
                f"Placed buy order for {order['quantity']} shares at ${order['buy_price']}"
            )

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
