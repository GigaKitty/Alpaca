from config import app
from flask import render_template

# Add app.route for 404 page
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404
