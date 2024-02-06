# Generates a unique order id based on interval and strategy coming from the webhook
def generate_order_id(data, length=10):
    """
    Creates a unique order id based on interval and strategy coming from the webhook
    There is not really input validation here and could maybe use some failover but it hasn't caused any issues to date
    """
    characters = string.ascii_lowercase + string.digits
    comment = data.get('comment').lower()
    interval = data.get('interval').lower()
    order_rand = ''.join(random.choice(characters) for _ in range(length))
    order_id = [comment, interval, order_rand]
    return "-".join(order_id)
