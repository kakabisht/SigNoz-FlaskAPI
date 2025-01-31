from flask import Flask, request, jsonify
from flask_restful import Api, Resource
import logging

# Initialize Flask app and API
app = Flask(__name__)
api = Api(app)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample database (in-memory)
coffee_menu = [
    {"id": 1, "name": "Espresso", "price": 2.5},
    {"id": 2, "name": "Latte", "price": 3.5},
    {"id": 3, "name": "Cappuccino", "price": 3.0}
]

# Helper function to find a coffee item by ID
def find_coffee(coffee_id):
    return next((coffee for coffee in coffee_menu if coffee["id"] == coffee_id), None)

# API Resource: Coffee List (GET and POST)
class CoffeeList(Resource):
    def get(self):
        """Fetch all coffee items"""
        logger.info("Fetching all coffee items.")
        return jsonify(coffee_menu)

    def post(self):
        """Add a new coffee item"""
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
        """Fetch a specific coffee item by ID"""
        coffee = find_coffee(coffee_id)
        if not coffee:
            logger.warning(f"Coffee item with ID {coffee_id} not found.")
            return {"message": "Coffee not found"}, 404
        
        logger.info(f"Fetching coffee item: {coffee}")
        return coffee

    def put(self, coffee_id):
        """Update an existing coffee item"""
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
        """Delete a coffee item by ID"""
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

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
