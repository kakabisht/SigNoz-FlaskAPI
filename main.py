from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from flasgger import Swagger
import logging

# OpenTelemetry for tracing
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Initialize Flask app and API
app = Flask(__name__)
api = Api(app)
swagger = Swagger(app)  # Initialize Swagger for API documentation

# Enable OpenTelemetry Tracing
FlaskInstrumentor().instrument_app(app)
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317")))

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# In-memory Coffee Shop menu
coffee_menu = [
    {"id": 1, "name": "Espresso", "price": 2.5},
    {"id": 2, "name": "Latte", "price": 3.5},
    {"id": 3, "name": "Cappuccino", "price": 3.0},
    {"id": 4, "name": "Chai", "price": 1.5}
]

# Helper function to find coffee item
def find_coffee(coffee_id):
    return next((coffee for coffee in coffee_menu if coffee["id"] == coffee_id), None)

# API Resource: Coffee List (GET & POST)
class CoffeeList(Resource):
    def get(self):
        """
        Get all coffee items
        ---
        responses:
          200:
            description: A list of coffee items
        """
        logger.info("Fetching all coffee items.")
        return jsonify(coffee_menu)

    def post(self):
        """
        Add a new coffee item
        ---
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              properties:
                name:
                  type: string
                price:
                  type: number
        responses:
          201:
            description: Coffee item added
          400:
            description: Bad Request - Missing fields
        """
        data = request.get_json()
        if not data.get("name") or not data.get("price"):
            logger.warning("Invalid request: Name and price are required.")
            return {"message": "Name and price are required."}, 400
        
        new_coffee = {
            "id": len(coffee_menu) + 1,
            "name": data["name"],
            "price": data["price"]
        }
        coffee_menu.append(new_coffee)
        logger.info(f"Added new coffee: {new_coffee}")
        return new_coffee, 201

# API Resource: Single Coffee Item (GET, PUT, DELETE)
class CoffeeItem(Resource):
    def get(self, coffee_id):
        """
        Get a specific coffee item by ID
        ---
        parameters:
          - name: coffee_id
            in: path
            type: integer
            required: true
        responses:
          200:
            description: Coffee item found
          404:
            description: Coffee not found
        """
        coffee = find_coffee(coffee_id)
        if not coffee:
            logger.warning(f"Coffee item with ID {coffee_id} not found.")
            return {"message": "Coffee not found"}, 404
        
        logger.info(f"Fetching coffee item: {coffee}")
        return coffee

    def put(self, coffee_id):
        """
        Update an existing coffee item
        ---
        parameters:
          - name: coffee_id
            in: path
            type: integer
            required: true
          - name: body
            in: body
            required: true
            schema:
              type: object
              properties:
                name:
                  type: string
                price:
                  type: number
        responses:
          200:
            description: Coffee item updated
          404:
            description: Coffee not found
        """
        coffee = find_coffee(coffee_id)
        if not coffee:
            logger.warning(f"Update failed: Coffee with ID {coffee_id} not found.")
            return {"message": "Coffee not found"}, 404

        data = request.get_json()
        coffee["name"] = data.get("name", coffee["name"])
        coffee["price"] = data.get("price", coffee["price"])
        logger.info(f"Updated coffee item: {coffee}")
        return coffee

    def delete(self, coffee_id):
        """
        Delete a coffee item by ID
        ---
        parameters:
          - name: coffee_id
            in: path
            type: integer
            required: true
        responses:
          200:
            description: Coffee item deleted
          404:
            description: Coffee not found
        """
        global coffee_menu
        coffee = find_coffee(coffee_id)
        if not coffee:
            logger.warning(f"Delete failed: Coffee with ID {coffee_id} not found.")
            return {"message": "Coffee not found"}, 404
        
        coffee_menu = [c for c in coffee_menu if c["id"] != coffee_id]
        logger.info(f"Deleted coffee item: {coffee}")
        return {"message": "Coffee deleted"}, 200

# Add resources to API
api.add_resource(CoffeeList, "/coffees")
api.add_resource(CoffeeItem, "/coffees/<int:coffee_id>")

# Run Flask App
if __name__ == "__main__":
    app.run(debug=True)
