# LiveKit Voice Assistant with RPC Support

This project implements a voice assistant using LiveKit's agent framework with added support for RPC (Remote Procedure Call) interactions.

## Features

- Voice interaction with users via LiveKit
- Support for multiple languages
- RPC-based interaction handling for:
  - Component clicks
  - Screen changes
  - Transcribed text
  - Task management (start, end, skip)
- Transcript recording and storage

## Architecture

The application is structured as follows:

```
worker/
├── agent.py                # Main agent entry point
├── manager/                # Managers for different services
│   ├── rpc_manager.py      # Main RPC manager
│   └── rpc/                # RPC handlers
│       ├── interaction_handler.py  # Handles interaction events
│       └── task_handler.py         # Handles task events
├── services/               # Service clients
│   └── db_service.py       # Database service client
├── plugins/                # LiveKit plugins
└── transcripts/            # Directory for storing transcripts
```

## RPC Protocol

The application uses LiveKit's built-in RPC functionality to register and handle method calls. The following RPC methods are registered:

### Interaction Methods

- `handleComponentClick`: Process component click events
- `handleScreenChange`: Process screen change events
- `handleTranscribedText`: Process transcribed text events

### Task Methods

- `handleTaskStart`: Process task start events
- `handleTaskEnd`: Process task end events
- `handleTaskSkip`: Process task skip events

## Client-Side Implementation

To invoke these RPC methods from the client side, use the LiveKit RPC API:

```javascript
// Example: Invoke component click handler
const response = await localParticipant.performRpc({
  destinationIdentity: "agent-identity",
  method: "handleComponentClick",
  payload: JSON.stringify({
    tenantId: "tenant-id",
    fileKey: "file-key",
    frameId: "frame-id",
    nodeId: "node-id",
    newFrameId: "new-frame-id",
    timestamp: Date.now(),
    animation: false,
  }),
});

console.log("RPC response:", response);
```

## Setup and Installation

1. Install dependencies:

```bash
pip3 install -r requirements.txt
```

2. Set up environment variables in `.env`:

```
LIVEKIT_URL=wss://your-livekit-server
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
DB_SERVICE_URL=http://your-db-service
```

3. Run the agent:

```bash
python3 agent.py
```

## Development

To add new RPC methods:

1. Create a new handler file in `worker/manager/rpc/`
2. Implement the handler class with appropriate RPC methods
3. Register the handler in `worker/manager/rpc_manager.py`
4. Register the RPC methods in the handler's `_register_rpc_methods` function

## License

This project is licensed under the MIT License - see the LICENSE file for details.
