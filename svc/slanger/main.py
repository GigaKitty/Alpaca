from config import app
from flask import Flask, Blueprint, render_template, request, jsonify, g
from routes import health, before_request, after_request, error_handler, favicon
import importlib
import os


def register_routes(app, package_name, package_path):
    """
    Blueprints autoloader for all endpoints
    """
    for module_name in os.listdir(package_path):
        if module_name.endswith(".py") and module_name != "__init__.py":
            module = importlib.import_module(f"{package_name}.{module_name[:-3]}")
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if isinstance(attribute, Blueprint):
                    app.register_blueprint(
                        attribute, url_prefix=f'/{package_name.split(".")[-1]}'
                    )


if __name__ == "__main__":
    # Register routes for crypto
    register_routes(app, "routes.crypto", "routes/crypto")

    # Register routes for equity
    register_routes(app, "routes.equity", "routes/equity")

    # Register routes for equity
    register_routes(app, "routes.options", "routes/options")

    # Run the app
    app.run(host="0.0.0.0", port=5000)
