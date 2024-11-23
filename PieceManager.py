import threading
import hashlib
import os
from torf import Torrent


class PieceManager:
    def __init__(self, torrent: Torrent, file_path: str):
        self.torrent = torrent
        self.piece_size = torrent.piece_size
        self.num_pieces = torrent.pieces
        self.hashes = torrent.hashes
        self.file_path = file_path
        self.piece_offsets = [i * self.piece_size for i in range(self.num_pieces)]
        self.bitfield = self.generate_bitfield()
        self.downloaded_pieces: dict[int, bytes] = {}
        self.remaining_pieces = self.num_pieces
        self.lock = threading.Lock()

    def add_downloaded_piece(self, piece_data: bytes, piece_idx: int):
        """Add the piece to the self.downloaded_pieces dictionary."""
        with self.lock:
            self.downloaded_pieces[piece_idx] = piece_data
            self.remaining_pieces -= 1
        self.update_bitfield(piece_idx)

    def verify_piece(self, piece_data, piece_idx):
        """Verifies the integrity of a downloaded piece."""
        calculated_hash = hashlib.sha1(piece_data).digest()
        with self.lock:
            expected_hash = self.hashes[piece_idx]
        return calculated_hash == expected_hash

    def generate_empty_bitfield(self):
        """Generates an empty bitfield."""
        return bytearray(self.num_pieces)

    def generate_bitfield(self):
        """Generates a bitfield by comparing file hashes with piece hashes."""
        bitfield = self.generate_empty_bitfield()

        try:
            with open(self.file_path, "rb") as file:
                for index, expected_hash in enumerate(self.hashes):
                    offset = self.piece_offsets[index]
                    # Read the piece based on remaining file size
                    remaining_size = min(
                        self.piece_size, os.path.getsize(self.file_path) - offset
                    )
                    piece = file.read(remaining_size)
                    if not piece:
                        break  # End of file

                    # Compute the hash of the current piece
                    piece_hash = hashlib.sha1(piece).digest()

                    # Compare the computed hash with the expected hash
                    if piece_hash == expected_hash:
                        bitfield[index] = 1
                    else:
                        pass

        except OSError as e:
            print(f"File system error: {e}")
        except Exception as e:
            print(f"[ERROR-PieceManager-generate_bitfield]: {e}")

        return bitfield

    def update_bitfield(self, piece_index):
        """Marks a piece as downloaded in the bitfield.
        Args:
            piece_index: The index of the downloaded piece.
        """
        with self.lock:
            self.bitfield[piece_index] = 1

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

    def get_piece_data(self, piece_idx):
        """
        Retrieves the specified piece from the file.

        Args:
            piece_idx (int): Index of the piece to retrieve.

        Returns:
            bytes: The piece data, or None if an error occurs.
        """

        try:
            with open(self.file_path, "rb") as f:
                # print("[INFO-PieceManager-get_piece_data]", self.file_path)
                offset = self.piece_offsets[piece_idx]

                # Seek to the correct offset and read data
                f.seek(offset)

                # Read the piece based on remaining file size
                remaining_size = min(
                    self.piece_size, os.path.getsize(self.file_path) - offset
                )
                # print(
                #     f"Reading piece {piece_idx} at offset {offset} with size {remaining_size}"
                # )

                piece_data = f.read(remaining_size)
                # print("read piece data", piece_data)

                return piece_data
        except FileNotFoundError:
            print(f"File not found: {self.file_path}")
            return None
        except Exception as e:
            print(f"Error reading piece: {e}")
            return None

    def get_all_piece_data(self):
        """Returns a dictionary of all downloaded pieces."""
        with self.lock:
            return self.downloaded_pieces
