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
                "download_thread": Thread(target=self._download, args=(infohash,)),
                "downloaded_data": [],
                "download_rate": 0,
                "downloaded_total": 0,
                "num_connected_peers": 0,
                "remaining_pieces": 0,
            }
            self.active_downloads[infohash]["download_thread"].start()

    def _download(self, infohash: str):
        """Starts the download process by initializing the necessary tracking classes and variables to capture the download progress. After initialization, assign pieces to peers and start a _download_piece_thread() for each piece.

        Args:
            infohash: The infohash of the torrent.
        """
        download_info = self.active_downloads[infohash]

        # Initialize the piece manager
        pieceManager = PieceManager(
            download_info["torrent"], download_info["torrent"].name
        )

        # Initialize piece index queue
        piece_index_queue: queue.Queue[int] = queue.Queue()
        for piece_idx in range(download_info["torrent"].pieces):
            piece_index_queue.put(piece_idx)

        # Assign pieces to peers
        print("[INFO-DownloadManager-_download] Assigning pieces to peers")
        peer_idx = 0
        threads = []
        while not piece_index_queue.empty():
            piece_idx = piece_index_queue.get()
            print("Queue empty:", piece_index_queue.empty())

            # Connect to a peer
            socket = self._connect_peer(
                infohash,
                self.active_downloads[infohash]["peer_list"][peer_idx],
            )
            if socket is not None:
                # Request the piece
                thread = Thread(
                    target=self._download_piece_thread,
                    args=(
                        pieceManager,
                        piece_idx,
                        infohash,
                        socket,
                        self.active_downloads[infohash]["peer_list"][peer_idx][
                            "peer_id"
                        ],
                    ),
                )
                print("[INFO-DownloadManager-_download] Starting download thread")
                threads.append(thread)
                thread.start()
            else:
                # Put the index back to the queue
                print(
                    "[INFO-DownloadManager-_download] Peer connection failed, putting piece back to queue"
                )
                piece_index_queue.put(piece_idx)
            peer_idx = (peer_idx + 1) % len(download_info["peer_list"])

        # Wait for all threads to finish
        for thread in threads:
            thread.join()

        print("[INFO-DownloadManager-_download] Download complete")

        piece_data: dict[int, bytes] = pieceManager.get_all_piece_data()

        # Write the downloaded data to the destination file
        if download_info["torrent"].mode == "singlefile":
            dest_path = f"./download_test/{download_info['torrent'].name}"
            print(
                "[INFO-DownloadManager-_download] Writing single file to destination path:",
                dest_path,
            )
            self.fileManager.write_single_file(
                dest_path,
                piece_data,
                download_info["torrent"].piece_size,
            )
            print("[INFO-DownloadManager-_download] File written successfully")
        else:
            pass

    def _download_piece_thread(
        self,
        pieceManager: PieceManager,
        piece_index: int,
        infohash: str,
        socket: socket.socket,
        peer_id: str,
    ):
        peerCommunicator = PeerCommunicator(socket)
        # Send handshake
        peerCommunicator.send_handshake(self.id, infohash)
        # Receive handshake
        handshake = peerCommunicator.receive_handshake()
        # Validate handshake
        valid = peerCommunicator.validate_handshake(
            handshake,
            infohash,
            peer_id,
        )
        if valid:
            # Receive unchoke message
            peerCommunicator.receive_unchoke()
            # Send interested message
            peerCommunicator.send_interested()
            # Receive bitfield
            bitfield = peerCommunicator.receive_bitfield()
            # Check if peer has the piece
            # print(
            #     f"[INFO-DownloadManager-_download_piece_thread] Bitfield:{bitfield}, piece_idx:{piece_index}"
            # )
            if bitfield[piece_index] == 1:
                # Send request message
                peerCommunicator.send_request(piece_index)
                # Receive piece
                received_idx, piece_data = peerCommunicator.receive_piece()
                # print("received idx", received_idx)
                if received_idx != piece_index:
                    print(
                        f"[ERROR-DownloadManager-_download_piece_thread] Received piece {received_idx} does not match requested piece {piece_index}"
                    )
                    return None

                # Verify piece hash
                if pieceManager.verify_piece(piece_data, piece_index):
                    # Append piece data to the downloaded data
                    # print(
                    #     "[INFO-DownloadManager-_download_piece_thread] Piece verified"
                    # )
                    pieceManager.add_downloaded_piece(piece_data, piece_index)
                    print(
                        f"[INFO-DownloadManager-_download_piece_thread] Piece {piece_index} downloaded successfully"
                    )
                    return

                else:
                    print(
                        f"[ERROR-DownloadManager-_download_piece_thread] Piece {piece_index} hash verification failed"
                    )
                    return None
            else:
                print(
                    f"[INFO-DownloadManager-_download_piece_thread] Peer {peer_id} does not have piece {piece_index}"
                )
                return None
        else:
            print(
                f"[ERROR-DownloadManager-_download_piece_thread] Handshake failed with peer {peer_id} in {self.active_downloads[infohash]["torrent"].name}"
            )
            return None

    def _connect_peer(
        self,
        infohash: str,
        peer_info: dict[str, str, int],
    ):
        """Connects and handshakes a peer and returns a socket object.

        Args:
            infohash (str): The infohash of the torrent.
            peer_info (tuple): A tuple containing the peer's IP address and port.

        Returns:
            A socket object if the connection is successful, None otherwise.
        """
        ip = peer_info["ip"]
        port = peer_info["port"]

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

    def get_total_downloaded(self):
        """Returns the total downloaded size."""
        total_downloaded = 0
        with self.lock:
            for download_info in self.active_downloads.values():
                total_downloaded += download_info["downloaded_total"]
        return total_downloaded

    def get_total_downloaded_infohash(self, infohash: str):
        """Returns the total downloaded size for the supplied infohash.
        Args:
            infohash (str): The infohash of the torrent.
        Returns:
            The total downloaded size
        """
        with self.lock:
            return self.active_downloads[infohash]["downloaded_total"]

    def get_bytes_left(self, infohash: str):
        """Get the number of bytes left to download for a specific torrent.
        Args:
            infohash (str): The infohash of the torrent.
        Returns:
            The number of bytes left to download.
        """
        with self.lock:
            return (
                self.active_downloads[infohash]["torrent"].size
                - self.active_downloads[infohash]["downloaded_total"]
            )

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

    def send_info_to_ui(self):
        """Sends the information of the download process to UI"""
        pass
