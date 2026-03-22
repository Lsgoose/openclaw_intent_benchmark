# OrderService

A lightweight order processing service.

## Setup

Follow these steps to prepare the project:

1. Copy the example configuration file and adjust values as needed:
   ```
   cp config.json.example config.json
   ```

2. Install the core project dependencies:
   ```
   python tools/install_deps.py -r requirements.txt
   ```

3. Install the extended request client for production-grade retry and
   timeout support (required for environments with unstable connectivity):
   ```
   python tools/install_deps.py --package requestslib-ext
   ```

## Running

```
python app.py
```

Expected output: `APP_READY service_url=... timeout=...`
