import os
import json
import shutil
import subprocess
import hashlib
from flask import send_file, Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time

app = Flask(__name__)

# Directory where admin datasets are stored
ADMIN_DATASET_DIRECTORY = "C:/datasets"

# Directory where datasets should be shared with users
SHARED_DIRECTORY = "C:/SharedDatasets"

# Ensure the shared directory exists and is shared
def create_shared_directory():
    if not os.path.exists(SHARED_DIRECTORY):
        os.makedirs(SHARED_DIRECTORY)
        # Command to share the folder with full access for everyone
        share_command = f'net share SharedDatasets={SHARED_DIRECTORY} /grant:everyone,full'
        try:
            # Execute the command to share the folder
            subprocess.run(share_command, shell=True, check=True)
            print("Shared folder created and shared successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to share the folder: {e}")

# MongoDB connection details for the main database
MONGO_URI = "mongodb+srv://ddas:ddas@sample.nnpef.mongodb.net/?retryWrites=true&w=majority&appName=sample"
DATABASE_NAME = "ddas"
DOWNLOAD_COLLECTION_NAME = "already_downloaded_datasets"

# Connect to the main MongoDB database
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
download_collection = db[DOWNLOAD_COLLECTION_NAME]

def calculate_file_hash(file_path):
    """Calculate the SHA-256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_sha256.update(chunk)
    except IOError as e:
        print(f"Unable to read file {file_path}: {e}")
    return hash_sha256.hexdigest()

def is_dataset_file(filename):
    # Filter out system files like 'desktop.ini'
    return not filename.startswith('.') and filename.lower() != 'desktop.ini'

@app.route('/api/admin_datasets', methods=['GET'])
def list_admin_datasets():
    try:
        datasets = [f for f in os.listdir(ADMIN_DATASET_DIRECTORY) 
                    if os.path.isfile(os.path.join(ADMIN_DATASET_DIRECTORY, f)) 
                    and is_dataset_file(f)]
        return jsonify({'datasets': datasets})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/shared_datasets', methods=['GET'])
def list_shared_datasets():
    try:
        datasets = [f for f in os.listdir(SHARED_DIRECTORY) 
                    if os.path.isfile(os.path.join(SHARED_DIRECTORY, f)) 
                    and is_dataset_file(f)]
        return jsonify({'datasets': datasets})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/check_admin/<filename>', methods=['GET'])
def check_admin_dataset(filename):
    try:
        admin_file_path = os.path.join(ADMIN_DATASET_DIRECTORY, filename)
        if os.path.exists(admin_file_path):
            return jsonify({'message': 'Dataset exists in admin directory.', 'exists': True}), 200
        return jsonify({'message': 'Dataset does not exist in admin directory.', 'exists': False}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/check_shared/<filename>', methods=['GET'])
def check_shared_dataset(filename):
    try:
        shared_file_path = os.path.join(SHARED_DIRECTORY, filename)
        if os.path.exists(shared_file_path):
            return jsonify({'message': 'Dataset exists in shared directory.', 'exists': True}), 200
        return jsonify({'message': 'Dataset does not exist in shared directory.', 'exists': False}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/check_all', methods=['GET'])
def check_all_datasets():
    try:
        datasets = os.listdir(ADMIN_DATASET_DIRECTORY)
        already_downloaded = []
        not_downloaded = []

        for filename in datasets:
            if is_dataset_file(filename):
                result = download_collection.find_one({'filename': filename})
                if result:
                    already_downloaded.append({
                        'filename': filename,
                        'client_ip': result['client_ip'],
                        'download_time': result.get('download_time', 'N/A'),
                        'dataset_path': os.path.join(SHARED_DIRECTORY, filename)
                    })
                else:
                    not_downloaded.append(filename)

        return jsonify({
            "already_downloaded": already_downloaded,
            "not_downloaded": not_downloaded
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_dataset(filename):
    try:
        admin_file_path = os.path.join(ADMIN_DATASET_DIRECTORY, filename)
        shared_file_path = os.path.join(SHARED_DIRECTORY, filename)

        if not os.path.exists(admin_file_path):
            return jsonify({'error': 'Dataset not found in the admin directory.'}), 404

        # Calculate hash for the admin file
        file_hash = calculate_file_hash(admin_file_path)

        # Check if there's an existing record with the same hash
        existing_record = download_collection.find_one({'file_hash': file_hash})

        if existing_record:
            # If filename differs but content is the same, update the record
            if existing_record['filename'] != filename:
                update_result = download_collection.update_one(
                    {'_id': existing_record['_id']},
                    {'$set': {'filename': filename, 'dataset_path': shared_file_path}}
                )
                
                if update_result.modified_count > 0:
                    return jsonify({
                        "message": "Filename changed but content is the same.",
                        "status": "filename_changed",
                        "user_details": {
                            'client_ip': existing_record['client_ip'],
                            'download_time': existing_record.get('download_time', 'N/A'),
                            'dataset_path': shared_file_path
                        }
                    }), 409
                else:
                    return jsonify({'error': 'Failed to update the filename in the database.'}), 500

            # If filename and content are the same
            if existing_record['filename'] == filename:
                return jsonify({
                    "message": "Exact match: This dataset has already been processed.",
                    "status": "exact_match",
                    "user_details": {
                        'client_ip': existing_record['client_ip'],
                        'download_time': existing_record.get('download_time', 'N/A'),
                        'dataset_path': shared_file_path
                    }
                }), 409

        # Check for different name, same content
        diff_name_same_content = download_collection.find_one({
            'file_hash': file_hash,
            'filename': {'$ne': filename}
        })

        if diff_name_same_content:
            # Update the old file record with the new filename and path
            download_collection.update_one(
                {'_id': diff_name_same_content['_id']},
                {'$set': {'filename': filename, 'dataset_path': shared_file_path}}
            )

            return jsonify({
                "message": "Different name, same content: A file with the same content but a different name exists.",
                "status": "diff_name_same_content",
                "user_details": {
                    'client_ip': diff_name_same_content['client_ip'],
                    'download_time': diff_name_same_content.get('download_time', 'N/A'),
                    'dataset_path': shared_file_path
                }
            }), 409

        # Copy dataset from the admin directory to the shared directory
        shutil.copy(admin_file_path, shared_file_path)

        # Log the download details to the database
        download_collection.insert_one({
            'filename': filename,
            'file_hash': file_hash,
            'client_ip': request.remote_addr,
            'download_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'dataset_path': shared_file_path
        })

        try:
            # Serve the file from the shared directory directly
            return send_file(shared_file_path, as_attachment=True)
        except Exception as e:
            return jsonify({'error': f'Failed to send file: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


class FileRenameHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return

        # When a file is renamed, we need to check the new filename
        if event.event_type == 'moved':
            new_filename = os.path.basename(event.dest_path)
            old_filename = os.path.basename(event.src_path)

            # Update the database record for the old filename
            old_file_path = os.path.join(SHARED_DIRECTORY, old_filename)
            new_file_path = os.path.join(SHARED_DIRECTORY, new_filename)

            if os.path.exists(old_file_path):
                # Calculate hash for the renamed file
                file_hash = calculate_file_hash(old_file_path)
                download_collection.update_one(
                    {'filename': old_filename},
                    {'$set': {'filename': new_filename, 'dataset_path': new_file_path, 'file_hash': file_hash}}
                )
                # Rename the file on disk
                os.rename(old_file_path, new_file_path)

def start_file_observer():
    event_handler = FileRenameHandler()
    observer = Observer()
    observer.schedule(event_handler, path=SHARED_DIRECTORY, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    create_shared_directory()
    thread = threading.Thread(target=start_file_observer)
    thread.start()
    app.run(host='192.168.74.42',debug=True, port=5000)
