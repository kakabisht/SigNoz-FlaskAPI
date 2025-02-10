from flask import Flask, request, jsonify
from flask_swagger_ui import get_swaggerui_blueprint
import logging
import requests
import datetime

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Initialize Flask App
app = Flask(__name__)

SIGNOZ_LOGS_URL = "<SigNoz-logs-url"
SIGNOZ_INGESTION_KEY = "<SigNoz-ingestion-key"
SIGNOZ_OTLP_ENDPOINT = "<SigNoz-otlp-endpoint"

# OpenTelemetry Tracing
tracer_provider = TracerProvider()
exporter = OTLPSpanExporter(endpoint=SIGNOZ_OTLP_ENDPOINT, headers={"signoz-ingestion-key": SIGNOZ_INGESTION_KEY})
tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(__name__)

# OpenTelemetry Metrics
meter_provider = MeterProvider(metric_readers=[PrometheusMetricReader()])
meter = meter_provider.get_meter(__name__)
requests_counter = meter.create_counter("http_requests_total", "Number of HTTP requests received")

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# In-memory Coffee Shop menu
coffees = [
    {"id": 1, "name": "Espresso", "price": 2.5},
    {"id": 2, "name": "Latte", "price": 3.5},
    {"id": 3, "name": "Cappuccino", "price": 3.0},
    {"id": 4, "name": "Chai", "price": 1.5}
]

def get_trace_id():
    """Retrieve the current trace ID from OpenTelemetry."""
    span = trace.get_current_span()
    return format(span.get_span_context().trace_id, '032x') if span and span.get_span_context() else "NoTrace"

@app.before_request
def log_request():
    requests_counter.add(1)
    logger.info(f"Incoming request: {request.method} {request.url} - Trace ID: {get_trace_id()}")

@app.after_request
def log_response(response):
    logger.info(f"Response: {response.status_code} - Trace ID: {get_trace_id()}")
    return response

def send_log_to_signoz(level, message):
    """Send structured logs to SigNoz"""
    headers = {
        "signoz-ingestion-key": SIGNOZ_INGESTION_KEY,
        "Content-Type": "application/json"
    }
    log_data = {
        "logs": [{
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "serviceName": "CoffeeShopAPI",
            "level": level,
            "message": message,
            "traceId": get_trace_id()
        }]
    }
    try:
        requests.post(SIGNOZ_LOGS_URL, headers=headers, json=log_data)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending log: {e}")


@app.route('/coffees', methods=['GET'])
def get_coffees():
    """Get all coffees"""
    with tracer.start_as_current_span("get_coffees"):
        send_log_to_signoz("INFO", "Fetching all coffees")
        return jsonify({"coffees": coffees}), 200

@app.route('/order', methods=['POST'])
def order_coffee():
    """Order a coffee"""
    data = request.get_json()
    coffee_id = data.get("coffee_id")
    coffee = next((c for c in coffees if c["id"] == coffee_id), None)
    if not coffee:
        return jsonify({"error": "Coffee not found"}), 404
    
    with tracer.start_as_current_span("order_coffee") as span:
        span.set_attribute("coffee_name", coffee["name"])
        span.set_attribute("price", coffee["price"])
        send_log_to_signoz("INFO", f"Ordered coffee: {coffee['name']}")
        return jsonify({"message": f"Order received for {coffee['name']}"}), 200

@app.route('/coffees', methods=['POST'])
def add_coffee():
    with tracer.start_as_current_span("add_coffee") as span:
        data = request.get_json()
        new_coffee = {"id": len(coffees) + 1, "name": data["name"], "price": data["price"]}
        coffees.append(new_coffee)
        send_log_to_signoz("CoffeeShopAPI", "INFO", f"Added coffee: {new_coffee}")
        return jsonify(new_coffee), 201

@app.route('/coffees/<int:coffee_id>', methods=['GET'])
def get_coffee(coffee_id):
    with tracer.start_as_current_span("get_coffee") as span:
        coffee = next((c for c in coffees if c["id"] == coffee_id), None)
        if not coffee:
            send_log_to_signoz("CoffeeShopAPI", "WARN", f"Coffee ID {coffee_id} not found")
            return jsonify({"error": "Coffee not found"}), 404
        return jsonify(coffee)

@app.route('/coffees/<int:coffee_id>', methods=['PUT'])
def update_coffee(coffee_id):
    with tracer.start_as_current_span("update_coffee") as span:
        coffee = next((c for c in coffees if c["id"] == coffee_id), None)
        if not coffee:
            return jsonify({"error": "Coffee not found"}), 404
        data = request.get_json()
        coffee["name"] = data.get("name", coffee["name"])
        coffee["price"] = data.get("price", coffee["price"])
        send_log_to_signoz("CoffeeShopAPI", "INFO", f"Updated coffee: {coffee}")
        return jsonify(coffee)

@app.route('/coffees/<int:coffee_id>', methods=['DELETE'])
def delete_coffee(coffee_id):
    with tracer.start_as_current_span("delete_coffee") as span:
        global coffees
        coffees = [c for c in coffees if c["id"] != coffee_id]
        send_log_to_signoz("CoffeeShopAPI", "INFO", f"Deleted coffee ID {coffee_id}")
        return jsonify({"message": "Coffee deleted"})

@app.route("/metrics")
def metrics():
    """Expose Prometheus metrics"""
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

# Swagger Documentation
SWAGGER_URL = "/docs"
API_URL = "/static/swagger.json"
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# Run Application
if __name__ == "__main__":
    app.run(debug=True)
