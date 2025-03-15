#!/usr/bin/env python3
import os
import sys
import argparse
from dotenv import load_dotenv

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from worker.services.sarvam import SarvamAI, LanguageCode
from worker.plugins.sarvam import Translator

def main():
    """Test the Sarvam translation functionality"""
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Test Sarvam translation functionality")
    parser.add_argument("--text", type=str, default="Hello, how can I help you today?", 
                        help="Text to translate")
    parser.add_argument("--source", type=str, default="en-IN", 
                        help="Source language code (e.g., en-IN)")
    parser.add_argument("--target", type=str, default="hi-IN", 
                        help="Target language code (e.g., hi-IN)")
    args = parser.parse_args()
    
    # Get API key from environment
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        print("Error: SARVAM_API_KEY environment variable is not set")
        sys.exit(1)
    
    # Create translator
    translator = Translator()
    
    # Translate text
    try:
        print(f"Translating: '{args.text}'")
        print(f"From: {args.source} to {args.target}")
        
        translated_text = translator.translate(
            text=args.text,
            source_language=args.source,
            target_language=args.target
        )
        
        print(f"Translation: '{translated_text}'")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Test direct API call
    try:
        print("\nTesting direct API call:")
        client = SarvamAI(api_key=api_key)
        
        response = client.translate_text(
            input_text=args.text,
            source_language_code=args.source,
            target_language_code=args.target
        )
        
        print(f"API Response: '{response.translated_text}'")
    except Exception as e:
        print(f"API Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 