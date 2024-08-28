# from config import app
# from flask import request, g

# # Add an orders after_request to handle postprocessing
# @app.after_request
# def after_request(response):
#     # if order was a sell order then calculate total profit of trades and print to console
#     # if hasattr(g, "data") and g.data.get("action") == "sell":
#     #    print(f"Total profit: {calc.calculate_profit(g.data, api)}")

#     # @TODO: this needs to spawn async trailing orders after each market order has been filled
#     if (
#         hasattr(g, "data")
#         and response.status_code == 200
#         and g.data.get("trailing") is True
#     ):
#         # threading.Thread(target=trailing).start()
#         # asyncio.run(trailing())
#         # Run the trailing function as an asynchronous task
#         loop = asyncio.get_event_loop()
#         print("postprocess start")
#         print(g.data)
#         print(g.data.get("trailing"))
#         print("postprocess end")
#         if loop.is_running():
#             asyncio.create_task(trailing())
#         else:
#             loop.run_until_complete(trailing())

#     return response
