from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import logging
import os
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS
CORS(app, origins=[
    "https://starmind.info",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
])

class AccountCreationAPI:
    def __init__(self):
        self.base_url = "https://broker-api-wl.match-trade.com/v1/accounts"
        self.default_headers = {
            'Authorization': '9_Qd-TWhdmywM76uEnoex33Lci3KD2gt0wX7wZcMSuM=',
            'Content-Type': 'application/json'
        }

    def create_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new account using the broker API"""
        try:
            logger.info("Attempting to create account...")
            payload = json.dumps(account_data)
            
            response = requests.post(
                self.base_url,
                headers=self.default_headers,
                data=payload,
                timeout=30
            )

            logger.info(f"Match Trade API Response Status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")

            # Try to parse JSON response
            try:
                response_data = response.json() if response.content else {}
            except json.JSONDecodeError:
                response_data = {"raw_text": response.text}

            return {
                "success": response.status_code in [200, 201],
                "status_code": response.status_code,
                "data": response_data,
                "message": "Account created successfully" if response.status_code in [200, 201] else "Account creation failed"
            }

        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            return {
                "success": False,
                "error": "Request timed out. Please try again.",
                "status_code": None
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            return {
                "success": False,
                "error": "Connection error. Please check your internet connection.",
                "status_code": None
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return {
                "success": False,
                "error": "Network error occurred. Please try again.",
                "status_code": None
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                "success": False,
                "error": "An unexpected error occurred. Please try again.",
                "status_code": None
            }

# Initialize the account creation service
account_service = AccountCreationAPI()

@app.route('/', methods=['GET'])
def home():
    """Basic home endpoint"""
    return jsonify({
        "service": "Account Creation API",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "create_account": "/api/accounts/simple"
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "service": "Account Creation API",
        "cors": "enabled"
    })

@app.route('/api/accounts/simple', methods=['POST', 'OPTIONS'])
def create_simple_account():
    """Create a simple account with minimal required data"""
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        logger.info("Handling CORS preflight request")
        return jsonify({'status': 'ok'})
    
    try:
        logger.info(f"Received {request.method} request to /api/accounts/simple")
        
        # Check content type
        if not request.is_json:
            logger.warning("Request is not JSON")
            return jsonify({
                "success": False,
                "error": "Content-Type must be application/json"
            }), 400
        
        data = request.get_json()
        if not data:
            logger.warning("No JSON data received")
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
            
        logger.info(f"Processing account creation for email: {data.get('email', 'unknown')}")
        
        # Validate required fields
        required_fields = ['email', 'password', 'firstname', 'lastname', 'phoneNumber']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        # Build the account data structure for Match Trade API
        account_data = {
            "email": data['email'].strip(),
            "password": data['password'],
            "offer": data.get('offer', "1a3d47dd-ea8c-4529-9e36-8a42499fcc69"),
            "createAsDepositedAccount": data.get('createAsDepositedAccount', False),
            "personalDetails": {
                "firstname": data['firstname'].strip(),
                "lastname": data['lastname'].strip()
            },
            "contactDetails": {
                "phoneNumber": data['phoneNumber'].strip()
            }
        }
        
        logger.info("Calling Match Trade API...")
        
        # Create account via Match Trade API
        result = account_service.create_account(account_data)
        
        # Determine HTTP status code
        if result["success"]:
            status_code = 200
            logger.info("Account created successfully")
        else:
            status_code = result.get("status_code", 500)
            if status_code is None:
                status_code = 500
            logger.error(f"Account creation failed: {result.get('error', 'Unknown error')}")
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error in create_simple_account endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error occurred"
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "success": False,
        "error": "Method not allowed"
    }), 405

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
