import hashlib
import os
from torf import Torrent


class PieceManager:
    def __init__(self, torrent: Torrent, file_path: str):
        self.torrent = torrent
        self.piece_size = torrent.piece_size
        self.num_pieces = torrent.pieces
        self.hashes = torrent.hashes
        self.bitfield = self.generate_empty_bitfield()
        self.piece_offsets = [i * self.piece_size for i in range(self.num_pieces)]
        self.file_path = file_path

    def save_piece(self, piece_data: bytes, piece_index: int):
        """Saves a downloaded piece to the file system."""
        with open(self.file_path, "r+b") as file:
            file.seek(self.piece_offsets[piece_index])
            file.write(piece_data)

    def verify_piece(self, piece_data, piece_hash):
        """Verifies the integrity of a downloaded piece."""
        calculated_hash = hashlib.sha1(piece_data).digest()
        return calculated_hash == piece_hash

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
        self.bitfield[piece_index] = 1

    def get_num_remaining_pieces(self):
        """Returns the number of remaining pieces to download."""
        return self.num_pieces - sum(self.bitfield)

    def get_not_downloaded_pieces(self):
        """Returns a list of indices of not downloaded pieces."""
        return [i for i, bit in enumerate(self.bitfield) if bit == 0]

    def get_downloaded_pieces(self):
        """Returns a list of indices of downloaded pieces."""
        return [i for i, bit in enumerate(self.bitfield) if bit == 1]

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
                f.seek(piece_idx * self.piece_size)
                piece_data = f.read(self.piece_size)
                return piece_data
        except FileNotFoundError:
            print(f"File not found: {self.file_path}")
            return None
        except Exception as e:
            print(f"Error reading piece: {e}")
            return None
