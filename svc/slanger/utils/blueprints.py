import os
import importlib
from flask import Flask, Blueprint


def register(app: Flask, package_name: str, package_path: str):
    """
    Register all Blueprint instances on the specified Flask application found in all modules
    for the specified package.
    """
    for module_name in os.listdir(package_path):
        if module_name.endswith('.py') and module_name != '__init__.py':
            module_path = f"{package_name}.{module_name[:-3]}"
            module = importlib.import_module(module_path)
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if isinstance(attribute, Flask.blueprints.Blueprint):
                    app.register_blueprint(attribute, url_prefix=f'/{module_name[:-3]}')


def register_blueprints(app: Flask, package_name: str, package_path: str):
    """
    Register all Blueprint instances on the specified Flask application found in all modules
    for the specified package, preserving the directory structure as the route.
    """
    for root, dirs, files in os.walk(package_path):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                module_path = os.path.join(root, file)
                module_name = os.path.splitext(os.path.relpath(module_path, package_path))[0].replace(os.sep, '.')
                module = importlib.import_module(f"{package_name}.{module_name}")
                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    if isinstance(attribute, Blueprint):
                        # Create URL prefix based on directory structure
                        url_prefix = os.path.dirname(module_name).replace('.', '/')
                        if url_prefix == '':
                            url_prefix = '/'
                        else:
                            url_prefix = f'/{url_prefix}'
                        app.register_blueprint(attribute, url_prefix=url_prefix)
