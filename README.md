# kedro-pamflow

This repository provides a workflow for analyzing passive acoustic monitoring (PAM) data using Python. It is designed to offer an easy-to-use and reproducible framework for researchers, conservation biologists, citizen scientists, and anyone interested in ecoacoustics and soundscape ecology.

## Before You Begin

### 1. Download or Clone This Repository

```bash
git clone https://github.com/nicolasbetancourtc/kedroPamflow
cd kedroPamflow
```

### 2. Set Up a Working Environment
Ensure you have Python 3.11 installed. Then, create and activate a virtual environment:

```bash
conda create -n pamenv python=3.11
conda activate pamenv
```

Next, install the required dependencies based on your operating system.

#### On Windows:
```bash
pip install -r requirements-win.txt
```

#### On macOS:
```bash
pip install -r requirements-mac.txt
```

### 3. Organize PAM Data
- **Audio Data:** All audio files must be stored in a dedicated directory. Each subdirectory within this directory should have a unique identifier corresponding to the ID or name of each sensor. This structure ensures that recordings are properly associated with their respective sensors.
- **Metadata:** Make sure you have a field deployment sheet in an Excel format. This sheet must contain a column named `recorderID`, where each value matches the names of the subdirectories in the audio data directory. This ensures proper linking between metadata and recorded audio files.

## Getting Started

### 1. Configure Local Settings

Edit the `./conf/local/parameters.yml` file to specify the path to your audio files:
```yaml
DEVICES_ROOT_DIRECTORY: <path to your directory with audio files>
```

Edit the `./conf/local/catalog.yml` file to define the path to your field deployment sheet:
```yaml
field_deployments_sheet@pandas:
  type: pandas.ExcelDataset
  filepath: <path to your Excel file with deployment information>
```

### 2. Run Workflows

The workflow can be executed entirely with the command:
```bash
kedro run
```
However, for the first execution, it is recommended to run one pipeline at a time for better control.

#### 2.1. Preprocessing
```bash
kedro run --pipeline=preprocessing
```

#### 2.2. Compute Acoustic Indices
```bash
kedro run --pipeline=acoustic_indices
```

#### 2.3. Generate Graphical Soundscapes
```bash
kedro run --pipeline=graphical_soundscape
```

#### 2.4. Perform BirdNet Detections
```bash
kedro run --pipeline=birdnet
```

## License

This project is licensed under the MIT License. See the [LICENSE.md](LICENSE.md) file for details.
