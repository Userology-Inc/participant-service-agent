# Setup Guide

## Prerequisites

- Python 3.8+
- pip
- virtualenv (optional, but recommended)

## Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd participant-service-agent
   ```

2. Run the setup script:

   ```bash
   cd worker
   chmod +x setup.sh
   ./setup.sh
   ```

3. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

## Configuration

The application uses environment variables for configuration. You can:

1. Use the `.env` file in the root directory (already set up)
2. Export variables directly in your shell
3. Use a deployment-specific method (Docker secrets, Kubernetes ConfigMaps, etc.)

Required environment variables:

```
# LiveKit
LIVEKIT_URL=<livekit-url>
LIVEKIT_API_KEY=<livekit-api-key>
LIVEKIT_API_SECRET=<livekit-api-secret>
LIVEKIT_TRUNK_ID=<livekit-trunk-id>

# API Keys
OPENAI_API_KEY=<openai-api-key>
ELEVEN_API_KEY=<eleven-api-key>
ELEVENLABS_API_KEY=<elevenlabs-api-key>
DEEPGRAM_API_KEY=<deepgram-api-key>
PORTKEY_API_KEY=<portkey-api-key>
SARVAM_API_KEY=<sarvam-api-key>

# Database
DB_SERVICE_URL=<db-service-url>

# AWS
AWS_SECRET_ACCESS_KEY=<aws-secret-key>
AWS_ACCESS_KEY_ID=<aws-access-key-id>
AWS_REGION=<aws-region>

# Slack
SLACK_TOKEN=<slack-token>
SLACK_CHANNEL_ID=<slack-channel-id>
```

## Running the Service

To run the service:

```bash
python3 agent.py
```

## Development Setup

For development:

1. Install development dependencies:

   ```bash
   pip3 install -r requirements-dev.txt
   ```

2. Run tests:

   ```bash
   pytest
   ```

3. Run linting:
   ```bash
   flake8
   ```
