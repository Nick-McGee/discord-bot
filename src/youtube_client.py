import os
import logging

from requests import head, ConnectionError
from yt_dlp import YoutubeDL as yt
from yt_dlp import DownloadError
from pytube import Playlist
from urlvalidator import validate_url, ValidationError

import config.logger


def get_audio(query: str) -> dict | None:
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


def _get_entry_from_youtube(query: str) -> dict | None:
    entry = None
    tries = 3

# 'cookiefile': f"{os.path.join(os.path.dirname(__file__))}/config/youtube.com_cookies.txt"

    while entry is None and tries > 0:
        with yt({'format': 'bestaudio', 'age_limit': 21, 'noplaylist': 'True'}) as ytdl:
            try:
                if __is_url(query):
                    logging.info('Queuing by URL')
                    info = ytdl.extract_info(query, download=False)
                    entry = info
                else:
                    logging.info('Queuing by search')
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


@staticmethod
def __is_url(query):
    is_url = False
    try:
        validate_url(query)
        logging.debug('%s is a URL', query)
        is_url = True
    except ValidationError:
        logging.debug('%s not a URL', query)
    return is_url
