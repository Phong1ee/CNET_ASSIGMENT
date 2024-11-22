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

        self.upload_rate: dict[str, float] = {}
        self.uploaded_total: dict[str, int] = {}
        self.num_connected_peers: dict[str, int] = {}

        self.active_uploads: dict[
            str, dict
        ] = {}  # A dictionary to store active uploads
        self.lock = threading.Lock()
        self.stopping_event = threading.Event()

    def stop_upload(self):
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
                "download_info": {},
                "upload_thread": Thread(target=self._upload, args=(infohash,)),
            }
            self.active_uploads[infohash]["upload_thread"].start()

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
                client_socket, address = server_socket.accept()
                Thread(
                    target=self._upload_piece_thread,
                    args=(infohash, client_socket, address),
                ).start()
            except KeyboardInterrupt:
                break

    def _upload_piece_thread(
        self, infohash: str, client_socket: socket.socket, address: tuple[str, int]
    ):
        """Handle the upload of a piece to a peer.
        Args:
            infohash (str): The infohash of the torrent.
            client_socket (socket.socket): The client socket.
            address (tuple): The address of the client.
        """
        peer_communicator = PeerCommunicator()

        # Receive handshake from the peer
        requested_infohash, peer_id = peer_communicator.receive_handshake(client_socket)

        # Check if local torrent folder has the requested infohash
        torrent_exist = self.fileManager.check_local_torrent(requested_infohash)
        if not torrent_exist:
            client_socket.close()
            return

        # Get the torrent file path
        file_path = self.fileManager.get_file_path(requested_infohash)

        torrent = self.active_uploads[infohash]["torrent"]
        pieceManager = PieceManager(torrent)

        # Send handshake to the peer
        peer_communicator.send_handshake(client_socket, self.id, requested_infohash)

        # Send unchoke message to the peer
        peer_communicator.send_unchoke(client_socket)

        # Receive interested message from the peer
        peer_communicator.receive_interested(client_socket)

        # Get the bitfield of the torrent
        bitfield = pieceManager.generate_bitfield(file_path)

        # Send bitfield message to the peer
        peer_communicator.send_bitfield(client_socket, bitfield)

        # Receive request message from the peer
        piece_idx = peer_communicator.receive_request(client_socket)

        # Get the piece index and piece data
        piece_index, piece_data = pieceManager.get_piece(file_path, piece_idx)

        # Send piece message to the peer
        peer_communicator.send_piece(client_socket, piece_index, piece_data)

    def get_total_uploaded(self):
        """Get the total uploaded size.
        Returns:
            The total uploaded size.
        """
        with self.lock:
            return sum(self.uploaded_total.values())

    def get_total_uploaded_infohash(self, infohash: str):
        """Get the total uploaded size.
        Args:
            infohash (str): The infohash of the torrent.
        Returns:
            The total uploaded size.
        """
        with self.lock:
            return self.uploaded_total[infohash]

    def get_num_uploading(self):
        """Get the number of uploading files.
        Returns:
            The number of uploading files.
        """
        with self.lock:
            return len(self.active_uploads)
