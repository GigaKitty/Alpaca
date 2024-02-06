# Syncs the clock so that we don't get an error from the data request
def sync_time(api, request):
    """
    Sync the clock so that we don't get an error from the data request.
    Set the data var and return it
    """
    api.get_clock()
    data = request.json
    return data