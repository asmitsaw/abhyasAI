from services.youtube_service import extract_video_id


url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


video_id = extract_video_id(url)


print("YouTube URL:")
print(url)

print()

print("Extracted Video ID:")
print(video_id)