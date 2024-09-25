from flask import Flask, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from transformers import pipeline

app = Flask(__name__)

# Load a summarization pipeline from Hugging Face  
summarizer = pipeline("summarization")

# Function to extract video ID from YouTube URL
def extract_video_id(url):
    if "youtube.com/watch?v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("/")[-1]
    return None

# Function to chunk text into smaller parts
def chunk_text(text, max_chunk_length=1000):
    sentences = text.split('. ')
    current_chunk = []
    chunks = []
    
    for sentence in sentences:
        if len(" ".join(current_chunk + [sentence])) <= max_chunk_length:
            current_chunk.append(sentence)
        else:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

# Route to serve the HTML page
@app.route('/')
def index():
    return render_template('index.html')

# API to handle video summarization
@app.route('/summarize', methods=['POST'])
def summarize_video():
    video_url = request.json.get("url")
    video_id = extract_video_id(video_url)
    
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400
    
    try:
        # Try to get the transcript from YouTube video
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([entry['text'] for entry in transcript])
        
        if len(text) < 50:  # Check if the transcript is too short
            return jsonify({"error": "The transcript is too short to summarize."}), 400
        
        # Break the text into chunks to avoid exceeding the summarizer's token limit
        chunks = chunk_text(text)
        
        # Summarize each chunk and combine the results
        summary = ""
        for chunk in chunks:
            summary_chunk = summarizer(chunk, max_length=150, min_length=50, do_sample=False)[0]['summary_text']
            summary += summary_chunk + " "
        
        return jsonify({"summary": summary.strip()})
    
    except NoTranscriptFound:
        return jsonify({"error": "No transcript available for this video."}), 404
    except TranscriptsDisabled:
        return jsonify({"error": "Transcripts are disabled for this video."}), 403
    except VideoUnavailable:
        return jsonify({"error": "This video is unavailable."}), 404
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)  