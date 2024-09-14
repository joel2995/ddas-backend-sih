from flask import Flask, request, jsonify, send_file, abort
import os
import requests
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# Base directory where datasets are stored
DATASET_DIRECTORY = "C:/SharedDatasets"

# Ensure the base dataset directory exists
if not os.path.exists(DATASET_DIRECTORY):
    os.makedirs(DATASET_DIRECTORY)

# MongoDB connection details
MONGO_URI = "mongodb+srv://ddas:ddas@sample.nnpef.mongodb.net/?retryWrites=true&w=majority&appName=sample"
DATABASE_NAME = "ddas"
COLLECTION_NAME = "sample"

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# Server URL for communication
SERVER_URL = 'http://192.168.74.42:5000'  # Ensure this is correctly formatted

def query_server_api(endpoint, method='GET', params=None):
    url = f"{SERVER_URL}/{endpoint}"
    try:
        response = requests.request(method, url, params=params)
        return response.json(), response.status_code
    except requests.RequestException as e:
        return {'error': str(e)}, 500

@app.route('/api/create_repository', methods=['POST'])
def create_repository():
    try:
        client_ip = request.remote_addr
        if client_ip:
            client_repo_path = os.path.join(DATASET_DIRECTORY, client_ip)
            if not os.path.exists(client_repo_path):
                os.makedirs(client_repo_path)
                return jsonify({"message": "Repository created successfully!"}), 201
            return jsonify({"message": "Repository already exists!"}), 200
        return jsonify({"message": "Failed to create repository."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/datasets', methods=['GET'])
def list_datasets():
    try:
        data, status_code = query_server_api("api/datasets")
        return jsonify(data), status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/check/<filename>', methods=['GET'])
def check_dataset(filename):
    try:
        data, status_code = query_server_api(f"api/check/{filename}")
        if status_code == 409:
            return jsonify(data), 409
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_dataset(filename):
    try:
        data, status_code = query_server_api(f"api/download/{filename}")
        if status_code == 409:
            return jsonify(data), 409
        elif status_code == 200:
            return send_file(data['path'], as_attachment=True)
        return abort(404)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/check_all', methods=['GET'])
def check_all_datasets():
    try:
        data, status_code = query_server_api("api/check_all")
        return jsonify(data), status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host='192.168.74.42', port=5001, debug=True)
