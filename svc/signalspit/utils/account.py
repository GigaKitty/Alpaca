############################################################
# Gets account information
def get(data, api):
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


def get_equity(api):
    account = api.get_account()
    available_equity = account.equity
    return available_equity


def cash_size(api):
    account = api.get_account()
    return account.get["cash"]


def qty_size(api):
    account = api.get_account()
    # calculate the size based on cash_size and share price.
    qty = cash_size(api) / g.data.get["ticker"]

    return qty
