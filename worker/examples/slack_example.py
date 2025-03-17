import asyncio
import os
from dotenv import load_dotenv
from worker.services.slack import SlackClient

# Load environment variables
load_dotenv()

async def main():
    # Get the Slack client instance
    slack_client = SlackClient.get_instance()
    
    # Channel ID to send the message to
    channel_id = os.getenv("SLACK_CHANNEL_ID", "general")
    
    # Send a simple message
    try:
        response = await slack_client.send_message(
            slack_channel=channel_id,
            message="Hello from the Python Slack service!"
        )
        print(f"Message sent successfully: {response}")
        
        # Send a message in a thread
        thread_ts = response.get("ts")
        if thread_ts:
            thread_response = await slack_client.send_message(
                slack_channel=channel_id,
                message="This is a threaded reply!",
                options={"thread_ts": thread_ts}
            )
            print(f"Threaded message sent successfully: {thread_response}")
            
    except Exception as e:
        print(f"Error sending message: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 