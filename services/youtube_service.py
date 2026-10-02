from urllib.parse import urlparse, parse_qs


def extract_video_id(url):
    """
    Extract the YouTube video ID from a YouTube URL.
    """

    try:
        parsed_url = urlparse(url)

        hostname = parsed_url.hostname

        if not hostname:
            return None

        hostname = hostname.lower()

        # ---------------------------------
        # Normal YouTube URL
        # https://www.youtube.com/watch?v=VIDEO_ID
        # ---------------------------------

        if "youtube.com" in hostname:

            query_parameters = parse_qs(
                parsed_url.query
            )

            video_id = query_parameters.get("v")

            if video_id:
                return video_id[0]

        # ---------------------------------
        # Short YouTube URL
        # https://youtu.be/VIDEO_ID
        # ---------------------------------

        if "youtu.be" in hostname:

            video_id = parsed_url.path.strip("/")

            if video_id:
                return video_id.split("/")[0]

        # ---------------------------------
        # YouTube Shorts
        # https://www.youtube.com/shorts/VIDEO_ID
        # ---------------------------------

        if "youtube.com" in hostname:

            path_parts = (
                parsed_url.path
                .strip("/")
                .split("/")
            )

            if (
                len(path_parts) >= 2
                and path_parts[0] == "shorts"
            ):
                return path_parts[1]

        return None

    except Exception:

        return None