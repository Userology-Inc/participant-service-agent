#!/bin/bash

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the core agents package
pip3 install -e ./livekit-agents --config-settings editable_mode=strict
pip3 install -e ./livekit-plugins/livekit-plugins-openai --config-settings editable_mode=strict
pip3 install -e ./livekit-plugins/livekit-plugins-deepgram --config-settings editable_mode=strict
pip3 install -e ./livekit-plugins/livekit-plugins-elevenlabs --config-settings editable_mode=strict
pip3 install -e ./livekit-plugins/livekit-plugins-google --config-settings editable_mode=strict
pip3 install -e ./livekit-plugins/livekit-plugins-aws --config-settings editable_mode=strict
pip3 install -e ./livekit-plugins/livekit-plugins-anthropic --config-settings editable_mode=strict
pip3 install -e ./livekit-plugins/livekit-plugins-assemblyai --config-settings editable_mode=strict
pip3 install -e ./livekit-plugins/livekit-plugins-turn-detector --config-settings editable_mode=strict
pip3 install -e ./livekit-plugins/livekit-plugins-speechmatics --config-settings editable_mode=strict
pip3 install -e ./livekit-plugins/livekit-plugins-silero --config-settings editable_mode=strict


# Install additional dependencies
pip3 install -r worker/requirements.txt

echo "Installation complete! All LiveKit agents and plugins have been installed." 