# This programm is an adaptation of the example script provided with ComfyUI : websockets_api_example.py
# The core of the script is unchanged, only the way prompts are queued and processed has been modified to allow batch processing from a json file

# This programme is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by  

#This is an example that uses the websockets api to know when a prompt execution is done
#Once the prompt execution is done it downloads the images using the /history endpoint

import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
import random
import os
import sys
from datetime import datetime

server_address = "127.0.0.1:8188"
client_id = str(uuid.uuid4())

def queue_prompt(prompt, prompt_id):
    p = {"prompt": prompt, "client_id": client_id, "prompt_id": prompt_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    urllib.request.urlopen(req).read()

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())

def get_images(ws, prompt):
    prompt_id = str(uuid.uuid4())
    queue_prompt(prompt, prompt_id)
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break #Execution is done
        else:
            # If you want to be able to decode the binary stream for latent previews, here is how you can do it:
            # bytesIO = BytesIO(out[8:])
            # preview_image = Image.open(bytesIO) # This is your preview in PIL image format, store it in a global
            continue #previews are binary data

    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        images_output = []
        if 'images' in node_output:
            for image in node_output['images']:
                image_data = get_image(image['filename'], image['subfolder'], image['type'])
                images_output.append(image_data)
        output_images[node_id] = images_output

    return output_images

def gen_images(jsonwf, save_images_params):
    """
    Queues a prompt for execution via the ComfyUI HTTP API.
    Tries two payload formats: one with the prompt as a dict, another with the prompt as a JSON string,
    """
    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
    images = get_images(ws, jsonwf)
    #ws.close() # for in case this example is used in an environment where it will be repeatedly called, like in a Gradio app. otherwise, you'll randomly receive connection timeouts
    #Commented out code to display the output images:

    if save_images_params['enabled']:
        for node_id in images:
            for image_data in images[node_id]:
                from PIL import Image
                import io
                image = Image.open(io.BytesIO(image_data))
                # générer un timestamp au format YYYYMMDD-hhmmss et l'utiliser comme nom
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{random.randint(1000,9999)}"
                image.save(save_images_params['output_directory'] + save_images_params['filename_prefix'] + f"-output_{timestamp}.png")
    
    
    ws.close()

def read_prompt_file(prompt_file):
    with open(prompt_file, "r", encoding="utf-8") as f:
        pjson = json.load(f)
    return pjson

def main():
    prompt_file = sys.argv[1] if len(sys.argv) > 1 else "./batchs/prompt-1.json"
    if not os.path.exists(prompt_file):
        print(f"Prompt file '{prompt_file}' not found.")
        return
    
    jsonwf = read_prompt_file(prompt_file)

    workflow_file = jsonwf['parameters']['workflow_file']
    workflow_items =  jsonwf['parameters']['workflow_items']
    prompts = jsonwf['prompts']
    save_images_params = jsonwf['parameters']['save_images']
    
    try:
        generic_prompts = jsonwf['parameters']['generic_prompts']
    except KeyError:
        generic_prompts = None

    # Iterate over each prompt and generate images
    for prompt in prompts:
        print("="*50)
        # Load the original workflow JSON data
        with open(workflow_file, "r", encoding="utf-8") as f:
            workflow_jsondata = f.read()

        jsonwf = json.loads(workflow_jsondata)

        # If generic prompt exists apply it
        if generic_prompts:
            for generic_key, generic_value in generic_prompts.items():
                # Get the node ID and input details from workflow_items
                z = workflow_items[generic_key].split(",")
                node_id = z[0]
                input_type = z[1]
                input_name = z[2]
                print(f"        Setting generic node {node_id} {input_type} {input_name} to {generic_value}")

                # Set the value in the workflow JSON
                jsonwf[node_id][input_type][input_name] = generic_value


        print ("===>", prompt)

        # Apply each prompt parameter to the workflow
        for prompt_key, prompt_value in prompt.items():
            print("   --->", prompt_key, " = ", prompt_value)

            # Determine the specific value to set from seed
            if (prompt_key == "seed" or prompt_key == "noise_seed" ) and prompt_value == "random":
                value = random.randint(1, 999999999999)
            else:
                value = prompt_value

            # Get the node ID and input details from workflow_items
            z = workflow_items[prompt_key].split(",")
            node_id = z[0]
            input_type = z[1]
            input_name = z[2]
            print(f"        Setting node {node_id} {input_type} {input_name} to {value}")

            # Set the value in the workflow JSON
            jsonwf[node_id][input_type][input_name] = value

        # Generate images with the updated workflow
        print("Generating images...")
        gen_images(jsonwf, save_images_params)

if __name__ == "__main__":
    main()