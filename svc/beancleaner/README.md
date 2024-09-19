BeanCleaner

Intends to clean up small positions at the end of the day so that we aren't carrying anything overnight or long term which isn't intended to be there. It simply looks for open positions and excludes positions which are meant to be held.

It runs once daily in the very last minute of market hours and closes so the price might not be the best available.