from flask import Flask, jsonify, send_file
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)

# Define the OpenAPI Specification file
OPENAPI_FILE = "spec.yaml"  # Replace with the path to your OpenAPI YAML file

# Swagger UI configuration
SWAGGER_URL = "/swagger"
API_URL = f"/{OPENAPI_FILE}"

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,  # Swagger UI endpoint
    API_URL,      # OpenAPI spec file URL
    config={"app_name": "OpenAPI Visualization"}  # Swagger UI title
)

# Register Swagger UI blueprint
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# Serve OpenAPI specification
@app.route(f"/{OPENAPI_FILE}", methods=["GET"])
def serve_openapi_spec():
    return send_file(OPENAPI_FILE, mimetype="application/yaml")

# Root endpoint for basic API status
@app.route("/")
def home():
    return jsonify({"message": "Welcome to the OpenAPI visualization!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
