from flask import Flask, request, jsonify
from flask_swagger_ui import get_swaggerui_blueprint
import logging
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import get_current_span

# Initialize Flask App
app = Flask(__name__)

# OpenTelemetry Tracing
FlaskInstrumentor().instrument_app(app)
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317")))

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - TraceID: %(trace_id)s - %(message)s')
logger = logging.getLogger(__name__)

# In-memory Coffee Shop menu
coffees = [
    {"id": 1, "name": "Espresso", "price": 2.5},
    {"id": 2, "name": "Latte", "price": 3.5},
    {"id": 3, "name": "Cappuccino", "price": 3.0},
    {"id": 4, "name": "Chai", "price": 1.5}
]

# You can also configure an external database

def get_trace_id():
    """Retrieve the current trace ID from OpenTelemetry."""
    span = get_current_span()
    if span and span.get_span_context():
        return span.get_span_context().trace_id
    return "NoTrace"

@app.before_request
def log_request():
    logger.info(f"Incoming request: {request.method} {request.url} - Trace ID: {get_trace_id()}")

@app.after_request
def log_response(response):
    logger.info(f"Response: {response.status_code} - Trace ID: {get_trace_id()}")
    return response

@app.route('/coffees', methods=['GET'])
def get_coffees():
    """Get all coffees"""
    logger.info("Fetching all coffees", extra={"trace_id": get_trace_id()})
    return jsonify({"coffees": coffees}), 200

@app.route('/coffees', methods=['POST'])
def add_coffee():
    """Add a new coffee"""
    data = request.get_json()
    if "name" not in data or "price" not in data:
        logger.error("Invalid request: Missing 'name' or 'price'")
        return jsonify({"error": "Name and price are required"}), 400

    new_coffee = {"id": len(coffees) + 1, "name": data["name"], "price": data["price"]}
    coffees.append(new_coffee)
    logger.info(f"Added new coffee: {new_coffee}", extra={"trace_id": get_trace_id()})
    return jsonify(new_coffee), 201

@app.route('/coffees/<int:coffee_id>', methods=['GET'])
def get_coffee(coffee_id):
    """Get coffee by ID"""
    coffee = next((c for c in coffees if c["id"] == coffee_id), None)
    if not coffee:
        logger.warning(f"Coffee with id {coffee_id} not found", extra={"trace_id": get_trace_id()})
        return jsonify({"error": "Coffee not found"}), 404
    return jsonify(coffee), 200

@app.route('/coffees/<int:coffee_id>', methods=['PUT'])
def update_coffee(coffee_id):
    """Update coffee by ID"""
    coffee = next((c for c in coffees if c["id"] == coffee_id), None)
    if not coffee:
        return jsonify({"error": "Coffee not found"}), 404

    data = request.get_json()
    coffee["name"] = data.get("name", coffee["name"])
    coffee["price"] = data.get("price", coffee["price"])
    logger.info(f"Updated coffee: {coffee}", extra={"trace_id": get_trace_id()})
    return jsonify(coffee), 200

@app.route('/coffees/<int:coffee_id>', methods=['DELETE'])
def delete_coffee(coffee_id):
    """Delete coffee by ID"""
    global coffees
    coffees = [c for c in coffees if c["id"] != coffee_id]
    logger.info(f"Deleted coffee with id {coffee_id}", extra={"trace_id": get_trace_id()})
    return jsonify({"message": "Coffee deleted"}), 200

# Swagger Documentation
SWAGGER_URL = "/docs"
API_URL = "/static/swagger.json"
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# Run Application
if __name__ == "__main__":
    app.run(debug=True)
