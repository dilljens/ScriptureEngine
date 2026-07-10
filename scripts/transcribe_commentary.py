#!/usr/bin/env python3
"""Transcribe all 66 Isaiah commentary MP3s using whisper."""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MP3_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "giliadi_books", "isaiah_commentary_mp3")
TEXT_DIR = os.path.join(MP3_DIR, "transcripts")
os.makedirs(TEXT_DIR, exist_ok=True)

import whisper

def transcribe_all():
    mp3_files = sorted([f for f in os.listdir(MP3_DIR) if f.endswith('.mp3') and os.path.isfile(os.path.join(MP3_DIR, f))])
    print(f"Found {len(mp3_files)} MP3 files to transcribe")
    
    model = whisper.load_model('base')
    total_start = time.time()
    
    for i, fname in enumerate(mp3_files):
        txt_path = os.path.join(TEXT_DIR, fname.replace('.mp3', '.txt'))
        json_path = os.path.join(TEXT_DIR, fname.replace('.mp3', '.json'))
        
        if os.path.exists(txt_path) and os.path.getsize(txt_path) > 0:
            print(f"  [{i+1}/{len(mp3_files)}] Skipping {fname} (already transcribed)")
            continue
        
        mp3_path = os.path.join(MP3_DIR, fname)
        size_mb = os.path.getsize(mp3_path) / (1024 * 1024)
        
        print(f"  [{i+1}/{len(mp3_files)}] Transcribing {fname} ({size_mb:.0f}MB)...", flush=True)
        t0 = time.time()
        
        try:
            result = model.transcribe(mp3_path, language='en')
            elapsed = time.time() - t0
            
            # Save full text
            with open(txt_path, 'w') as f:
                f.write(result['text'].strip())
            
            # Save segments with timestamps as JSON
            segments = []
            for seg in result['segments']:
                segments.append({
                    'id': seg['id'],
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': seg['text'].strip(),
                })
            
            with open(json_path, 'w') as f:
                json.dump({'segments': segments, 'text': result['text'].strip()}, f, indent=2)
            
            mins = elapsed / 60
            print(f"    ✓ {len(segments)} segments, {elapsed:.0f}s ({mins:.1f} min), text saved to {os.path.basename(txt_path)}")
            
        except Exception as e:
            print(f"    ✗ ERROR: {e}")
    
    total_elapsed = time.time() - total_start
    print(f"\nDone! Total time: {total_elapsed/60:.1f} minutes")
    
    # Count transcribed
    transcribed = sum(1 for f in os.listdir(TEXT_DIR) if f.endswith('.txt'))
    total_text = sum(os.path.getsize(os.path.join(TEXT_DIR, f)) for f in os.listdir(TEXT_DIR) if f.endswith('.txt'))
    print(f"Transcribed: {transcribed}/{len(mp3_files)} chapters ({total_text/1024:.0f}KB total)")

if __name__ == '__main__':
    transcribe_all()
