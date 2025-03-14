# Timed Transcript Feature

This agent implementation includes a feature to capture and visualize word-level timing information for both user and agent speech in the conversation.

## Features

- Captures start and end times for each word spoken by the user and agent
- Logs detailed timing information to the console
- Saves individual speech segments as JSON files
- Creates a complete conversation transcript with timing information
- Generates an interactive HTML visualization with timeline view

## Output Files

When you run the agent, it will create a `timed_transcripts` directory containing:

1. Individual JSON files for each speech segment (user and agent)
2. A complete conversation transcript JSON file
3. An HTML visualization file with two views:
   - Conversation view: Shows the full conversation with timing details
   - Timeline view: Visualizes when each word was spoken on a timeline

## How to Use

1. Run the agent as usual
2. Interact with the agent through voice
3. Check the logs for timing information
4. After the conversation, examine the files in the `timed_transcripts` directory
5. Open the HTML visualization file in a web browser to see the interactive timeline

## Timing Data Format

The timing data is stored in the following format:

```json
{
  "text": "The full text of the speech segment",
  "start_time": 1234.56,
  "end_time": 1240.78,
  "words": [
    {
      "text": "word1",
      "start": 0.0,
      "end": 0.5,
      "confidence": 0.95
    },
    {
      "text": "word2",
      "start": 0.6,
      "end": 1.2,
      "confidence": 0.98
    }
  ]
}
```

## Implementation Details

The timing information is captured by:

1. Tracking word timing in the STT (Speech-to-Text) process for user speech
2. Tracking word timing in the TTS (Text-to-Speech) process for agent speech
3. Storing this information in the ChatMessage objects in the chat context
4. Emitting events when speech with timing information is available

This allows for detailed analysis of the conversation timing, including:
- How long each person spoke
- Pauses between words
- Overall conversation flow
- Turn-taking patterns 