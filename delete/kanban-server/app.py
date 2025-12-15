# app.py
from flask import Flask
from config_loader import load_routes
import os

app = Flask(__name__)

# Load routes from YAML configuration
yaml_file = os.getenv('ROUTES_YAML', 'routes.yaml')
load_routes(app, yaml_file)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)