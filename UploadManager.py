from FileManager import FileManager


class UploadManager:
    def __init__(self, target_path: str, fileManager: FileManager):
        """Initialize the UploadManager object.
        Args:
            target_path (str): Path to the folder storing the torrents
        """
        self.target_path = target_path
        self.fileManager = fileManager

        def upload_torrent(torrent_path: str):
            """Upload a torrent to the tracker.
            Args:
                torrent_path (str): Path to the torrent file.
            """
            pass

        def get_num_downloading(self):
            """Get the number of downloading files.
            Returns:
                The number of downloading files.
            """
            pass
