from pytube.__main__ import YouTube
import pytube.request
from pytube import Search
from pytube import Stream
import re
import sys

# Compile regex pattern beforehand, speeds up time if ran a lot.
pattern = re.compile(r'(?<!^)(?=[A-Z])')
# Set downloads in 0.25MB chunks.
pytube.request.default_range_size = 500000


class Audio:
    '''
    Audio is the return type for GetAudio.retrieveFile. It contains a bool if the file is downloaded,
    the title of the file from YouTube, and the directory of the file.

    Parameters:
    results(bool): If the file was downloaded or not.
    title(str): The title of the audio file from YouTube.
    directory(str): The directory where the audio file was saved to.
    '''

    def __init__(self, results: bool, title: str, directory: str) -> None:
        self.results = results 
        self.title = title
        self.directory = directory


class GetAudio:
    '''
    getAudio utilizes the PyTube library (https://pytube.io/en/latest/index.html). Call retrieveFile(query)
    with either a YouTube URL or search query as a string. The first result will be downloaded 
    to the directory ./music. While the object exists, the files in ./music are tracked, and if the file already
    exists it will be returned rather than downloading the file from YouTube.

    Parameters:
    fileSize(int): The max size in bytes an audio file can be.
    '''

    def __init__(self, fileSize: int) -> None:
        self.title = None
        self.fileSize = None
        self.maxFileSize = fileSize

    def _cleanName(self, title: str) -> str:
        '''
        Removes unwanted characters from YouTube video title to invalid filename on filesystem.
        Source: https://stackoverflow.com/a/46801075/4364154

        Parameters:
        title (str): The name of the YouTube video

        Returns:
        str: A cleaned up version of the title for easier storage.
        '''
        title = str(title).strip().replace(' ', '_')
        return re.sub(r'(?u)[^-\w.]', '', title)

    def _on_progress_callback(self, chunk: Stream, file_handle: bytes, bytes_remaining: int) -> None:
        '''
        In progress callback function from downloading a video or audio file. Called at every request.
        Request size set by pytube.request.default_range_size.

        Parameters:
        chunk (Stream): Segment of media file binary data, not yet written to disk.
        file_handle (Bytes): The file handle where the media is being written to.
        bytes_remaining (int): How many bytes left to be downloaded.

        Returns:
        None
        '''
        print('getAudio.py: {0} progress: {1:.2f}%'.format(self.title, 100.0 - (bytes_remaining / self.fileSize) * 100.0))

    def _on_complete_callback(self, stream: Stream, file_path: str) -> None:
        '''
        Completion callback function from downloading a video or audio file, listing both the YouTube 
        video title and the filepath the file was saved to.

        Parameters:
        stream (Stream): The Stream object of the YouTube video.
        file_path (str): A string of the file path where the file was saved.

        Returns:
        None
        '''
        print('getAudio.py: Downloaded \"{0}\" to {1}'.format(stream.title, file_path))

    def _download(self, audio: YouTube, title: str) -> bool:
        '''
        Download an audio file from YouTube. Saves audio file as .mp3 to the directory 
        ./music in the current directory.

        Parameters:
        title (str): The title of the video which will be saved.
        audio (YouTube): A YouTube object of the queried title.

        Returns:
        bool: True if file was downloaded, False if filesize was over max filesize.
        '''
        audio.register_on_progress_callback(self._on_progress_callback)
        audio.register_on_complete_callback(self._on_complete_callback)
        audio = audio.streams.get_audio_only()
        self.fileSize = audio.filesize

        if self.fileSize > self.maxFileSize:
            return False

        audio.download(filename=title, output_path='./music')
        return True

    def retrieveFile(self, searchQuery: str) -> Audio:
        '''
        Check if a YouTube video exists and has already been downloaded. If not downloaded, 
        will request to download. Can search by either YouTube URL, or by search text. If 
        search text is used, the first search result will be downloaded.

        Parameters:
        searchQuery (str): A search query or YouTube URL.

        Returns:
        Audio(bool, str, str): Returns an Audio object with file retrieved, the YouTube title name, and the filepath.
        '''
        try:
            if searchQuery[0:5] == 'https':
                audio = YouTube(searchQuery)
            else:
                audio = Search(searchQuery)         
                audio = audio.results[0]
        except Exception as e:
            print('getAudio.py retrieveFile:', e)
            return(Audio(False, None, None))

        self.title = self._cleanName(audio.title) + '.mp3'
        if self._download(audio, self.title):
            return(Audio(True, audio.title, './music/' + self.title))
        else:
            print('getAudio.py retrieveFile: Filesize too large.')
            return(Audio(False, None, None))


def main(searchQuery):
    audioManager = GetAudio(200000000)
    audioManager.retrieveFile(searchQuery)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(' '.join(sys.argv[1:]))
    else:
        print('ERROR: No search query given.')
