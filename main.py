import os
import re
import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spotify_downloader")

def extract_spotify_id(url):
    """
    Extract the Spotify type and ID from a Spotify URL.
    Returns a tuple (url_type, spotify_id) where url_type is one of "track", "album", or "playlist".
    """
    regex = r"open\.spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)"
    match = re.search(regex, url)
    if match:
        return match.group(1), match.group(2)
    return None, None

def build_query(track):
    """Build a search query using the track's artist(s) and title with 'official audio' appended."""
    artist = ", ".join([a["name"] for a in track.get("artists", [])])
    title = track.get("name", "")
    return f"{artist} - {title} official audio"

def sanitize_filename(name):
    """Remove illegal characters from a filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name)

def download_song(query, downloads_dir, base_filename, ffmpeg_path="ast"):
    """
    Download a song using yt_dlp.
    Uses an output template so that the final file is named <base_filename>.mp3.
    Returns the full path of the downloaded file (or None if it fails).
    """
    output_template = os.path.join(downloads_dir, f"{base_filename}.%(ext)s")
    final_filename = f"{base_filename}.mp3"
    final_path = os.path.join(downloads_dir, final_filename)
    
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "ffmpeg_location": ffmpeg_path,
        "retries": 3,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info("ytsearch:" + query, download=False)
            if "entries" in info and len(info["entries"]) > 0:
                video = info["entries"][0]
                video_url = video.get("webpage_url")
                logger.info(f"Found video: {video_url}")
                ydl.download([video_url])
                if os.path.exists(final_path):
                    return final_path
    except Exception as e:
        logger.error(f"Error downloading song: {e}")
    return None

def get_items_from_spotify(sp, url_type, spotify_id):
    """
    Given a Spotify URL type and ID, returns a tuple (items, name)
    - For a track: items is a list with one track object and name is the track's title.
    - For an album: items is a list of track objects (retrieved via sp.track) and name is the album name.
    - For a playlist: items is a list of track objects and name is the playlist name.
    """
    items = []
    name = ""
    try:
        if url_type == "track":
            track = sp.track(spotify_id)
            items.append(track)
            name = track.get("name", "Unknown Track")
        elif url_type == "album":
            album = sp.album(spotify_id)
            name = album.get("name", "Unknown Album")
            album_tracks = sp.album_tracks(spotify_id)['items']
            # For each track, retrieve full details
            for track_info in album_tracks:
                tid = track_info.get("id")
                if tid:
                    track_obj = sp.track(tid)
                    items.append(track_obj)
        elif url_type == "playlist":
            playlist = sp.playlist(spotify_id)
            name = playlist.get("name", "Unknown Playlist")
            for item in playlist["tracks"]["items"]:
                track_obj = item.get("track")
                if track_obj:
                    items.append(track_obj)
        else:
            raise ValueError("Unknown Spotify URL type encountered.")
        logger.info(f"Found {len(items)} track(s) in {url_type} '{name}'")
    except Exception as e:
        logger.error(f"Error fetching items from Spotify: {e}")
        raise
    return items, name

def main():
    # Here go the credentials, between the ""
    client_id = ""
    client_secret = ""
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id,
                                                               client_secret=client_secret))
    
    spotify_url = input("Enter Spotify URL (track/album/playlist): ").strip()
    url_type, spotify_id = extract_spotify_id(spotify_url)
    if not url_type or not spotify_id:
        logger.error("Invalid Spotify URL.")
        return
    
    try:
        items, collection_name = get_items_from_spotify(sp, url_type, spotify_id)
    except Exception as e:
        logger.error(f"Failed to fetch items: {e}")
        return
    
    downloads_dir = os.path.join(os.getcwd(), "downloads")
    if not os.path.exists(downloads_dir):
        os.makedirs(downloads_dir)
    
    # If a single track, download directly to downloads folder.
    if url_type == "track" or len(items) == 1:
        track = items[0]
        query = build_query(track)
        logger.info(f"Search query: {query}")
        artist = ", ".join([a["name"] for a in track.get("artists", [])])
        title = track.get("name", "")
        base_filename = sanitize_filename(f"{artist} - {title}")
        output_path = download_song(query, downloads_dir, base_filename, ffmpeg_path="ast")
        if output_path:
            logger.info(f"Downloaded song to {output_path}")
        else:
            logger.error("Failed to download the song.")
    else:
        # For album or playlist, create a folder with the collection name and download each track.
        collection_folder = os.path.join(downloads_dir, sanitize_filename(collection_name))
        if not os.path.exists(collection_folder):
            os.makedirs(collection_folder)
        
        logger.info(f"Downloading {len(items)} tracks into folder '{collection_folder}'")
        
        def process_track(track):
            q = build_query(track)
            artist = ", ".join([a["name"] for a in track.get("artists", [])])
            title = track.get("name", "")
            base_fn = sanitize_filename(f"{artist} - {title}")
            logger.info(f"Downloading track: {base_fn}")
            return download_song(q, collection_folder, base_fn, ffmpeg_path="ast")
        
        downloaded = []
        # You can use a ThreadPoolExecutor for concurrent downloads if desired.
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_track, track) for track in items]
            for future in futures:
                result = future.result()
                if result:
                    downloaded.append(result)
        
        if downloaded:
            logger.info(f"Successfully downloaded {len(downloaded)} tracks to '{collection_folder}'")
        else:
            logger.error("Failed to download any tracks from the collection.")

if __name__ == "__main__":
    main()
