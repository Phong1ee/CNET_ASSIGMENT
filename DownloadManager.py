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
        self.dest_dir = dest_dir
        self.fileManager = fileManager
        self.id = id

        self.active_downloads: dict[
            str, dict
        ] = {}  # A dictionary to store active downloads
        self.lock = threading.Lock()

    def new_download(self, torrent: Torrent, peer_list: list):
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
        download_info = self.active_downloads[infohash]
        peer_list = download_info["peer_list"]

        # Initialize the piece manager
        pieceManager = PieceManager(download_info["torrent"], self.dest_dir)

        # Initialize piece index queue
        piece_index_queue: queue.Queue[int] = queue.Queue()
        for piece_idx in range(download_info["torrent"].pieces):
            piece_index_queue.put(piece_idx)

        # Assign pieces to peers
        # print("[INFO-DownloadManager-_download] Assigning pieces to peers")
        peer_idx = 0
        threads = []
        while not piece_index_queue.empty():
            piece_idx = piece_index_queue.get()
            # print("Queue empty:", piece_index_queue.empty())

            # Connect to a peer
            socket = self._connect_peer(infohash, peer_list[peer_idx])
            if socket is not None:
                peer_id = peer_list[peer_idx]["peer_id"]
                download_info["num_connected_peers"] += 1
                thread = Thread(
                    target=self._download_piece_thread,
                    args=(pieceManager, piece_idx, infohash, socket, peer_id),
                )
                threads.append(thread)

            else:  # Put the index back to the queue
                # print(
                #     "[INFO-DownloadManager-_download] Peer connection failed, putting piece back to queue"
                # )
                piece_index_queue.put(piece_idx)

            peer_idx = (peer_idx + 1) % len(download_info["peer_list"])

        # Start all threads
        for thread in threads:
            thread.start()
        # print("[INFO-DownloadManager-_download] All threads started")

        # Wait for all threads to finish
        for thread in threads:
            thread.join()
        # print("[INFO-DownloadManager-_download] Download complete")
        piece_data: dict[int, bytes] = pieceManager.get_all_piece_data()

        # Create file tree
        self.fileManager.create_file_tree(download_info["torrent"], "./download_test/")
        # print(
        #     "[INFO-DownloadManager-_download] File tree created at", "./download_test/"
        # )

        # Write the downloaded data to the destination file
        if download_info["torrent"].mode == "singlefile":
            dest_path = f"./download_test/{download_info['torrent'].name}"
            # print(
            #     "[INFO-DownloadManager-_download] Writing single file to destination path:",
            #     dest_path,
            # )
            self.fileManager.write_single_file(
                dest_path,
                piece_data,
            )
        else:
            # print(
            #     "[INFO-DownloadManager-_download] Writing multi file to destination path",
            # )
            self.fileManager.write_multi_file(
                "./download_test/", piece_data, download_info["torrent"].files
            )
        # print("[INFO-DownloadManager-_download] File written successfully")
        # remove from active downloads
        with self.lock:
            del self.active_downloads[infohash]
            # print("[INFO-DownloadManager-_download] Removed from active downloads")

    def _download_piece_thread(
        self,
        pieceManager: PieceManager,
        piece_index: int,
        infohash: str,
        socket: socket.socket,
        peer_id: str,
    ):
        peerCommunicator = PeerCommunicator(socket)

        peerCommunicator.send_handshake(self.id, infohash)
        handshake = peerCommunicator.receive_handshake()
        valid = peerCommunicator.validate_handshake(
            handshake,
            infohash,
            peer_id,
        )

        if valid:
            peerCommunicator.receive_unchoke()
            peerCommunicator.send_interested()
            bitfield = peerCommunicator.receive_bitfield()

            if bitfield[piece_index] == 1:
                peerCommunicator.send_request(piece_index)
                received_idx, piece_data = peerCommunicator.receive_piece()
                if received_idx != piece_index:
                    # print(
                    #     f"[ERROR-DownloadManager-_download_piece_thread] Received piece {received_idx} does not match requested piece {piece_index}"
                    # )
                    return
                if pieceManager.verify_piece(piece_data, piece_index):
                    pieceManager.add_downloaded_piece(piece_data, piece_index)
                    with self.lock:
                        self.active_downloads[infohash]["downloaded_total"] += len(
                            piece_data
                        )
                        self.active_downloads[infohash]["num_connected_peers"] -= 1
                    # print(
                    #     f"[INFO-DownloadManager-_download_piece_thread] Piece {piece_index} downloaded successfully"
                    # )
                    return

                else:
                    # print(
                    #     f"[ERROR-DownloadManager-_download_piece_thread] Piece {piece_index} hash verification failed"
                    # )
                    return
            else:
                # print(
                #     f"[INFO-DownloadManager-_download_piece_thread] Peer {peer_id} does not have piece {piece_index}"
                # )
                return
        else:
            # print(
            #     f"[ERROR-DownloadManager-_download_piece_thread] Handshake failed with peer {peer_id}"
            # )
            return

    def _connect_peer(
        self,
        infohash: str,
        peer_info: dict,
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

    def get_downloaded(self):
        """Returns the total downloaded data."""
        downloaded = []
        with self.lock:
            for download_info in self.active_downloads.values():
                downloaded.append(download_info["downloaded_total"])
        return downloaded

    def get_total(self):
        """Returns the total file size."""
        total = []
        with self.lock:
            for download_info in self.active_downloads.values():
                total.append(download_info["torrent"].size)
        return total

    def get_num_peers(self):
        """Returns the number of peers."""
        num_peers = []
        with self.lock:
            for download_info in self.active_downloads.values():
                num_peers.append(len(download_info["peer_list"]))
        return num_peers

    def get_num_connected_peers(self):
        """Returns the number of connected peers."""
        num_connected_peers = []
        with self.lock:
            for download_info in self.active_downloads.values():
                num_connected_peers.append(download_info["num_connected_peers"])
        return num_connected_peers

    def get_num_downloading(self):
        """Returns the number of downloading files."""
        return len(self.active_downloads)

    def get_file_names(self):
        file_names = []
        with self.lock:
            for download_info in self.active_downloads.values():
                file_names.append(download_info["torrent"].name)
        return file_names
