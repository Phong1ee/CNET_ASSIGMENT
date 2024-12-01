import socket
import threading
from threading import Thread

from Torrent import Torrent

from FileManager import FileManager
from PeerCommunicator import PeerCommunicator
from PieceManager import PieceManager


class UploadManager:
    def __init__(
        self,
        id: str,
        ip: str,
        port: int,
        torrent_dir: str,
        original_dir: str,
    ):
        self.torrent_dir = torrent_dir
        self.original_dir = original_dir
        self.id = id
        self.ip = ip
        self.port = port

        self.active_uploads: dict[
            str, dict
        ] = {}  # A dictionary to store active uploads
        self.lock = threading.Lock()
        self.stopping_event = threading.Event()

    def stop(self):
        """Stop the upload manager."""
        self.stopping_event.set()

    def run_server(self):
        """Act as a server, listening for connections from peers."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.ip, self.port))

        server_socket.listen(50)

        while not self.stopping_event.is_set():
            try:
                client_socket, _ = server_socket.accept()
                Thread(
                    target=self._upload_piece_thread,
                    args=(client_socket,),
                ).start()
            except KeyboardInterrupt:
                break

        server_socket.close()

    def new_upload(self, torrent: Torrent):
        with self.lock:
            infohash = torrent.infohash
            self.active_uploads[infohash] = {
                "torrent": torrent,
                "upload_rate": 0,
                "uploaded_total": 0,
                "num_connected_peers": 0,
            }

    def _upload_piece_thread(
        self,
        client_socket: socket.socket,
    ):
        peer_communicator = PeerCommunicator(client_socket)

        # Receive handshake from the peer
        handshake = peer_communicator.receive_handshake()
        infohash = handshake[28:48].hex()
        peer_id = handshake[48:].decode("utf-8")

        # Validate handshake
        val = peer_communicator.validate_handshake(handshake, infohash, peer_id)
        if not val:
            print("[INFO-UploadManager-_upload_piece_thread] Handshake failed")
            client_socket.close()
            return None

        # Check if local torrent folder has the requested infohash
        torrent_exist = FileManager.check_local_torrent(infohash, self.torrent_dir)
        if not torrent_exist:
            print("[INFO-UploadManager-_upload_piece_thread] Torrent does not exist")
            client_socket.close()
            return None

        with self.lock:
            torrent = self.active_uploads[infohash]["torrent"]
        pieceManager = PieceManager(torrent, self.original_dir)

        # Communicate with the peer
        peer_communicator.send_handshake(self.id, infohash)
        peer_communicator.send_unchoke()
        peer_communicator.receive_interested()
        peer_communicator.send_bitfield(pieceManager.generate_bitfield())

        while True:
            piece_idx = peer_communicator.receive_request()
            if piece_idx is None:
                break
            piece_data = pieceManager.get_piece_data(piece_idx)
            peer_communicator.send_piece(piece_idx, piece_data)
            # Update the total uploaded size
            with self.lock:
                self.active_uploads[infohash]["uploaded_total"] += len(piece_data)

        client_socket.close()

    def get_total_uploaded(self):
        total_uploaded = 0
        with self.lock:
            for upload_info in self.active_uploads.values():
                total_uploaded += upload_info["uploaded_total"]
        return total_uploaded

    def get_total_uploaded_infohash(self, infohash: str):
        with self.lock:
            return self.active_uploads[infohash]["uploaded_total"]

    def get_num_uploading(self):
        with self.lock:
            return len(self.active_uploads)
