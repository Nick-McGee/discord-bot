import logging
from typing import Union

from requests import head, ConnectionError
from youtube_dl import YoutubeDL as yt
from youtube_dl import DownloadError
from pytube import Playlist

import config.logger


def get_audio(query: str) -> Union[dict, None]:
    entry = _get_entry_from_youtube(query=query)
    if entry:
        entry = {'audio_url': entry['url'],
                 'webpage_url': entry['webpage_url'],
                 'title': entry['title'],
                 'length': entry['duration'],
                 'thumbnail': entry['thumbnail']
        }
    return entry


def get_playlist(playlist_url: str) -> Playlist:
    return Playlist(url=playlist_url)


def _get_entry_from_youtube(query: str) -> Union[dict, None]:
    entry = None
    tries = 3

    while entry is None and tries > 0:
        with yt({'format': 'bestaudio', 'age_limit': 21, 'noplaylist': 'True', 'cookiefile': 'config/youtube.com_cookies.txt'}) as ytdl:
            try:
                info = ytdl.extract_info(f'ytsearch:{query}', download=False)
                first_entry = info['entries'][0]
                status_code = head(first_entry['url']).status_code
                logging.info('Query status code: %s', status_code)
                if status_code == 200:
                    entry = first_entry
            except (TypeError, IndexError) as type_index_error:
                logging.error('No entries found: %s', type_index_error)
            except KeyError as key_error:
                logging.error('Key not found: %s', key_error)
            except ConnectionError as connection_error:
                logging.error('Unable to connect: %s', connection_error)
            except DownloadError as download_error:
                logging.error('Error downloading: %s', download_error)
            finally:
                tries -= 1

    return entry
