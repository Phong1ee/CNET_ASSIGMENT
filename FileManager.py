import os

from Torrent import Torrent


class FileManager:
    @classmethod
    def write_file(cls, destination, data, file_infos=None):
        if file_infos is None:  # Single file mode
            with open(destination, "wb") as f:
                for _, piece_data in sorted(data.items()):
                    f.write(piece_data)
        else:  # Multi-file mode
            offset = 0
            concat_data = b"".join(piece_data for _, piece_data in sorted(data.items()))
            for file_info in file_infos:
                size = file_info[1]
                write_path = os.path.join(destination, str(file_info[0]))
                os.makedirs(
                    os.path.dirname(write_path), exist_ok=True
                )  # Ensure directories exist
                with open(write_path, "wb") as f:
                    file_data = concat_data[offset : offset + size]
                    f.write(file_data)
                offset += size

    @classmethod
    def list_torrents(cls, torrent_dir):
        files = [f for f in os.listdir(torrent_dir) if f.endswith(".torrent")]
        return files

    @classmethod
    def check_local_torrent(cls, infohash: str, torrent_dir: str):
        files = cls.list_torrents(torrent_dir)
        for file in files:
            if Torrent.read(torrent_dir + file).infohash == infohash:
                return True
        return False

    @classmethod
    def get_torrent_file_path(cls, infohash: str, torrent_dir: str):
        files = cls.list_torrents(torrent_dir)
        for file in files:
            if Torrent.read(torrent_dir + file).infohash == infohash:
                return torrent_dir + file

    @classmethod
    def get_original_file_path(cls, infohash: str, original_dir: str, torrent_dir: str):
        files = cls.list_torrents(torrent_dir)
        for file in files:
            if Torrent.read(torrent_dir + file).infohash == infohash:
                return original_dir + Torrent.read(torrent_dir + file).name

    @classmethod
    def create_file_tree(cls, torrent: Torrent, dest_path):
        cls._process_file_tree(torrent.filetree, dest_path)

    @staticmethod
    def _process_file_tree(tree, base_path):
        for item, value in tree.items():
            if isinstance(value, dict):  # Directory
                dir_path = os.path.join(base_path, item)
                FileManager._create_directory(dir_path)
                FileManager._process_file_tree(value, dir_path)
            else:  # File
                file_path = os.path.join(base_path, item)
                FileManager._create_file(file_path)

    @staticmethod
    def _create_directory(path):
        try:
            os.makedirs(path)
        except FileExistsError:
            pass

    @staticmethod
    def _create_file(path):
        with open(path, "w"):
            pass
