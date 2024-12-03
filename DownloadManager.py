import queue
import socket
import threading
from threading import Thread

from Torrent import Torrent
from FileManager import FileManager
from PieceManager import PieceManager
from PeerCommunicator import PeerCommunicator


class DownloadManager:
    def __init__(
        self,
        id: str,
        torrent_dir: str,
        dest_dir: str,
    ):
        self.torrent_dir = torrent_dir
        self.dest_dir = dest_dir
        self.id = id
        self.MAXIMUM_CONNECT_RETRY = 5
        self.MAXIMUM_DOWNLOAD_RETRY = 3
        self.BATCH_SIZE = 10

        self.active_downloads: dict[str, dict] = (
            {}
        )  # A dictionary to store active downloads
        self.lock = threading.Lock()

    def new_download(self, torrent: Torrent, peer_list: list):
        with self.lock:
            infohash = torrent.infohash
            self.active_downloads[infohash] = {
                "peer_list": peer_list,
                "torrent": torrent,
                "download_thread": Thread(target=self._download, args=(infohash,)),
                "downloaded_data": [],
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

        # Connect to peers
        connected_peers = []
        peer_to_connect = peer_list.copy()

        for _ in range(self.MAXIMUM_CONNECT_RETRY):
            for peer in peer_to_connect[:]:
                socket = self._connect_peer(infohash, peer)
                if socket:
                    connected_peers.append({"socket": socket, "peer": peer})
                    peer_to_connect.remove(peer)

            if len(connected_peers) >= len(peer_list):
                break

        print(
            f"Connected to {len(connected_peers)} out of {len(peer_list)} peers for {download_info['torrent'].name}"
        )
        print("Connected peers: ", connected_peers)

        # Retrieve bitfields from connected peers
        bitfields: dict[str, bytearray] = {}
        for peer in connected_peers:
            Thread(
                target=self._retrieve_bitfield,
                args=(peer["peer"]["peer_id"], peer["socket"], bitfields),
            ).start()

        # Wait for all bitfields to be retrieved
        while len(bitfields) < len(connected_peers):
            pass

        print("All bitfields retrieved.")

        # Initialize the failed pieces queue
        failed_pieces: queue.Queue = queue.Queue()

        # Download and retry loop
        for retry_attempt in range(self.MAXIMUM_DOWNLOAD_RETRY + 1):
            print(f"Download attempt {retry_attempt + 1}")

            if retry_attempt == 0:
                pieces_to_download = self._get_rarest_pieces(bitfields)
            else:
                if failed_pieces.empty():
                    print("No failed pieces to retry.")
                    break
                pieces_to_download = list(failed_pieces.queue)
                failed_pieces.queue.clear()

            print(f"Pieces to download: {pieces_to_download}")

            # Assign pieces to peers in a Round-Robin manner
            assigned_dict: dict[str, list] = {
                peer["peer"]["peer_id"]: [] for peer in connected_peers
            }
            for i, piece_idx in enumerate(pieces_to_download):
                peer = connected_peers[i % len(connected_peers)]
                peer_id = peer["peer"]["peer_id"]

                if bitfields[peer_id][piece_idx] == 1:
                    assigned_dict[peer_id].append(piece_idx)

            print(f"Assigned pieces: {assigned_dict}")

            # Start download threads
            threads = []
            for peer in connected_peers:
                peer_id = peer["peer"]["peer_id"]
                assigned_pieces = assigned_dict[peer_id]

                if assigned_pieces:
                    thread = Thread(
                        target=self._download_piece_thread,
                        args=(
                            pieceManager,
                            assigned_pieces,
                            infohash,
                            peer["socket"],
                            failed_pieces,
                            self.MAXIMUM_DOWNLOAD_RETRY,
                        ),
                    )
                    threads.append(thread)
                    thread.start()

            # Wait for all threads to finish
            for thread in threads:
                thread.join()

        if not failed_pieces.empty():
            print(
                f"Failed to download some pieces after {self.MAXIMUM_DOWNLOAD_RETRY} retries."
            )
            return

        print(f"Download finished for {download_info['torrent'].name}")

        # Verify the downloaded data
        success = pieceManager.verify_all_pieces()
        if not success:
            print(
                f"Downloaded data verification failed for {download_info['torrent'].name}"
            )
            return
        print(
            f"Downloaded data verification passed for {download_info['torrent'].name}"
        )

        # Finalize download
        piece_data = pieceManager.get_all_piece_data()
        FileManager.create_file_tree(download_info["torrent"], "./download_test/")
        FileManager.write_file(
            "./download_test/", piece_data, download_info["torrent"].files
        )

        with self.lock:
            del self.active_downloads[infohash]
        print(f"Write file completed for {download_info['torrent'].name}")

    def _download_piece_thread(
        self,
        pieceManager: PieceManager,
        assigned_pieces: list,
        infohash: str,
        socket: socket.socket,
        failed_pieces: queue.Queue,
        MAXIMUM_RETRY: int,
    ):
        peerCommunicator = PeerCommunicator(socket)
        for piece_index in assigned_pieces:
            # print("Attemping to download piece ", piece_index)
            for attempt in range(MAXIMUM_RETRY):
                try:
                    peerCommunicator.send_request(piece_index)
                    # print("DownloadManager: sent request for piece ", piece_index)
                    received_idx, piece_data = peerCommunicator.receive_piece()
                    # print("DownloadManager: received piece ", received_idx)

                    if received_idx != piece_index:
                        raise Exception(
                            f"Received idx {received_idx} not match requested idx {piece_index}"
                        )

                    if pieceManager.verify_piece(piece_data, piece_index):
                        pieceManager.add_downloaded_piece(piece_data, piece_index)
                        with self.lock:
                            self.active_downloads[infohash]["downloaded_total"] += len(
                                piece_data
                            )
                        break

                    else:
                        raise Exception("Piece verification failed")
                except Exception as e:
                    print(
                        f"[ERROR] Download failed for piece {piece_index}, attempt {attempt + 1}/{MAXIMUM_RETRY}: {e}"
                    )

                    if attempt + 1 == MAXIMUM_RETRY:
                        failed_pieces.put(piece_index)
                    else:
                        continue
        peerCommunicator.send_choke()
        socket.close()

    def _retrieve_bitfield(
        self,
        peer_id: str,
        socket: socket.socket,
        bitfields: dict,
    ):
        peerCommunicator = PeerCommunicator(socket)
        peerCommunicator.receive_unchoke()
        # print("received unchoke from peer ", peer_id)
        peerCommunicator.send_interested()
        # print("sent interested to peer ", peer_id)
        bitfield = peerCommunicator.receive_bitfield()
        # print("received bitfield from peer ", peer_id)
        with self.lock:
            bitfields[peer_id] = bitfield

    def _connect_peer(
        self,
        infohash: str,
        peer_info: dict,
    ):
        ip = peer_info["ip"]
        port = peer_info["port"]

        try:
            # Connect to the peer
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            buffer_size = 1024 * 1024
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, buffer_size)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, buffer_size)
            s.connect((ip, port))

            # Handshake with the peer
            peer_communicator = PeerCommunicator(s)
            peer_communicator.send_handshake(self.id, infohash)
            # print(f"Sent handshake to {ip}:{port}")
            handshake = peer_communicator.receive_handshake()
            # print(f"Received handshake from {ip}:{port}")
            infohash = handshake[28:48].hex()
            peer_id = handshake[48:].decode("utf-8")

            valid = peer_communicator.validate_handshake(handshake, infohash, peer_id)
            if not valid:
                raise Exception("Handshake failed")

            # Successfully connected to the peer
            with self.lock:
                self.active_downloads[infohash]["num_connected_peers"] += 1
            return s
        except Exception as e:
            print(e)
            return None

    def _get_rarest_pieces(self, bitfields):
        """Returns a list of pieces ordered by rarity."""
        piece_count = {}

        for bitfield in bitfields.values():
            for idx, bit in enumerate(bitfield):
                if bit == 1:
                    piece_count[idx] = piece_count.get(idx, 0) + 1

        # Sort pieces by rarity (ascending)
        return [
            piece for piece, _ in sorted(piece_count.items(), key=lambda item: item[1])
        ]

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
