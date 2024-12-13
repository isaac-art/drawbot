import argparse
import json
import random
import time
import requests
from pathlib import Path

def upload_image(url, image_path):
    upload_url = f"{url}/upload/image"
    files = {'image': open(image_path, 'rb')}
    data = {'type': 'input', 'overwrite': 'true'}

    try:
        response = requests.post(upload_url, files=files, data=data)
        response.raise_for_status()
        result = response.json()
        filename = result['name']
        print(f"Image uploaded successfully. Server filename: {filename}")
        return filename
    except requests.exceptions.RequestException as ex:
        print(f'POST {upload_url} failed: {ex}')
        return None
    finally:
        files['image'].close()

def queue_prompt(url, prompt):
    p = {"prompt": prompt}
    data = json.dumps(p).encode('utf-8')
    prompt_url = f"{url}/prompt"
    try:
        r = requests.post(prompt_url, data=data)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as ex:
        print(f'POST {prompt_url} failed: {ex}')
        return None

def get_queue(url):
    queue_url = f"{url}/queue"
    try:
        r = requests.get(queue_url)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as ex:
        print(f'GET {queue_url} failed: {ex}')
        return None

def get_history(url, prompt_id):
    history_url = f"{url}/history/{prompt_id}"
    try:
        r = requests.get(history_url)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as ex:
        print(f'GET {history_url} failed: {ex}')
        return None

def download_image(url, save_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"Image saved locally as: {save_path}")
    except requests.exceptions.RequestException as ex:
        print(f"Failed to download the image: {ex}")

def main(ip, port, filepath, image_path):
    url = f"http://{ip}:{port}"

    # Upload the image
    uploaded_filename = upload_image(url, image_path)
    if uploaded_filename is None:
        print("Image upload failed. Exiting.")
        return

    # Load the workflow JSON
    with open(filepath, 'r') as file:
        prompt_text = json.load(file)

    prompt_text["5"]["inputs"]["image"] = uploaded_filename

    # Queue the prompt
    response1 = queue_prompt(url, prompt_text)
    if response1 is None:
        print("Failed to queue the prompt.")
        return

    prompt_id = response1['prompt_id']
    print(f'Prompt ID: {prompt_id}')
    print('-' * 20)

    # Monitor the queue
    while True:
        time.sleep(5)
        queue_response = get_queue(url)
        if queue_response is None:
            continue

        queue_pending = queue_response.get('queue_pending', [])
        queue_running = queue_response.get('queue_running', [])

        # Check position in queue
        for position, item in enumerate(queue_pending):
            if item[1] == prompt_id:
                print(f'Queue running: {len(queue_running)}, Queue pending: {len(queue_pending)}, Workflow is in position {position + 1} in the queue.')

        # Check if the prompt is currently running
        for item in queue_running:
            if item[1] == prompt_id:
                print(f'Queue running: {len(queue_running)}, Queue pending: {len(queue_pending)}, Workflow is currently running.')
                break

        if not any(prompt_id in item for item in queue_pending + queue_running):
            break

    # Retrieve the output
    history_response = get_history(url, prompt_id)
    if history_response is None:
        print("Failed to retrieve history.")
        return

    output_info = history_response.get(prompt_id, {}).get('outputs', {}).get('64', {}).get('images', [{}])[0]
    filename = output_info.get('filename', 'unknown.png')
    output_url = f"{url}/output/{filename}"

    print(f"Output URL: {output_url}")

    # Save the image locally
    save_path = Path("output") / filename
    save_path.parent.mkdir(exist_ok=True)  # Create 'output' directory if it doesn't exist
    download_image(output_url, save_path)
    return save_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Add a prompt to the queue and wait for the output.')
    parser.add_argument('--ip', type=str, required=True, help='The public IP address of the pod.')
    parser.add_argument('--port', type=int, required=True, help='The external port of the pod.')
    parser.add_argument('--filepath', type=str, required=True, help='The path to the JSON file containing the workflow in API format.')
    parser.add_argument('--image_path', type=str, required=True, help='The path to the image file to upload.')

    args = parser.parse_args()
    main(args.ip, args.port, args.filepath, args.image_path)
