# ComfyUI API Batch Processing

A batch image generation tool for ComfyUI using WebSocket API. Process multiple prompts sequentially from JSON configuration files.

## Description

This program enables batch image generation using the ComfyUI API. It reads JSON configuration files containing image prompts and workflow parameters, then executes them sequentially against a running ComfyUI server via WebSocket connection.

**Note:** This is an adaptation of the `websockets_api_example.py` script provided with ComfyUI, modified to support batch processing from JSON files.

## Features

- Batch processing of multiple prompts from a single JSON file
- Support for random seed generation
- Generic prompt parameters (applied to all prompts in a batch)
- Image output saving with timestamped filenames
- WebSocket-based communication with ComfyUI server
- Per-prompt parameter overrides

## Requirements

- Python 3.7+
- ComfyUI server running locally
- websocket-client library

## Installation

1. **Clone or download this repository:**
   ```bash
   git clone https://github.com/Nap095/ComfyUI-API-BatchProcessing.git
   cd ComfyUI-API-BatchProcessing

2. **Create and activate a virtual environment**
   ```bash
   python -m venv .ven
   .venv/Script/activate

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt

## Usage

1. **Ensure ComfyUI is running:**

    Start ComfyUI before running batch processing, ComfyUI must be accessible at 127.0.0.1:8188    

2. **Execution:**
    ```batch
    python ComfyUI-API-BatchProcessing.py ./path/prompt_file.json

If no argument is provided, the script looks for ./batchs-files/prt-v15-pruned.json:

By convention, workflow files are stored in the "workflows" directory and batch prompts are stored in the "batches" directory.


Configuration File Format
JSON configuration files must follow this structure:

```
{
    "parameters": {
        "workflow_file": "./workflows-files/your-workflow.json",
        "workflow_items": {
            "positive_prompt": "node_id,inputs,field_name",
            "negative_prompt": "node_id,inputs,field_name",
            "seed": "node_id,inputs,field_name",
            "width": "node_id,inputs,field_name",
            "height": "node_id,inputs,field_name",
            "batch_size": "node_id,inputs,field_name"
        },
        "save_images": {
            "enabled": true,
            "output_directory": "./images/",
            "filename_prefix": "CFYUI-BP"
        },
        "generic_prompts": {
            "negative_prompt": "blurry ugly bad",
            "width": 1024,
            "height": 1024
        }
    },
    "prompts": [
        {
            "positive_prompt": "your prompt here",
            "seed": "random"
        },
        {
            "positive_prompt": "another prompt",
            "negative_prompt": "override generic prompt",
            "seed": 12345,
            "batch_size": 2
        }
    ]
}
```





Configuration Explanation

- workflow_file: Path to the ComfyUI workflow JSON file
- workflow_items: Maps prompt parameters to workflow node locations (format: node_id,inputs,field_name)
- save_images: Configure output image saving
- enabled: Enable/disable image saving
- output_directory: Where to save generated images
- filename_prefix: Prefix for saved image filenames
- generic_prompts: Default parameters applied to all prompts
- prompts: Array of individual prompt configurations
- Use "random" for seed to generate random values
- Any parameter can override generic prompts

File Structure

```
ComfyUI-API-BatchProcessing/
├── ComfyUI-API-BatchProcessing.py   # Main script
├── batchs_files/                    # Batch configuration files
│   ├── prt-Z-Image-Turbo.json
│   └── ...
├── workflows-files/                 # ComfyUI workflow definitions
│   ├── wkf-Z-Image-Turbo-API.json
│   └── ...
├── images/                          # Generated images output
├── archives/                        # (excluded from git)
├── requirements.txt
└── README.md
```

Example

Generate images using the provided configuration:

```batch
    python ComfyUI-API-BatchProcessing.py ./batchs-files/prt-Z-Image-Turbo.json
```

The script will:

- Load the batch configuration
- Load the workflow template
- Apply generic prompts to the workflow
- For each prompt in the batch:
- Override parameters with prompt-specific values
- Queue the workflow for execution
- Wait for completion
- Save images (if enabled). These images have not a metadata

License

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation.

This is an adaptation of the websockets_api_example.py example script provided with ComfyUI.

Troubleshooting

- Connection refused: Ensure ComfyUI server is running on 127.0.0.1:8188
- Prompt file not found: Verify the path to your JSON configuration file
- Images not saving: Check that the output directory exists and is writable

