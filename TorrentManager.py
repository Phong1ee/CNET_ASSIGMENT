import torf
import os

class TorrentManager:
    def __init__(self, torrent_directory):
        self.torrent_directory = torrent_directory

    def list_torrents(self):
        """Lists all torrents in the torrent directory."""
        # Use torf to list .torrent files in the directory
        # ...
        # torrent_manager = TorrentManager('/path/to/torrent/directory')
        # torrents = torrent_manager.list_torrents()
        # print("Torrents found:", torrents)
        try:
            if not os.path.exists(self.torrent_directory):
                raise FileNotFoundError(f"Directory not found: {self.torrent_directory}")
            
            torrents = [
                file for file in os.listdir(self.torrent_directory)
                if file.endswith('.torrent')
            ]
            return torrents
        except Exception as e:
            print(f"Error listing torrents: {e}")
            return []
             

    def check_torrent_status(self, torrent_hash):
        """Checks the status of a torrent by its hash."""
        # Check if the torrent file exists
        # Check if the torrent's files exist and are complete
        # ...

    def prepare_tracker_request(self, torrent_file):
        """Prepares a tracker request."""
        # Get the torrent info using torf
        # Construct the request parameters: info_hash, peer_id, event, uploaded, downloaded, left
        # ...
