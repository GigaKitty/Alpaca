import datetime
import finnhub
import os


# Function to check if the value is not None and is a number
def is_valid(value):
    if value is None:
        return 0

    if value == 0:
        return 0

    return value


def good_buy(earning):
    eps_growth_threshold = 0.05  # 5%
    revenue_growth_threshold = 0.03  # 3%

    actual = is_valid(earning["epsActual"])
    estimate = is_valid(earning["epsEstimate"])
    rev_act = is_valid(earning["revenueActual"])
    rev_est = is_valid(earning["revenueEstimate"])

    if actual == False or estimate == False or rev_act == False or rev_est == False:
        return False

    # print(earning)
    # print(actual, estimate, rev_act, rev_est)
    eps_growth = (actual - estimate) / estimate

    revenue_growth = rev_act - rev_est / rev_est

    # Determine if it's a good buy
    is_good_buy = (
        eps_growth > eps_growth_threshold and revenue_growth > revenue_growth_threshold
    )

    # Results by percentage
    eps_growth_percentage = eps_growth * 100
    revenue_growth_percentage = revenue_growth * 100

    if is_good_buy == True:
        print(
            earning,
            is_good_buy,
            eps_growth_percentage,
            revenue_growth_percentage,
            earning["symbol"],
        )

        open_websocket(earning)


# Check every hour for earnings data from 09:30EST (14:30UTC) to 16:00EST (21:00UTC) on weekdays (Mon-Fri)
def fetch_earnings_calendar():
    # Configure your Finnhub API key here
    finnhub_client = finnhub.Client(api_key=os.getenv("FINNHUB_API_KEY"))

    # Define the date range for the earnings calendar
    # For example, the next 7 days from today
    start_date = datetime.datetime.now().date()
    end_date = (
        datetime.datetime.now() + datetime.timedelta(days=os.getenv("FINNHUB_DAYS", 7))
    ).date()

    # Fetch the earnings calendar
    earnings_calendar = finnhub_client.earnings_calendar(
        _from=start_date.strftime("%Y-%m-%d"),
        to=end_date.strftime("%Y-%m-%d"),
        symbol="",
        international=False,
    )

    # Check if there are earnings in the fetched data
    if "earningsCalendar" in earnings_calendar:
        for earning in earnings_calendar["earningsCalendar"]:
            good_buy(
                earning,
            )
    else:
        print("No earnings data found for the specified date range.")


# Function to open a websocket for all the tickers in the earnings calendar
def open_websocket(earning):
    print(earning["symbol"])
    # open websocket and monitor for patterns and changes
    pass


# Function to monitor for patterns at specific interval such as RSI or MacD
def monitor(ticker):
    pass


# Init the main function
fetch_earnings_calendar()
