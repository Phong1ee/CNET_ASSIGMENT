import threading
import hashlib
from Torrent import Torrent


class PieceManager:
    def __init__(self, torrent: Torrent, file_path: str):
        self.torrent = torrent
        self.piece_size = torrent.piece_size
        self.num_pieces = torrent.pieces
        self.hashes = torrent.hashes
        self.file_path = file_path
        self.piece_offsets = [i * self.piece_size for i in range(self.num_pieces)]
        self.bitfield: bytearray = bytearray(self.num_pieces)
        self.downloaded_pieces: dict[int, bytes] = {}
        self.remaining_pieces = self.num_pieces
        self.lock = threading.Lock()

    def generate_bitfield(self):
        bitfield = bytearray(self.num_pieces)
        data = self._concat_data()
        current_offset = 0
        try:
            for index, expected_hash in enumerate(self.hashes):
                offset = self.piece_offsets[index]
                remaining_size = min(self.piece_size, self.torrent.size - offset)
                piece = data[current_offset : current_offset + remaining_size]
                piece_hash = hashlib.sha1(piece).digest()

                if piece_hash == expected_hash:
                    bitfield[index] = 1
                else:
                    pass

                current_offset += remaining_size

        except OSError as e:
            print(f"[ERROR-PieceManager-generate_bitfield]: OSError {e}")
        except Exception as e:
            print(f"[ERROR-PieceManager-generate_bitfield]: {e}")

        return bitfield

    def update_bitfield(self, piece_index):
        with self.lock:
            self.bitfield[piece_index] = 1

    def _concat_data(self):
        data = b""
        for file_info in self.torrent.files:
            file_path = self.file_path + "/" + str(file_info[0])

            with open(file_path, "rb") as f:
                data += f.read()
        return data

    def get_piece_data(self, piece_idx):
        data = self._concat_data()
        offset = self.piece_offsets[piece_idx]
        remaining_size = min(self.piece_size, self.torrent.size - offset)
        piece_data = data[offset : offset + remaining_size]
        return piece_data

    def get_all_piece_data(self):
        with self.lock:
            return self.downloaded_pieces

    def verify_piece(self, piece_data, piece_idx):
        calculated_hash = hashlib.sha1(piece_data).digest()
        # print(f"Calculated hash: {calculated_hash}")
        # print(f"Expected hash: {self.hashes[piece_idx]}")
        with self.lock:
            expected_hash = self.hashes[piece_idx]
        return calculated_hash == expected_hash

    def verify_all_pieces(self):
        for piece_idx, piece_data in self.downloaded_pieces.items():
            if not self.verify_piece(piece_data, piece_idx):
                return False
        return True

    def add_downloaded_piece(self, piece_data: bytes, piece_idx: int):
        with self.lock:
            self.downloaded_pieces[piece_idx] = piece_data
            self.remaining_pieces -= 1
        self.update_bitfield(piece_idx)

    def get_num_remaining_pieces(self):
        """Returns the number of remaining pieces to download."""
        with self.lock:
            return self.remaining_pieces

    def get_not_downloaded_indexes(self):
        """Returns a list of indices of not downloaded pieces."""
        with self.lock:
            not_downloaded = [i for i, bit in enumerate(self.bitfield) if bit == 0]
        return not_downloaded

    def get_downloaded_indexes(self):
        """Returns a list of indices of downloaded pieces."""
        with self.lock:
            downloaded = [i for i, bit in enumerate(self.bitfield) if bit == 1]
        return downloaded
