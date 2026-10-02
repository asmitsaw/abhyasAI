from services.transcript_service import get_transcript


video_id = "dQw4w9WgXcQ"


transcript = get_transcript(video_id)


if transcript:

    print("Transcript successfully retrieved!")

    print()

    print("First 1000 characters:")
    print(transcript[:1000])

else:

    print("Could not retrieve transcript.")