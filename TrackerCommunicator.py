import time

import bencodepy
import requests
from torf import Torrent
from DownloadManager import DownloadManager
from UploadManager import UploadManager


class TrackerCommunicator:
    def __init__(
        self,
        id: str,
        url: str,
        downloadManager: DownloadManager,
        uploadManager: UploadManager,
        host: str,
        port: int,
    ):
        """Initialize a TrackerCommunicate object, generating a random PeerID
        Args:
            id (str): The ID of the client
            url (str): URL of the tracker
            downloadManager (DownloadManager): DownloadManager object
            uploadManager (UploadManager): UploadManager object
            host (str): IP address of the client
            port (int): Port number of the client
        """
        self.url = url
        self.downloadManager = downloadManager
        self.uploadManager = uploadManager
        self.announce_interval = 0
        self.host = host
        self.port = port
        self.id = id

    def download_announce(self, torrent_file):
        """Announce to server by GET request with the initial params, receive response from the tracker
        Args:
            torrent_file (str): Path to the torrent file
        """
        params = self._prepare_download_request(torrent_file)
        try:
            resp = requests.get(url=self.url, params=params)
            peers = self.handle_response(resp)
            return peers
        except Exception as e:
            print("[Announce Error] ", e)

    def regular_announce(self):
        """Announce every self.announce_interval to the tracker"""
        # TODO: fix this
        while True:
            # Announce to the tracker
            self.announce_to_tracker()
            # Sleep for the specified interval
            time.sleep(self.announce_interval)

    def stopping_announce(self):
        """Announce to tracker that this client is stopping"""
        params = self._prepare_regular_announce(infohash, event="stopped")
        try:
            resp = requests.get(self.url, params=params)
        # handle connection error or other errors here, let's hope there is not any
        except Exception as e:
            print("[Stopping Announce] ", e)
        return 0

    def handle_response(self, resp: requests.Response):
        resp = bencodepy.decode(resp.content)
        resp = {k.decode("utf-8"): v for k, v in resp.items()}
        if "failure reason" in resp:
            print(f"[Error] Response from tracker {resp['failure reason']}")
            return 2

        announce_interval = int(resp["interval"])
        self.announce_interval = announce_interval

        peers = resp["peers"]
        for peer in peers:
            new_peer = {}
            for key, value in peer.items():
                new_key = key.decode("utf-8")
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                new_peer[new_key] = value
            peers[peers.index(peer)] = new_peer

        if peers:
            return peers
        else:
            return 3

    def _prepare_download_request(self, torrent_file, compact=0, numwant=50):
        """Prepares a tracker request to download a torrent.
        Args:
            torrent_file (str): Path to the torrent file
            compact (int): Whether to use compact response
            numwant (int): Number of peers to request
        """
        file = Torrent.read(torrent_file)
        params = {
            "info_hash": file.infohash,
            "peer_id": self.id,
            "ip": self.host,
            "port": self.port,
            "uploaded": 0,
            "downloaded": 0,
            "left": file.size,
            "compact": compact,
            "event": "started",
            "numwant": numwant,
        }
        return params

    def _prepare_regular_announce(self, infohash, event=None):
        """get the information from self.downloadManager and self.uploadManager to get the uploaded and downwloaded for the torrent"""
        params = {
            "info_hash": infohash,
            "peer_id": self.id,
            "ip": self.host,
            "port": self.port,
            "uploaded": self.uploadManager.get_total_uploaded(
                infohash
            ),  # Placeholder function, TODO
            "downloaded": self.downloadManager.get_total_downloaded(
                infohash
            ),  # Placeholder function, TODO
            "left": self.downloadManager.get_left(
                infohash
            ),  # Placeholder function, TODO
            "compact": 1,
            "event": event,
            "numwant": 0,
        }
        return params

    def get_id(self):
        return self.id
