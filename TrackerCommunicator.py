from time import sleep
from typing import Optional
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
        self.url = url
        self.downloadManager = downloadManager
        self.uploadManager = uploadManager
        self.announce_interval = 0
        self.host = host
        self.port = port
        self.id = id
        self.announced_torrents: set[str] = set()

    def download_announce(self, torrent_file: Torrent):
        params = self._prepare_announce_request("started", torrent_file)
        return self._send_announce_request(params)

    def upload_announce(self, torrent_file: Torrent):
        params = self._prepare_announce_request("completed", torrent_file)
        self.announced_torrents.add(torrent_file.infohash)
        self._send_announce_request(params)

    def regular_announce(self):
        # Periodically announce updates for downloaded/uploaded data
        for infohash in self.announced_torrents:
            params = self._prepare_announce_request(infohash=infohash)
            self._send_announce_request(params)
        # Sleep for the specified interval
        sleep(self.announce_interval)

    def stopping_announce(self):
        for infohash in self.announced_torrents:
            params = self._prepare_stopping_announce(infohash)
            self._send_announce_request(params)

    def handle_response(self, resp: requests.Response):
        """Handle the response from the tracker
        Args:
            resp (requests.Response): Response from the tracker
        Returns:
            peers (list): List of peers received from the tracker
        """
        raw_resp = bencodepy.decode(resp.content)
        decoded_resp = {k.decode("utf-8"): v for k, v in raw_resp.items()}
        if "failure reason" in decoded_resp:
            print(
                f"[Handle Response] Response from tracker {decoded_resp['failure reason']}"
            )
            return None

        announce_interval = int(decoded_resp["interval"])
        self.announce_interval = announce_interval

        peers = decoded_resp["peers"]
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
            # print("[Handle Response] No peers found in the response.")
            return None

    def _prepare_announce_request(
        self,
        event: str = "",
        torrent_file: Optional[Torrent] = None,
        infohash: str = "",
    ):
        """Base for preparing an announce request to the tracker
        Args:
            event (str): The event type of the announce request
            torrent_file (Torrent): The torrent file object
            infohash (str): The infohash of the torrent
        Returns:
            params (dict): The parameters for the announce request
        """
        if torrent_file is not None:
            infohash = torrent_file.infohash
        else:
            infohash = infohash

        if event == "completed":
            left = 0
        elif event == "started":
            left = torrent_file.size
        else:  # TODO: Fix this, left should be the bytes left to download
            left = 0
        params = {
            "info_hash": infohash,
            "peer_id": self.id,
            "ip": self.host,
            "port": self.port,
            # "uploaded": self.uploadManager.get_total_uploaded_infohash(infohash),
            # "downloaded": self.downloadManager.get_total_downloaded_infohash(infohash),
            "left": left,
            "compact": 0,
            "event": event,
            "numwant": 0,
        }
        return params

    def _prepare_stopping_announce(self, infohash):
        params = {
            "info_hash": infohash,
            "peer_id": self.id,
            "ip": self.host,
            "port": self.port,
            "left": 0,
            "event": "stopped",
        }
        return params

    def _send_announce_request(self, params):
        try:
            resp = requests.get(url=self.url + "/announce", params=params)
            resp.raise_for_status()  # Raise an exception for error HTTP statuses

            peer_list = self.handle_response(resp)
            if "event" in params and params["event"] == "started":
                self.announced_torrents.add(
                    params["info_hash"]
                )  # Track announced torrents
            return peer_list

        except requests.exceptions.RequestException as e:
            print(
                f"[ERROR-TrackerCommunicator-_send_announce_request] Request failed: {e}"
            )
            raise  # Re-raise the exception to propagate the error
