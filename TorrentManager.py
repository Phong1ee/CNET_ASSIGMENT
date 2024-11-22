import torf
import os


class TorrentManager:
    def __init__(self, torrent_directory):
        self.torrent_directory = torrent_directory

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
