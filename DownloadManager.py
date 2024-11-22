import queue
import socket
import threading
from threading import Thread

from torf import Torrent
from FileManager import FileManager
from PieceManager import PieceManager
from PeerCommunicator import PeerCommunicator


class DownloadManager:
    def __init__(
        self,
        id: str,
        dest_dir: str,
        fileManager: FileManager,
    ):
        """Initialize a DownloadManager object

        Args:
            id (str): The ID of the client
            destination_path (str): Path the to desired download folder
            fileManager (FileManager.FileManager): FileManager object
        """
        self.dest_dir = dest_dir
        self.fileManager = fileManager
        self.id = id

        self.download_rate: dict[str, float] = {}
        self.downloaded_total: dict[str, int] = {}
        self.num_connected_peers: dict[str, int] = {}

        self.active_downloads: dict[
            str, dict
        ] = {}  # A dictionary to store active downloads
        self.lock = threading.Lock()

    def new_download(self, torrent: Torrent, peer_list: list):
        """Start a new torrent download

        Args:
            torrent (Torrent object): Torrent object
            destination_path (str): Path the to desired download folder
        """
        with self.lock:
            infohash = torrent.infohash
            self.active_downloads[infohash] = {
                "peer_list": peer_list,
                "torrent": torrent,
                "download_info": {},
                "download_thread": Thread(target=self._download, args=(infohash,)),
                "downloaded_data": [],
                "remaining_pieces": 0,
            }
            self.active_downloads[infohash]["download_thread"].start()

    def _download(self, infohash: str):
        """Starts the download process by initializing the necessary tracking classes and variables to capture the download progress. After initialization, assign pieces to peers and start a _download_piece_thread() for each piece.

        Args:
            infohash: The infohash of the torrent.
        """
        download_info = self.active_downloads[infohash]["download_info"]

        # Initialize the piece manager and peer communicator
        pieceManager = PieceManager(download_info["torrent"])
        peerCommunicator = PeerCommunicator()

        # Initialize piece index queue
        piece_index_queue: queue.Queue[int] = queue.Queue()
        for piece_idx in range(download_info["torrent"].num_pieces):
            piece_index_queue.put(piece_idx)

        # Assign pieces to peers
        peer_idx = 0
        while not piece_index_queue.empty():
            piece_idx = piece_index_queue.get()

            # Connect to a peer
            socket = self._connect_peer(
                infohash,
                self.active_downloads[infohash]["peer_list"][peer_idx],
                peerCommunicator,
            )
            if socket is not None:
                # Request the piece
                pass
            else:
                # Put the index back to the queue
                piece_index_queue.put(piece_idx)

    def _download_piece_thread(self, piece_index: int):
        """Downloads a specific piece.

        Args:
            piece_index: The index of the piece to download.
        """
        while True:
            # Select a peer with the piece
            # Request the piece
            # Receive the piece
            # Verify the piece
            # Update the bitfield
            # Write the piece to disk
            # ... (Implement download logic)
            pass
        pass

    def _connect_peer(
        self,
        infohash: str,
        peer_info: tuple[str, str, int],
        peerCommunicator: PeerCommunicator,
    ):
        """Connects and handshakes a peer and returns a socket object.

        Args:
            infohash (str): The infohash of the torrent.
            peer_info (tuple): A tuple containing the peer's IP address and port.
            peerCommunicator (PeerCommunicator): PeerCommunicator object.

        Returns:
            A socket object if the connection is successful, None otherwise.
        """
        ip = peer_info[1]
        port = peer_info[2]

        try:
            # Connect to the peer
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, port))

            return s
        except Exception as e:
            print(
                f"[Connect Peer] Error while connecting to peer {ip}:{port}: {e}"
                in {self.active_downloads[infohash]["torrent"].name()}
            )
            return None

    def _request_piece(self, socket, piece_index):
        """Requests a piece from a peer.

        Args:
            socket (socket object): The socket object connected to the peer.
            piece_index: The index of the piece to request.

        Returns:
            True if the peer has the piece, False otherwise.
        """

    def get_total_downloaded(self):
        """Returns the total downloaded size."""
        with self.lock:
            return sum(self.downloaded_total.values())

    def get_total_downloaded_infohash(self, infohash: str):
        """Returns the total downloaded size for the supplied infohash.
        Args:
            infohash (str): The infohash of the torrent.
        Returns:
            The total downloaded size
        """
        with self.lock:
            return self.downloaded_total[infohash]

    def get_bytes_left(self, infohash: str):
        """Get the number of bytes left to download for a specific torrent.
        Args:
            infohash (str): The infohash of the torrent.
        Returns:
            The number of bytes left to download.
        """
        with self.lock:
            return self.active_downloads[infohash]["download_info"]["remaining"]

    def get_download_rate(self):
        """Calculates the current download rate."""
        # ... (Implement rate calculation logic, e.g., using a timer and tracking bytes downloaded)

    def get_download_status(self, download_id):
        # ... (Return the status of a download, e.g., progress, speed, remaining time)
        pass

    def get_remaining_size(self):
        """Returns the remaining size to be downloaded."""
        pass

    def get_number_of_connected_peers(self):
        """Returns the number of connected peers."""
        pass

    def get_num_downloading(self):
        """Returns the number of downloading files."""
        return len(self.active_downloads)

    def get_file_size(self):
        """Returns the total file size."""
        pass

    def get_file_name(self):
        """Returns the file name."""
        pass

    def write_file(self):
        """Writes the downloaded pieces to the destination file."""
        # ... (Implement file writing logic using the FileManager)

    def send_info_to_ui(self):
        """Sends the information of the download process to UI"""
        pass

    # Other methods for managing downloads, such as prioritizing, limiting bandwidth, etc.
