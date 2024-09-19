import pandas as pd
import matplotlib.pyplot as plt
from pymarketstore import Client

# Initialize MarketStore client
client = Client("http://localhost:5993/rpc")

# Query data from MarketStore
symbol = "AAPL/1Min/OHLCV"
query = {
    "requests": [
        {
            "destination": symbol,
            "start": "2023-01-01T00:00:00Z",
            "end": "2023-12-31T23:59:59Z",
        }
    ]
}
response = client.query(query)

# Convert the response to a pandas DataFrame
data = response[symbol]
df = pd.DataFrame(data)

# Convert the 'Epoch' column to datetime
df['datetime'] = pd.to_datetime(df['Epoch'], unit='s')

# Set the datetime column as the index
df.set_index('datetime', inplace=True)

# Plot the data using matplotlib
plt.figure(figsize=(12, 6))
plt.plot(df.index, df['Close'], label='Close Price')
plt.title('AAPL Close Price')
plt.xlabel('Date')
plt.ylabel('Price')
plt.legend()
plt.show()