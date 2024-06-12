############################################################
# Gets account information
def get_account(data, api):
    """
    Checks the position of the current ticker
    """
    try:
        acc = api.get_account()
        if acc is None:
            return False
        else:
            return acc
    except Exception as e:
        return False


def get_cash(data, api):
    account = api.get_account()
    cash = account.cash
    print(cash)

    if cash > 0:
        return cash
    else:
        return False


def cash_size(data, api):
    account = api.get_account()
    return account.get["cash"]


def qty_size(data, api):
    # account = api.get_account()
    # calculate the size based on cash_size and share price.
    qty = cash_size(api) / g.data.get["ticker"]

    return qty
