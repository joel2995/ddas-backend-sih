from flask import Flask, jsonify, send_file
from flask_pymongo import PyMongo
from flask_cors import CORS
import gridfs

app = Flask(__name__)
CORS(app)

# Replace with your actual MongoDB URI
app.config["MONGO_URI"] = "mongodb+srv://ddas:ddas@sample.nnpef.mongodb.net/?retryWrites=true&w=majority&appName=sample"
mongo = PyMongo(app)

# Accessing the underlying pymongo database instance
db = mongo.cx["ddas"]  # Replace "ddas" with the correct database name if different
fs = gridfs.GridFS(db)

@app.route('/')
def home():
    return "Welcome to the Flask MongoDB App!"

@app.route('/datasets', methods=['GET'])
def list_datasets():
    try:
        files = fs.find()
        datasets = [file.filename for file in files]  # Filenames with extensions
        return jsonify({'datasets': datasets}), 200
    except Exception as e:
        print("Error occurred:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_dataset(filename):
    try:
        file = fs.find_one({"filename": filename})
        if file:
            return send_file(file, as_attachment=True, download_name=filename)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        print("Error occurred:", e)
        return jsonify({"error": str(e)}), 500
    
@app.route('/get', methods=['GET'])
def get_data():
    # Example data
    data = [{"name": "Dataset1.csv"}, {"name": "Dataset2.xlsx"}]
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='192.168.137.223', port=5000, debug=True)

