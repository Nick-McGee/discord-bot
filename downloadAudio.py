from pytube.__main__ import YouTube
import pytube.request
from pytube import Search
from pytube import Stream
import re
import sys
import os

# Compile regex pattern beforehand, speeds up time if ran a lot.
pattern = re.compile(r'(?<!^)(?=[A-Z])')
# Set downloads in 0.25MB chunks.
pytube.request.default_range_size = 500000


class getAudio:
    def __init__(self) -> None:
        self.title = None
        self.fileSize = None
        self.currFiles = set(os.listdir('./music'))

    def cleanName(self, title: str) -> str:
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
        print('{0} progress: {1:.2f}%'.format(self.title,
              100.0 - (bytes_remaining / self.fileSize) * 100.0))

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
        print('Downloaded \"{0}\" to {1}'.format(stream.title, file_path))

    def download(self, audio: YouTube, title: str) -> None:
        '''
        Download an audio file from YouTube. Saves audio file as .mp3 to the directory 
        ./music in the current directory.

        Parameters:
        title (str): The title of the video which will be saved.
        audio (YouTube): A YouTube object of the queried title.

        Return:
        None
        '''
        audio.register_on_progress_callback(self._on_progress_callback)
        audio.register_on_complete_callback(self._on_complete_callback)
        audio = audio.streams.get_audio_only()
        self.fileSize = audio.filesize
        audio.download(filename=title, output_path='./music')

    def retrieveFile(self, searchQuery: str) -> list:
        '''
        Check if a YouTube video exists and has already been downloaded. If not downloaded, 
        will request to download. Can search by either YouTube URL, or by search text. If 
        search text is used, the first search result will be downloaded.

        Parameters:
        searchQuery (str): 

        Return:
        list(bool, str, str): Return if file retrieved, the YouTube title name, and the filepath.
        '''
        try:
            audio = Search(searchQuery)
            audio = audio.results[0]
            self.title = self.cleanName(audio.title) + '.mp3'
        except:
            print('File not found.')
            return (False, 'None', 'None')

        if self.title not in self.currFiles:
            self.download(audio, self.title)
            self.currFiles.add(self.title)
        else:
            print(self.title, 'already downloaded!')
        
        return (True, audio.title, './music' + self.title)


def main(searchQuery):
    musicQueue = ['big iron', 'kanye west waves', 'marty robbins el paso']

    audioManager = getAudio()
    for music in musicQueue:
        print(audioManager.retrieveFile(music))


if __name__ == '__main__':
    if len(sys.argv) > 2:
        main(sys.argv[1:])
    else:
        print('ERROR: No search query given.')
