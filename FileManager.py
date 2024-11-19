class FileManager:
    def __init__(self, torrent_info, destination_path):
        self.torrent_info = torrent_info
        self.destination_path = destination_path
        self.file_tree = self.build_file_tree(torrent_info)

    def build_file_tree(self, torrent_info):
        """Builds a file tree based on the torrent information.

        Args:
            torrent_info: The torrent information object.

        Returns:
            A nested dictionary representing the file tree.
        """
        # ... (Implement logic to construct the file tree)

    def write_piece_to_file(self, piece_index, piece_data):
        """Writes a piece of data to the appropriate file.

        Args:
            piece_index: The index of the piece.
            piece_data: The piece data.
        """
        # ... (Implement logic to determine the file and offset, write the data)

    def verify_file_integrity(self, file_path, piece_hashes):
        """Verifies the integrity of a file.

        Args:
            file_path: The path to the file.
            piece_hashes: A list of piece hashes.

        Returns:
            True if the file is valid, False otherwise.
        """
        # ... (Implement logic to read the file in chunks, calculate hashes, and compare)

    def delete_incomplete_files(self):
        """Deletes any incomplete files in the destination directory."""
        # ... (Implement logic to identify and delete incomplete files)

    def resume_download(self):
        """Resumes a previously interrupted download.

        This involves checking the existing files, calculating the missing pieces, and updating the bitfield.
        """
        # ... (Implement logic to check file integrity, update bitfield, and resume download)