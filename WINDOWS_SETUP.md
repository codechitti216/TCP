# TCP Setup for Windows with CARLA 0.10.0

This document provides instructions for running TCP on Windows with CARLA 0.10.0.

## Prerequisites

- Windows 10/11
- Python 3.8, 3.9, 3.10, 3.11, or 3.12
- CARLA 0.10.0 installed at: `D:\Carla-0.10.0-Win64-Shipping (1)\Carla-0.10.0-Win64-Shipping`
- NVIDIA GPU with CUDA support (recommended)

## Quick Start

### 1. Install CARLA Python Package

Run the installer script to install the CARLA Python package for your Python version:

```batch
install_carla.bat
```

Or manually install with pip:

```batch
pip install "D:\Carla-0.10.0-Win64-Shipping (1)\Carla-0.10.0-Win64-Shipping\PythonAPI\carla\dist\carla-0.10.0-cp310-cp310-win_amd64.whl"
```

(Replace `cp310` with your Python version: cp38, cp39, cp310, cp311, or cp312)

### 2. Set Up Python Environment

Create and activate the conda environment:

```batch
conda env create -f environment.yml --name TCP
conda activate TCP
```

**Note:** The original environment.yml is for Linux. You may need to modify some packages for Windows compatibility.

### 3. Set Environment Variables

**Option A: Using Command Prompt (CMD)**
```batch
call set_env.bat
```

**Option B: Using PowerShell**
```powershell
. .\set_env.ps1
```

### 4. Start CARLA Server

In a separate terminal, start the CARLA server:

```batch
start_carla.bat
```

Or manually:

```batch
cd "D:\Carla-0.10.0-Win64-Shipping (1)\Carla-0.10.0-Win64-Shipping"
CarlaUnreal.exe -carla-rpc-port=2000 -quality-level=Low
```

### 5. Run Data Collection

With CARLA server running, in another terminal:

```batch
data_collection.bat
```

### 6. Run Evaluation

First, edit `run_evaluation.bat` to set your model checkpoint path, then:

```batch
run_evaluation.bat
```

## Available Scripts

| Script | Description |
|--------|-------------|
| `set_env.bat` | Sets environment variables (CMD) |
| `set_env.ps1` | Sets environment variables (PowerShell) |
| `start_carla.bat` | Starts the CARLA server |
| `install_carla.bat` | Installs CARLA Python package |
| `data_collection.bat` | Runs data collection with Roach agent |
| `run_evaluation.bat` | Runs TCP model evaluation |

## CARLA 0.10.0 vs 0.9.10 Notes

This repository was originally designed for CARLA 0.9.10.1. CARLA 0.10.0 has some API changes:

1. **Python API**: CARLA 0.10.0 uses wheel packages instead of egg files
2. **Executable**: `CarlaUnreal.exe` instead of `CarlaUE4.exe`
3. **API Changes**: Some API methods may have changed. Check the [CARLA 0.10.0 documentation](https://carla.readthedocs.io/) for details.

## Troubleshooting

### "ModuleNotFoundError: No module named 'carla'"

Make sure you've installed the CARLA wheel package:
```batch
install_carla.bat
```

### Connection refused errors

1. Make sure CARLA server is running (`start_carla.bat`)
2. Check the port (default: 2000)
3. Verify no firewall is blocking the connection

### CUDA/GPU errors

1. Make sure you have the correct NVIDIA drivers installed
2. Verify CUDA is working: `python -c "import torch; print(torch.cuda.is_available())"`

### Python version mismatch

CARLA 0.10.0 provides wheels for Python 3.8-3.12. Make sure your Python version matches one of the available wheels.

## Configuration

### Changing CARLA Path

If your CARLA installation is in a different location, edit the following files:
- `set_env.bat` - Update `CARLA_ROOT`
- `set_env.ps1` - Update `$env:CARLA_ROOT`
- `start_carla.bat` - Update `CARLA_ROOT`
- `install_carla.bat` - Update `CARLA_ROOT`

### Changing Ports

Default ports:
- CARLA RPC Port: 2000
- Traffic Manager Port: 8000

To change, edit the `PORT` and `TM_PORT` variables in the batch scripts.

