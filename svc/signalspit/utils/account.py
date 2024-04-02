def get_equity(api):
    account = api.get_account()
    print(account)
    available_equity = account.equity
    print(f"Available Equity: {available_equity}")
