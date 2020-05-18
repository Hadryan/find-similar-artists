from spotipy import Spotify, SpotifyException
import requests
from bs4 import BeautifulSoup


# There were issues with passing instance objects to redis, which is the reason I need to go for the approach
# where I pass the Spotify object to every method


def get_artist(name: str, sp: Spotify):
    """
    Search Spotify for an artist
    :param name: name of artist
    :param sp: Spotify object to be used with the API query
    :return: the top search result artist
    """
    try:
        results = sp.search(q='' + name, type='artist', limit=1)
    except SpotifyException as e:
        print(e)
        return None
    items = results['artists']['items']
    if len(items) > 0:
        # Get the top search result
        return items[0]
    else:
        print(name + ": no matches on Spotify")
        return None


def get_top_tracks(artist_id: str, sp: Spotify):
    try:
        top_tracks = sp.artist_top_tracks(artist_id)
    except SpotifyException as e:
        print(e)
        return None
    if len(top_tracks['tracks']) == 0:
        # Handle the case of no top tracks.
        print(top_tracks)
        print("No top tracks found")
        return None
    return top_tracks


def create_and_populate_playlist(playlist_name: str, track_ids: list, sp: Spotify):
    try:
        playlist = sp.user_playlist_create(sp.me()['id'], playlist_name, public=True,
                                           description='generated by '
                                                       'FindSimilarArtists')
        playlist_id = playlist['uri']
        sp.user_playlist_add_tracks(sp.me()['id'], playlist_id, track_ids)
        return playlist_id
    except SpotifyException as e:
        print(e)
        return None
    except Exception as e:
        print(e)
        return None


def scrape_music_map(artist: str):
    """
        :param artist: name of the artist
        :return: a list of similar artists
    """
    result = []
    url = f"https://www.music-map.com/{artist}"
    try:
        page = requests.get(url)
    except requests.exceptions.RequestException as e:
        print(e)
        return result

    if page.status_code != 200:
        print("Page load unsuccesful")
        return result

    soup = BeautifulSoup(page.text, 'html.parser')
    sw = soup.find('div', id='gnodMap')

    if sw is None:
        print("artist not found / div gnodMap not found")

    similar_artists = sw.find_all('a', class_='S')

    if not similar_artists:
        print("no similar artists found. music-map html changed?")
    for artist in similar_artists:
        result.append(artist.text)

    return result  # The first artist in the list is the artist itself. Use to verify that correct artist was selected.


def generate_playlist(search: str, sp_user: Spotify, sp_app: Spotify, use_musicmap: bool = False):
    """
    Generates a playlist of top songs of similar artists.
    :param search: the name of the artist. Also supports Spotify URI or ID of the artist when use_musicmap is False
    :param sp_user: a Spotify object authenticated by the user who will be creating the playlist
    :param sp_app: a Spotify object authenticated by the app for a higher rate limit
    :param use_musicmap: True= uses music map for related artists, False = uses Spotify's related artists
    :return: a dict containing information on the playlist or nothing if the process failed.
    """
    uri_prefix = 'spotify:artist:'
    if use_musicmap:
        artist = get_artist(search, sp_user)
        if not artist:
            return False
        track_ids = generate_track_ids_musicmap(artist, sp_app)
    else:
        if search.startswith(uri_prefix) and not use_musicmap:
            artist = sp_user.artist(search)
        else:
            artist = get_artist(search, sp_user)
        if not artist:
            return "Artist not found"
        track_ids = generate_track_ids_spotify(artist, sp_user)
    if track_ids:
        playlist_name = artist['name'] + " recommendations"
        status = create_and_populate_playlist(playlist_name, track_ids, sp_user)
        if status:
            return status
        else:
            return "Playlist creation failed"
    else:
        print("track_ids is empty")
        return "No similar tracks found"


def generate_track_ids_musicmap(artist: dict, sp: Spotify):
    track_ids = []
    similar_artists = scrape_music_map(artist['name'])
    for artist in similar_artists:
        artist_id = get_artist(artist, sp)['uri']
        if artist_id is None:
            continue
        top_tracks = get_top_tracks(artist_id, sp)
        if not top_tracks:
            continue
        track = top_tracks['tracks'][0]['uri']
        track_ids.append(track)
    return track_ids


def generate_track_ids_spotify(artist: dict, sp: Spotify):
    track_ids = []
    artist_id = artist['uri']
    similar_artists = sp.artist_related_artists(artist_id)
    for artist in similar_artists['artists']:
        top_tracks = sp.artist_top_tracks(artist['uri'])
        if len(top_tracks['tracks']) == 0:
            # Handle the case of no top tracks.
            print(top_tracks)
            print("No top tracks found")
            continue
        track = top_tracks['tracks'][0]['uri']
        track_ids.append(track)
    return track_ids
