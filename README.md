
## API Usage 
This app calls the Allen Brain Atlas API via the `allen_api.py` module using the `requests` library to fetch metadata for a given structure ID. The key parameter is the numeric `structure_id`, which is included in the API query to request fields like name, acronym, and `color_hex_triplet`. The API returns JSON; the code parses it into Python dictionaries and uses those values to color 3D meshes and label slices. Responses are cached on disk in `.cache/allen_structures.json` to reduce repeated calls. No API key is required for the public Allen API, so there is no authentication setup needed.

## Quick Start

1. **Install dependencies:**
   ```bash
   bash setup.sh
   ```
   Or manually:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the app:**
   ```bash
   streamlit run app.py
   ```

3. Open browser to `http://localhost:8501`

## Features
- Explore 3D mouse brain with interactive visualization
- Make virtual blade cuts along different axes
- Browse generated atlas slices
- Annotate structures using Allen Brain Atlas API
- Export slices as PNG or PDF


