import sys
import os

def main():
    print("=" * 60)
    print("🎙️ YouTube Lecture Transcription Pipeline (CLI Mode)")
    print("=" * 60)
    
    # Initialize pipeline
    from transcript_engine import TranscriptPipeline
    
    url = "https://www.youtube.com/watch?v=h0s3MmtS0Gc&list=PLKyB9RYzaFRjorE3KQgXorUpCNoxQYSCM"
    subject = "Microbology"
    course = "BT102"
    model = "small"
    output_dir = r"E:\documents\vu-plan-handouts"
    
    pipeline = TranscriptPipeline(
        model_name=model,
        subject_name=subject,
        course_code=course,
        output_base_dir=output_dir
    )
    
    # Resolve playlist
    print("🔍 Resolving playlist/video URL...")
    videos = pipeline.resolve_playlist(url, log_callback=lambda msg, lvl: print(msg))
    
    if not videos:
        print("No videos found.")
        return
        
    print(f"✅ Resolved {len(videos)} video(s)")
    
    def on_progress(current, total, title):
        print(f"\n[{current}/{total}] Transcribing: {title}")
        
    # Process all
    pipeline.process_all(
        progress_callback=on_progress,
        log_callback=lambda msg, lvl="info": print(msg)
    )
    print("\n✅ All done!")

if __name__ == "__main__":
    main()
