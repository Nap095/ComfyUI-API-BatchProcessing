# This programm is an adaptation of the example script provided with ComfyUI : websockets_api_example.py
# The core of the script is unchanged, only the way prompts are queued and processed has been modified to allow batch processing from a json file

# This programme is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by  

#This is an example that uses the websockets api to know when a prompt execution is done
#Once the prompt execution is done it downloads the images using the /history endpoint

import itertools
import re
import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
import random
import os
import sys
from datetime import datetime
from functions_json import get_node_block, set_node_block

def expand_prompt_with_variables(prompt, variables_lists):
    positive_prompt = prompt.get("positive_prompt", "")
    if not positive_prompt or "$" not in positive_prompt:
        return [prompt]

    placeholder_names = re.findall(r"\$([A-Za-z_]\w*)", positive_prompt)
    unique_names = []
    for name in placeholder_names:
        if name in variables_lists and name not in unique_names:
            unique_names.append(name)

    if not unique_names:
        return [prompt]

    lists = [variables_lists[name] for name in unique_names]
    if any(len(values) == 0 for values in lists):
        return [prompt]

    expanded_prompts = []
    for combo in itertools.product(*lists):
        new_prompt = prompt.copy()
        new_positive = positive_prompt
        for name, value in zip(unique_names, combo):
            new_positive = new_positive.replace(f"${name}", value)
        new_prompt["positive_prompt"] = new_positive
        expanded_prompts.append(new_prompt)

    return expanded_prompts

def set_node_block_fallback(workflow, block_name, node_id, attr_name, new_value, index_or_key=None):
    """Modifie un attribut d'un nœud dans un bloc et retourne workflow mis à jour."""
    if not isinstance(workflow, dict):
        raise ValueError("workflow doit être un dict")

    block = workflow.get(block_name)
    if not isinstance(block, list):
        raise ValueError(f"{block_name} doit être une liste")

    node = next((n for n in block if str(n.get("id")) == str(node_id)), None)
    if node is None:
        raise ValueError(f"Noeud id={node_id} non trouvé dans {block_name}")

    if attr_name not in node:
        raise ValueError(f"Attribut '{attr_name}' absent du nœud id={node_id}")

    if index_or_key is not None:
        if isinstance(index_or_key, int):
            attr_value = node[attr_name]
            if not isinstance(attr_value, list):
                raise ValueError(f"Attribut '{attr_name}' n'est pas une liste")
            if not (0 <= index_or_key < len(attr_value)):
                raise IndexError(f"index {index_or_key} hors plage")
            attr_value[index_or_key] = new_value
            node[attr_name] = attr_value
        else:
            # Assume dict
            if not isinstance(node[attr_name], dict):
                raise ValueError(f"Attribut '{attr_name}' n'est pas un dict")
            node[attr_name][index_or_key] = new_value
    else:
        node[attr_name] = new_value

    # Mise à jour du bloc dans workflow
    workflow[block_name] = block
    return workflow

# Use fallback if import fails
try:
    set_node_block
except NameError:
    set_node_block = set_node_block_fallback

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
    prompt_file = sys.argv[1] if len(sys.argv) > 1 else "./batchs-files/prt-v15-pruned.json"
    if not os.path.exists(prompt_file):
        print(f"Prompt file '{prompt_file}' not found.")
        return
    
    jsonwf = read_prompt_file(prompt_file)

    workflow_file = jsonwf['parameters']['workflow_file']
    workflow_items =  jsonwf['parameters']['workflow_items']
    prompts = jsonwf['prompts']
    save_images_params = jsonwf['parameters']['save_images']
    
    # Read variables section if present and store each file as a list of lines
    variables_lists = {}
    lists = []
    if 'variables' in jsonwf:
        for var_name, path in jsonwf['variables'].items():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = [line.strip() for line in f if line.strip()]
                variables_lists[var_name] = content
                lists.append(content)
            except FileNotFoundError:
                print(f"File {path} not found for variable {var_name}")
                variables_lists[var_name] = []
                lists.append([])
    
    try:
        generic_prompts = jsonwf['parameters']['generic_prompts']
    except KeyError:
        generic_prompts = None

    # Iterate over each prompt and generate images
    for prompt in prompts:
        prompt_variants = expand_prompt_with_variables(prompt, variables_lists)
        for variant in prompt_variants:
            print("="*50)
            # Load the original workflow JSON data
            with open(workflow_file, "r", encoding="utf-8") as f:
                workflow_jsondata = f.read()

            jsonwf = json.loads(workflow_jsondata)

            # If generic prompt exists apply it
            if generic_prompts:
                for generic_key, generic_value in generic_prompts.items():
                    # Get the node ID and input details from workflow_items
                    z = workflow_items[generic_key].replace(" ", "").split(",")
                    if len(z) == 4:
                        if z[0] == "nodes":
                            block_name = z[0]
                            node_id = z[1]
                            attr_name = z[2]
                            list_index = z[3]
                        else:
                            block_name = z[1]
                            node_id = z[0]
                            attr_name = z[2]
                            list_index = z[3]
                    elif len(z) == 3:
                        block_name = "nodes"
                        node_id = z[0]
                        attr_name = z[1]
                        list_index = z[2]
                    else:
                        raise ValueError(f"Invalid workflow_items format for {generic_key}: {workflow_items[generic_key]}")

                    index_or_key = int(list_index) if list_index.isdigit() else list_index

                    # Set the value in the workflow JSON
                    if index_or_key is None:
                        jsonwf[node_id][attr_name] = generic_value
                    elif isinstance(index_or_key, int):
                        jsonwf[node_id][attr_name][index_or_key] = generic_value
                    else:
                        jsonwf[node_id][attr_name][index_or_key] = generic_value


            print ("===>", variant)

            # Apply each prompt parameter to the workflow
            for prompt_key, prompt_value in variant.items():
                print("   --->", prompt_key, " = ", prompt_value)

                # Determine the specific value to set from seed
                if (prompt_key == "seed" or prompt_key == "noise_seed" ) and prompt_value == "random":
                    value = random.randint(1, 999999999999)
                else:
                    value = prompt_value

                # Get the node ID and input details from workflow_items
                z = workflow_items[prompt_key].replace(" ", "").split(",")
                if len(z) == 4:
                    if z[0] == "nodes":
                        block_name = z[0]
                        node_id = z[1]
                        attr_name = z[2]
                        list_index = z[3]
                    else:
                        block_name = z[1]
                        node_id = z[0]
                        attr_name = z[2]
                        list_index = z[3]
                elif len(z) == 3:
                    block_name = "nodes"
                    node_id = z[0]
                    attr_name = z[1]
                    list_index = z[2]
                else:
                    raise ValueError(f"Invalid workflow_items format for {prompt_key}: {workflow_items[prompt_key]}")

                index_or_key = int(list_index) if list_index.isdigit() else list_index

                # Set the value in the workflow JSON
                if index_or_key is None:
                    jsonwf[node_id][attr_name] = value
                elif isinstance(index_or_key, int):
                    jsonwf[node_id][attr_name][index_or_key] = value
                else:
                    jsonwf[node_id][attr_name][index_or_key] = value

            # Generate images with the updated workflow
            print("Generating images...")
            gen_images(jsonwf, save_images_params)

if __name__ == "__main__":
    main()