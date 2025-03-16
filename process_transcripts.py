import json
import os

def process_transcripts(input_file):
    # Read the input JSON file
    with open(input_file, 'r') as f:
        transcripts = json.load(f)
    
    # Get the first start time as reference
    reference_time = transcripts[0]['start']
    print(f"Reference time: {reference_time}")
    
    # Process each transcript
    for transcript in transcripts:
        # Replace start and end with relative times
        transcript['start'] = round(transcript['start'] - reference_time, 3)
        transcript['end'] = round(transcript['end'] - reference_time, 3)
        
        # Process words if they exist
        if 'words' in transcript and transcript['words']:
            for word in transcript['words']:
                # Replace word times with relative times
                word['start'] = round(word['start'] - reference_time, 3)
                word['end'] = round(word['end'] - reference_time, 3)
    
    # Generate output filename
    base_name = os.path.splitext(input_file)[0]
    output_file = f"{base_name}_modified.json"
    
    # Write the modified data to new file
    with open(output_file, 'w') as f:
        json.dump(transcripts, f, indent=2)
    
    print(f"Processed file saved as: {output_file}")

if __name__ == "__main__":
    input_file = "worker/transcripts/playground-dlW5-NA5M_transcripts.json"
    process_transcripts(input_file) 