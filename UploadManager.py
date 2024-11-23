import socket
import threading
from threading import Thread

from torf import Torrent

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
        fileManager: FileManager,
    ):
        """Initialize the UploadManager object.
        Args:
            id (str): The ID of the client.
            ip (str): The IP address of the client.
            port (int): The port number of the client.
            torrent_dir (str): The directory where the torrent files are stored.
            fileManager (FileManager): The FileManager object.
        """
        self.torrent_dir = torrent_dir
        self.fileManager = fileManager
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

    def new_upload(self, torrent: Torrent):
        """Upload a torrent to the tracker.
        Args:
            torrent (Torrent): The torrent object to upload.
        """
        with self.lock:
            infohash = torrent.infohash
            self.active_uploads[infohash] = {
                "peer_list": [],
                "torrent": torrent,
                "upload_rate": 0,
                "uploaded_total": 0,
                "num_connected_peers": 0,
                "upload_thread": Thread(target=self._upload, args=(infohash,)),
            }
            self.active_uploads[infohash]["upload_thread"].start()
            print(f"Started uploading {infohash}")

    def _upload(self, infohash: str):
        """Start listening for incoming peer connections and spawn a new thread _upload_piece_thread for each connection.
        Args:
            infohash (str): The infohash of the torrent.
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.ip, self.port))

        server_socket.listen(50)

        while not self.stopping_event.is_set():
            try:
                client_socket, _ = server_socket.accept()
                Thread(
                    target=self._upload_piece_thread,
                    args=(infohash, client_socket),
                ).start()
            except KeyboardInterrupt:
                break

    def _upload_piece_thread(
        self,
        infohash: str,
        client_socket: socket.socket,
    ):
        peer_communicator = PeerCommunicator(client_socket)

        # Receive handshake from the peer
        handshake = peer_communicator.receive_handshake()
        requested_infohash = handshake[28:48].hex()
        # print(
        #     "[INFO-UploadManager-_upload_piece_thread] Requested infohash:",
        #     requested_infohash,
        # )

        # Check if local torrent folder has the requested infohash
        torrent_exist = self.fileManager.check_local_torrent(requested_infohash)
        if not torrent_exist:
            print("[INFO-UploadManager-_upload_piece_thread] Torrent does not exist")
            client_socket.close()
            return None

        # Get the torrent file path
        file_path = self.fileManager.get_original_file_path(requested_infohash)
        # print("INFO-UploadManager-_upload_piece_thread] File path:", file_path)
        with self.lock:
            torrent = self.active_uploads[infohash]["torrent"]
        pieceManager = PieceManager(torrent, file_path)

        # Send handshake to the peer
        peer_communicator.send_handshake(self.id, infohash)

        # Send unchoke message to the peer
        peer_communicator.send_unchoke()

        # Receive interested message from the peer
        peer_communicator.receive_interested()

        # Get the bitfield of the torrent
        bitfield = pieceManager.bitfield
        # print("[INFO-UploadManager-_upload_piece_thread] Bitfield:", bitfield)

        # Send bitfield message to the peer
        peer_communicator.send_bitfield(bitfield)

        # Receive request message from the peer
        piece_idx = peer_communicator.receive_request()

        # Get the piece data
        piece_data = pieceManager.get_piece_data(piece_idx)

        # Send piece message to the peer
        peer_communicator.send_piece(piece_idx, piece_data)

    def get_total_uploaded(self):
        """Get the total uploaded size.
        Returns:
            The total uploaded size.
        """
        total_uploaded = 0
        with self.lock:
            for upload_info in self.active_uploads.values():
                total_uploaded += upload_info["uploaded_total"]
        return total_uploaded

    def get_total_uploaded_infohash(self, infohash: str):
        """Get the total uploaded size.
        Args:
            infohash (str): The infohash of the torrent.
        Returns:
            The total uploaded size.
        """
        with self.lock:
            return self.active_uploads[infohash]["uploaded_total"]

    def get_num_uploading(self):
        """Get the number of uploading files.
        Returns:
            The number of uploading files.
        """
        with self.lock:
            return len(self.active_uploads)
