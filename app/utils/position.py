# Gets currently open position for ticker
def get(data):
    """
    Checks the position of the current ticker
    """
    try:
        return api.get_open_position(data.get('ticker'))
    except Exception as e:
        return False

def anal(data, position):
    """
    Gives the hook an opportunity to justify the order or not.
    Basically if we're already in a position and there's no profit.
    Then stay in position but buy more at same side and don't switch.

    If there's no profit and the action isn't the same then we skip for same side trades.
    """
    """
    profit returns a +/- number
    """
    profit = float(position.unrealized_pl)
    # make position.side lowercase for comparison with action
    side = position.side.lower()

    print(float(position.unrealized_pl))
    print(f"Profit: {profit}")
    print(f"Position: {position}")

    # match naming convention of action
    if data.get('action') == 'buy':
        action = 'long'
    else:
        action = 'short'

    # if we're in a position and there's no profit then we need to buy more  
    if (profit <= 0 and side == action):
        print(position.unrealized_pl)
        print("Buy more to creep!")
        return True
    # if we're in a position and there's no profit and the action is not the same to side then we skip
    elif (profit <= 0 and side != action):
        print(position.unrealized_pl)
        print("Skip")
        return False
    # if we're in a position and there's profit and the action is not the same to side then we close and continue
    elif (profit >= 1 and side != action):
        print('Close & Continue')
        api.close_position(data.get('ticker'))
        print('Closed positions')
        return True
    # all else return true
    else:
        print("Continue")
        return True

def close_profitable():
    """
    Checks all profitable open positions and closes them
    """
    positions = api.list_positions()
    for position in positions:
        if position.unrealized_pl > 10:
            print(f"Closing {position.symbol} for {position.unrealized_pl}")
            api.close_position(position.symbol)
