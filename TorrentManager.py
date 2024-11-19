import torf

class TorrentManager:
    def __init__(self, torrent_directory):
        self.torrent_directory = torrent_directory

    def list_torrents(self):
        """Lists all torrents in the torrent directory."""
        # Use torf to list .torrent files in the directory
        # ...

    def check_torrent_status(self, torrent_hash):
        """Checks the status of a torrent by its hash."""
        # Check if the torrent file exists
        # Check if the torrent's files exist and are complete
        # ...

    def prepare_tracker_request(self, torrent_hash, event='started'):
        """Prepares a tracker request."""
        # Get the torrent info using torf
        # Construct the request parameters: info_hash, peer_id, event, uploaded, downloaded, left
        # ...