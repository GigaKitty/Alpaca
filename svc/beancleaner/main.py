# Beancleaner is a service that cleans up old beans left from Alpacka.
# This is called the bean cleaner because Alpaca poops are called beans.
# We don't like beans, so we clean them up. We don't like losses, so we clean them up.
# It's purppose is to cleanup old trades that aren't in ideal positions.
#
#
# get current positions
# open websocket to each symbol
# monitor the price of each symbol
# when it hits a positive mark, close the position
# if it's in a really bad spot we need to  weight considerations sucha as pps, future price, etc. to see if we can wiggle out of this shitty position
#
#
#
# Take the smallest loss possible and clean it up.
# Part of the point of this service is to free up capital for better trades.
# It's also to be stubborn and not take a loss, but to take the smallest loss possible.
# which can end up being a really terrible idea.
# Use only in the most dire of situations.
# Or if we think it will work to cleanup a lot of smaller losses.
#
#
# Get the lowest fill price
# calculate how many shares we have to buy from the current price to break even
# if those shares and price etc. work out to less than a certain risk facter then we buy and then we exit
# # Given values
original_purchase_price = 50  # Original purchase price per share
current_price = 40  # Current price per share
current_shares = 100  # Number of shares currently owned
target_average_price = original_purchase_price  # Target average price to break even

# Calculate total investment
total_investment = original_purchase_price * current_shares

# Calculate additional shares needed
additional_shares = (total_investment - (target_average_price * current_shares)) / (
    target_average_price - current_price
)

additional_shares


# Correcting the logic to calculate additional shares needed to adjust the average cost

# Let's assume we want to calculate how many shares need to be bought at $40
# to lower the average cost without specifying a new target average price.

# For simplicity, let's find out how buying additional shares at $40 affects the average cost.

# We know:
# - total_investment so far
# - current_shares owned
# - new_price to buy additional shares

# We aim to find a formula that directly solves for additional shares needed to achieve a specific new average cost.
# However, since we didn't specify a new average, let's calculate a general scenario
# of how additional shares at the new price affect the average cost.

# Let's manually set an example of buying 50 additional shares and see the new average cost.
additional_shares_example = 50  # Example additional shares to buy

# New total investment after buying additional shares
new_total_investment = total_investment + (additional_shares_example * current_price)

# New total shares after buying additional
new_total_shares = current_shares + additional_shares_example

# New average cost per share
new_average_cost = new_total_investment / new_total_shares

new_average_cost
