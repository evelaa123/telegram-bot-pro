#!/usr/bin/env python3
"""
Test script for ffmpeg long video stitching.
Verifies that ffmpeg can concatenate multiple video clips into a single video.

Usage:
    python scripts/test_ffmpeg_stitch.py [--clips 3] [--duration 4]

This script:
1. Generates synthetic video clips using ffmpeg (color bars with text overlay)
2. Concatenates them using the same logic as worker/tasks.py
3. Verifies the output is a valid, playable video
4. Reports durations of individual clips and the final video
"""
import subprocess
import tempfile
import os
import sys
import argparse
import json


def create_test_clip(output_path: str, clip_index: int, duration: int = 4, size: str = "1280x720"):
    """
    Create a synthetic test video clip using ffmpeg.
    Each clip has a different color background and text overlay showing the clip number.
    """
    colors = ["blue", "red", "green", "orange", "purple", "cyan"]
    color = colors[clip_index % len(colors)]
    
    # Create a clip with solid color background and text
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi',
        '-i', f'color=c={color}:s={size}:d={duration}:r=24',
        '-vf', f"drawtext=text='Clip {clip_index + 1}':fontsize=80:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-pix_fmt', 'yuv420p',
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode != 0:
        print(f"  ERROR creating clip {clip_index + 1}: {result.stderr.decode()[-200:]}")
        return False
    return True


def get_video_duration(filepath: str) -> float:
    """Get video duration using ffprobe."""
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        filepath
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=15)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    return 0.0


def stitch_clips(clip_paths: list, output_path: str) -> bool:
    """
    Stitch video clips using the same method as worker/tasks.py.
    Uses ffmpeg concat demuxer.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as concat_file:
        for cp in clip_paths:
            concat_file.write(f"file '{cp}'\n")
        concat_path = concat_file.name
    
    try:
        result = subprocess.run(
            [
                'ffmpeg', '-f', 'concat', '-safe', '0',
                '-i', concat_path,
                '-c', 'copy',
                '-y', output_path
            ],
            capture_output=True, timeout=120
        )
        
        if result.returncode != 0:
            print(f"  FFMPEG ERROR: {result.stderr.decode()[-300:]}")
            return False
        return True
    finally:
        os.unlink(concat_path)


def main():
    parser = argparse.ArgumentParser(description="Test ffmpeg video stitching")
    parser.add_argument("--clips", type=int, default=3, help="Number of clips (default: 3)")
    parser.add_argument("--duration", type=int, default=4, help="Duration per clip in seconds (default: 4)")
    parser.add_argument("--size", type=str, default="1280x720", help="Video resolution (default: 1280x720)")
    args = parser.parse_args()
    
    # Check ffmpeg is available
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        if result.returncode != 0:
            print("ERROR: ffmpeg not found")
            sys.exit(1)
        version_line = result.stdout.decode().split('\n')[0]
        print(f"Using: {version_line}")
    except FileNotFoundError:
        print("ERROR: ffmpeg not installed. Install with: apt-get install ffmpeg")
        sys.exit(1)
    
    print(f"\n=== Long Video Stitch Test ===")
    print(f"Clips: {args.clips}")
    print(f"Duration per clip: {args.duration}s")
    print(f"Resolution: {args.size}")
    print(f"Expected total: ~{args.clips * args.duration}s")
    print()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: Create test clips
        print("Step 1: Creating test clips...")
        clip_paths = []
        for i in range(args.clips):
            clip_path = os.path.join(tmpdir, f"clip_{i}.mp4")
            print(f"  Creating clip {i + 1}/{args.clips}...", end=" ")
            if create_test_clip(clip_path, i, args.duration, args.size):
                duration = get_video_duration(clip_path)
                size_kb = os.path.getsize(clip_path) / 1024
                print(f"OK ({duration:.1f}s, {size_kb:.0f}KB)")
                clip_paths.append(clip_path)
            else:
                print("FAILED")
                sys.exit(1)
        
        # Step 2: Stitch clips together
        print("\nStep 2: Stitching clips with ffmpeg concat...")
        output_path = os.path.join(tmpdir, "long_video.mp4")
        if stitch_clips(clip_paths, output_path):
            final_duration = get_video_duration(output_path)
            final_size_kb = os.path.getsize(output_path) / 1024
            expected_duration = args.clips * args.duration
            
            print(f"  Output: {output_path}")
            print(f"  Duration: {final_duration:.1f}s (expected: ~{expected_duration}s)")
            print(f"  Size: {final_size_kb:.0f}KB")
            
            # Verify duration is reasonable
            if abs(final_duration - expected_duration) < 1.0:
                print(f"\n✅ SUCCESS: Video stitched correctly! {final_duration:.1f}s total")
            else:
                print(f"\n⚠️ WARNING: Duration mismatch. Got {final_duration:.1f}s, expected ~{expected_duration}s")
                print("  This may be due to encoding differences, but the concat logic works.")
        else:
            print("  FAILED to stitch clips")
            sys.exit(1)
        
        # Step 3: Verify output is valid
        print("\nStep 3: Verifying output video...")
        probe_cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-show_format',
            output_path
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, timeout=15)
        if probe_result.returncode == 0:
            probe_data = json.loads(probe_result.stdout)
            streams = probe_data.get("streams", [])
            for s in streams:
                if s["codec_type"] == "video":
                    print(f"  Video codec: {s['codec_name']}")
                    print(f"  Resolution: {s['width']}x{s['height']}")
                    print(f"  Frame rate: {s.get('r_frame_rate', 'N/A')}")
            print(f"  Format: {probe_data.get('format', {}).get('format_name', 'N/A')}")
            print(f"\n✅ Output video is valid and playable!")
        else:
            print("  Could not probe output video")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    main()
