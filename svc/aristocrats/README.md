Aristocrats

Service collects the dividend aristocrats tickers and saves them into redis as a list.
This list can then be used in various other services which can make determinations of what to do with an asset.
For instance you can invest on a large interval using an indicator that sends a webhook to slanger for a long term investment strategy which will DCA into positions over time.

Meant to be a very simple service which merely creates the list of aristorcrats and not any TA or other action.

Runs every day once a day which is more than necessary since this list is usually updated only once per year unless there's a dramatic change to any of the assets to trigger a rebalance.