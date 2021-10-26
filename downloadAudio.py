import pytube.request
from pytube import Search
from pytube import Stream
import re
import sys

# Compile regex pattern beforehand, speeds up time if ran a lot.
pattern = re.compile(r'(?<!^)(?=[A-Z])')
# Set downloads in 0.25MB chunks.
pytube.request.default_range_size = 250000


def cleanName(title: str) -> str:
    '''
    Removes unwanted characters from YouTube video title to invalid filename on filesystem.
    Source: https://stackoverflow.com/a/46801075/4364154

    Paramaters:
    title (str): The name of the YouTube video

    Returns:
    str: A cleaned up version of the title for easier storage.
    '''
    title = str(title).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', title)


def _on_progress_callback(chunk: Stream, file_handle: bytes, bytes_remaining: int) -> None:
    '''
    In progress callback function from downloading a video or audio file. Called at every request.
    Request size set by pytube.request.default_range_size.

    Paramaters:
    chunk (Stream): Segment of media file binary data, not yet written to disk.
    file_handle (Bytes): The file handle where the media is being written to.
    bytes_remaining (int): How many bytes left to be downloaded.

    Returns:
    None
    '''
    print('MB Remaining:', bytes_remaining / 1000, 'MB')


def _on_complete_callback(stream: Stream, file_path: str) -> None:
    '''
    Completion callback function from downloading a video or audio file, listing both the YouTube 
    video title and the filepath the file was saved to.

    Paramaters:
    stream (Stream): The Stream object of the YouTube video.
    file_path (str): A string of the file path where the file was saved.

    Returns:
    None
    '''
    print('Downloaded \"{0}\" to {1}'.format(stream.title, file_path))


def download(searchQuery) -> None:
    '''
    Download an audio file from YouTube. Can search by either YouTube URL, or by search text.
    If search text is used, the first search result will be downloaded. Saves audio file as
    .mp3 to the directory ./music in the current directory.

    Paramaters:
    searchQuery (str): Either a string search query or YouTube URL link.

    Return:
    None
    '''
    audio = Search(searchQuery)
    audio = audio.results[0]
    audio.register_on_progress_callback(_on_progress_callback)
    audio.register_on_complete_callback(_on_complete_callback)
    audio = audio.streams.get_audio_only()
    title = cleanName(audio.title) + '.mp3'
    audio.download(filename=title, output_path='./music')


def main(searchQuery):
    download(searchQuery)


if __name__ == '__main__':
    if len(sys.argv) > 2:
        main(sys.argv[1:])
    else:
        print('ERROR: No search query given.')
