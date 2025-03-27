# DB Service Client

A Python client for interacting with the database service API.

## Features

- HTTP request handling with automatic retries
- Error classification and handling
- Comprehensive logging
- Asynchronous API methods
- Robust connection management

## Installation

This module is part of the worker package. No separate installation is needed.

## Usage

```python
import asyncio
from worker.services.db import DBService

async def example():
    # Get study data
    study_data = await DBService.get_study_data("database-id", "study-id")
    print(f"Study name: {study_data.get('name')}")

    # Update session data
    await DBService.update_session_data(
        "database-id",
        "study-id",
        "participant-id",
        "session-id",
        {"status": "completed"}
    )

    # Get Figma frame data
    frame_data = await DBService.get_figma_frame_data(
        "database-id",
        "file-key",
        "frame-id"
    )

    # Health check
    health = await DBService.get_health_check()
    print(f"Service status: {health['status']}")

# Run the example
asyncio.run(example())
```

## Error Handling

The client provides detailed error types via the `DBErrorType` enum:

```python
from worker.services.db import DBService, DBErrorType, DBServiceError

try:
    result = await DBService.get_study_data("db-id", "study-id")
except DBServiceError as e:
    if e.error_type == DBErrorType.NOT_FOUND:
        print("Study not found")
    elif e.error_type == DBErrorType.NETWORK_ERROR:
        print("Network error occurred")
    else:
        print(f"Error: {e}")
```

## Configuration

Configuration is loaded from environment variables:

- `DB_SERVICE_URL`: Base URL for the DB service (default: "http://localhost:8080")
- `DB_SERVICE_TIMEOUT`: Default request timeout in seconds (default: 60)

## Testing

Run the tests with pytest:

```bash
python -m pytest worker/services/db/tests/
```
