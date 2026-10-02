# pyrefly: ignore [missing-import]
from youtube_transcript_api import YouTubeTranscriptApi


def get_transcript(video_id):
    """
    Fetch the transcript of a YouTube video.

    Returns:
        str: Combined transcript text.
    """

    try:

        api = YouTubeTranscriptApi()

        transcript = api.fetch(video_id)

        text = " ".join(
            snippet.text
            for snippet in transcript
        )

        return text

    except Exception as error:

        print(f"Transcript error: {error}")

        return None