# FRIDAY Voice Assistant 🎙️

A voice-controlled assistant with system control capabilities, built with FastAPI.

## Installation

```bash
pip install friday-assistant
```

## Requirements

- Python >= 3.8
- FastAPI
- Uvicorn
- WebSockets
- python-dotenv

## Usage

```python
from app import app
import uvicorn

uvicorn.run(app, host="0.0.0.0", port=8000)
```

Or run directly via CLI:

```bash
uvicorn app.main:app --reload
```

## Environment Variables

Create a `.env` file in your root directory:

```env
# Add your environment variables here
API_KEY=your_api_key
```

## Features

- 🎙️ Voice-controlled assistant
- 🔌 WebSocket support
- 🌐 REST API via FastAPI
- ⚙️ System control capabilities
- 🔒 CORS enabled

## License

MIT License
