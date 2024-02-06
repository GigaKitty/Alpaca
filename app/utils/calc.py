from decimal import Decimal


# Calculates the price based on the price
def price(price):
    """
    Convert to decimal obviously
    """
    return Decimal(price)

# Calculates the limit price based on the price
def limit_price(price):
    """
    @TODO: make the arg calc the tolerance
    """
    return float(price) * 0.998

# Calculates the profit price based on the price
def profit_price(price):
    """
    @TODO: make the arg calc the tolerance
    """
    return float(price) * 1.001

# Calculates the stop price based on the price
def stop_price(price):
    """
    @TODO: make the arg calc the tolerance
    """
    return float(price) * 0.999

# Calculates the buying power for the account
def buying_power():
    # Get our account information.
    account = api.get_account()
    
    # Check if our account is restricted from trading.
    if account.trading_blocked:
        print('Account is currently restricted from trading.')

    # Check how much money we can use to open new positions.
    print('${} is available as buying power.'.format(account.buying_power))
    
    return account.buying_power