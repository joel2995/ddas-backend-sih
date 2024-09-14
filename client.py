import requests
import os

# Configuration
SERVER_URL = 'http://192.168.1.3:5000'  # Replace with your server's IP address
CLIENT_ID = 'client1'  # Example client ID
NETWORK_SHARED_DIR = r'\\ 192.168.1.3\SharedDatasets'  # Replace with your server's IP address

# Create directory for the client locally
LOCAL_DOWNLOAD_DIR = './client_data/' + CLIENT_ID
if not os.path.exists(LOCAL_DOWNLOAD_DIR):
    os.makedirs(LOCAL_DOWNLOAD_DIR)

def list_datasets():
    try:
        response = requests.get(f'{SERVER_URL}/api/datasets')
        response.raise_for_status()
        datasets = response.json().get('datasets', [])
        print('Available datasets:')
        for dataset in datasets:
            print(dataset)
    except requests.exceptions.RequestException as e:
        print(f'Failed to fetch datasets: {e}')

def check_dataset(filename):
    try:
        response = requests.get(f'{SERVER_URL}/api/check/{filename}')
        response.raise_for_status()
        print('Dataset is not downloaded.')
        return False
    except requests.exceptions.HTTPError as e:
        if response.status_code == 409:
            user_details = response.json().get('user_details', {})
            print('Dataset already downloaded by another user.')
            print(f"Details:\nClient IP: {user_details.get('client_ip')}\nDownload Time: {user_details.get('download_time')}\nPath: {user_details.get('dataset_path')}")
            return True
        else:
            print(f'Error checking dataset: {e}')
            return False
    except requests.exceptions.RequestException as e:
        print(f'Error checking dataset: {e}')
        return False

def log_download(filename):
    try:
        response = requests.post(f'{SERVER_URL}/api/log_download', json={'filename': filename})
        response.raise_for_status()
        print('Download logged successfully.')
    except requests.exceptions.RequestException as e:
        print(f'Failed to log download: {e}')

def download_dataset(filename):
    try:
        network_file_path = os.path.join(NETWORK_SHARED_DIR, filename)
        local_file_path = os.path.join(LOCAL_DOWNLOAD_DIR, filename)
        print(f"Copying from: {network_file_path} to {local_file_path}")
        
        # Copy the file from the network share to the local download directory
        if os.path.exists(network_file_path):
            with open(network_file_path, 'rb') as nf, open(local_file_path, 'wb') as lf:
                lf.write(nf.read())
            print(f'Dataset downloaded to {local_file_path}')
            
            # Log the download in MongoDB
            log_download(filename)
        else:
            print(f"Error: File {filename} does not exist on the network share.")
    except Exception as e:
        print(f'Error downloading dataset: {e}')

def main():
    list_datasets()
    filename = input('Enter the filename to download: ')
    if not check_dataset(filename):
        download_dataset(filename)

if __name__ == '__main__': 
    main()
