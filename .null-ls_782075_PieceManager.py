import hashlib


class PieceManager:
    def __init__(self, torrent_info):
        self.num_pieces = torrent_info._pieces
        self.piece_length = torrent_info.piece_length
        self.bitfield = [0] * self.num_pieces  # Initialize bitfield to all zeros

    def save_piece(self, piece_data: bytes, piece_index: int, file_path: str):
        """Saves a downloaded piece to the file system.

        Args:
            piece_data (str): The downloaded piece data.
            piece_index (int): The index of the downloaded piece.
            file_path (str): The path to the downloaded file
        """
        with open(file_path, "r+b") as file:
            file.seek(piece_index * self.piece_length)
            file.write(piece_data)

    def verify_piece(self, piece_data, piece_hash):
        """Verifies the integrity of a downloaded piece.

        Args:
            piece_data: The downloaded piece data.
            piece_hash: The expected hash of the piece.

        Returns:
            True if the piece is valid, False otherwise.
        """
        calculated_hash = hashlib.sha1(piece_data).digest()
        return calculated_hash == piece_hash

    def generate_empty_bitfield(self):
        """Generates an empty bitfield.
        Return:
            A bytearray representing an empty bitfield of length self.num_pieces.
        """
        return bytearray(self.num_pieces)

    def generate_bitfield(self, file_path, piece_hashes):
        """
        Generates a bitfield by comparing file hashes with piece hashes.

        Args:
            file_path: The path to the file.
            piece_hashes: A list of piece hashes.

        Returns:
            A bytearray representing the downloaded pieces.
        """
        # Generate an empty bitfield
        bitfield = self.generate_empty_bitfield()

        # Calculate the size of each piece
        piece_size = self.piece_length

        try:
            with open(file_path, "rb") as file:
                for index, expected_hash in enumerate(piece_hashes):
                    # Read the next piece from the file
                    piece = file.read(piece_size)
                    if not piece:
                        break  # End of file

                    # Compute the hash of the current piece
                    piece_hash = hashlib.sha1(piece).digest()

                    # Compare the computed hash with the expected hash
                    if piece_hash == expected_hash:
                        bitfield[index] = 1
                    else:
                        pass

        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except Exception as e:
            print(f"[ERROR-PieceManager-generate_bitfield]: {e}")

        return bitfield

    def update_bitfield(self, piece_index, bitfield):
        """Marks a piece as downloaded in the bitfield.
        Args:
            piece_index: The index of the downloaded piece.
            bitfield: The current bitfield.
        """
        bitfield[piece_index] = 1
        return bitfield

    def remaining_pieces(self):
        """Returns the number of remaining pieces to download."""
        return self.num_pieces - sum(self.bitfield)

    def not_downloaded_pieces(self):
        """Returns a list of indices of not downloaded pieces."""
        return [i for i, bit in enumerate(self.bitfield) if bit == 0]

    def downloaded_pieces(self):
        """Returns a list of indices of downloaded pieces."""
        return [i for i, bit in enumerate(self.bitfield) if bit == 1]
