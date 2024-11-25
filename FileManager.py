import os
from torf import Torrent


class FileManager:
    def __init__(self, torrent_dir: str, destination_dir: str):
        self.torrent_dir = torrent_dir
        self.destination_dir = destination_dir

    def write_single_file(self, destination_file_path, data):
        with open(destination_file_path, "wb") as f:
            for _, piece_data in sorted(data.items()):
                f.write(piece_data)

    def write_multi_file(self, dest_dir, data, file_infos):
        offset = 0
        concat_data = b""
        for _, piece_data in sorted(data.items()):
            concat_data += piece_data
        for file_info in file_infos:
            size = file_info.size
            write_path = dest_dir + str(file_info.parent) + "/" + str(file_info.name)
            with open(write_path, "wb") as f:
                data = concat_data[offset : offset + size]
                print(
                    f"writing to {write_path} with size {size} and length {len(data)}"
                )
                f.write(data)
            offset += size

    def check_local_torrent(self, infohash: str):
        files = self.list_torrents()
        for file in files:
            if Torrent.read(self.torrent_dir + file).infohash == infohash:
                return True
        return False

    def get_torrent_file_path(self, infohash: str):
        files = self.list_torrents()
        for file in files:
            if Torrent.read(self.torrent_dir + file).infohash == infohash:
                # print("[INFO-FileManager-get_file_path]", self.torrent_dir + file)
                return self.torrent_dir + file

    def get_original_file_path(self, infohash: str):
        files = self.list_torrents()
        for file in files:
            if Torrent.read(self.torrent_dir + file).infohash == infohash:
                return self.destination_dir + Torrent.read(self.torrent_dir + file).name

    def list_torrents(self):
        files = [f for f in os.listdir(self.torrent_dir) if f.endswith(".torrent")]
        return files

    def create_file_tree(self, torrent: Torrent):
        self._process_file_tree(torrent.filetree, self.destination_dir)

    def _process_file_tree(self, tree, base_path):
        for item, value in tree.items():
            if isinstance(value, dict):  # Directory
                dir_path = os.path.join(base_path, item)
                self._create_directory(dir_path)
                self._process_file_tree(value, dir_path)
            else:  # File
                file_path = os.path.join(base_path, item)
                self._create_file(file_path)

    def _create_directory(self, path):
        try:
            os.makedirs(path)
        except FileExistsError:
            pass

    def _create_file(self, path):
        with open(path, "w"):
            pass
