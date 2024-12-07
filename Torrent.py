import bencodepy
import hashlib
import os
import pathlib
import math
import utils


class Torrent:
    def __init__(self):
        self.metainfo = {}

    @property
    def name(self):
        return self.metainfo["info"]["name"]

    @property
    def size(self):
        if "length" in self.metainfo["info"]:
            return self.metainfo["info"]["length"]
        else:
            return sum(f["length"] for f in self.metainfo["info"]["files"])

    @property
    def piece_size(self):
        return self.metainfo["info"]["piece length"]

    @property
    def pieces(self):
        size = self.size
        piece_size = self.piece_size
        return math.ceil(size / piece_size)

    @property
    def file_mode(self):
        if "length" in self.metainfo["info"]:
            return "singlefile"
        else:
            return "multifile"

    @property
    def infohash(self):
        info = bencodepy.encode(self.metainfo["info"])
        return hashlib.sha1(info).hexdigest()

    @property
    def files(self):
        if self.file_mode == "singlefile":
            path = pathlib.Path(self.metainfo["info"]["name"])
            files = ((path, self.size),)
        else:
            base_path = self.metainfo["info"]["name"]
            files = tuple(
                (pathlib.Path(base_path) / "/".join(f["path"]), f["length"])
                for f in self.metainfo["info"]["files"]
            )
        return files

    @property
    def filetree(self):
        if self.file_mode == "singlefile":
            path = pathlib.Path(self.metainfo["info"]["name"])
            return {str(path): self.size}
        else:
            base_path = self.metainfo["info"]["name"]
            file_tree = {}

            for f in self.metainfo["info"]["files"]:
                path = pathlib.Path(base_path) / "/".join(f["path"])
                parts = list(path.parts)
                current_level = file_tree

                for part in parts[:-1]:
                    current_level = current_level.setdefault(part, {})
                current_level[parts[-1]] = f["length"]

            return file_tree

    @property
    def hashes(self):
        pieces = self.metainfo["info"]["pieces"]
        return tuple(pieces[i : i + 20] for i in range(0, len(pieces), 20))

    @classmethod
    def read(cls, path):
        try:
            with open(path, "rb") as f:
                data = f.read()
                decoded = bencodepy.decode(data)
                if b"info" in decoded and b"pieces" in decoded[b"info"]:
                    pieces = decoded[b"info"][b"pieces"]
                    metainfo = utils.decode_dict(decoded)
                    metainfo["info"]["pieces"] = pieces
                else:
                    metainfo = utils.decode_dict(decoded)
                    print(metainfo)
                torrent = cls()
                torrent.metainfo = metainfo
                return torrent
        except OSError as e:
            print(f"Error reading file: {e}")
            return None

    @classmethod
    def generate_torrent(
        cls, path: str, torrent_dir: str, piece_size: int = 512 * 1024
    ):
        """Generates a torrent file from a given file or folder, and saves it to the specified directory."""

        print("generating torrent file for path: ", path)
        metainfo = dict()

        base_path = pathlib.Path(path).resolve()
        torrent_dir_path = pathlib.Path(torrent_dir).resolve()
        torrent_dir_path.mkdir(parents=True, exist_ok=True)

        if base_path.is_file():
            # Singlefile
            files = [{"path": [base_path.name], "length": base_path.stat().st_size}]
            torrent_type = "singlefile"
            total_size = base_path.stat().st_size
        elif base_path.is_dir():
            # Multifile
            files = []
            total_size = 0
            for root, dirs, filenames in os.walk(base_path):
                for filename in filenames:
                    file_path = pathlib.Path(root) / filename
                    relative_path = file_path.relative_to(base_path)
                    file_length = file_path.stat().st_size
                    files.append({"path": relative_path.parts, "length": file_length})
                    total_size += file_length
            torrent_type = "multifile"
            files.sort(key=lambda x: x["path"])  # consistent between OSes
        else:
            raise ValueError(f"Invalid file path: {base_path}")

        info = dict(
            [
                (b"name", base_path.name.encode()),
                (b"piece length", piece_size),
                (b"pieces", b""),
            ]
        )

        if torrent_type == "singlefile":
            info[b"length"] = total_size
        else:
            info[b"files"] = files

        piece_hashes = []
        if torrent_type == "singlefile":
            # Singlefile
            with open(base_path, "rb") as f:
                piece = f.read(piece_size)
                while piece:
                    piece_hashes.append(hashlib.sha1(piece).digest())
                    piece = f.read(piece_size)
        elif torrent_type == "multifile":
            # Multifile
            data = b""
            for file in files:
                file_path = pathlib.Path(*file["path"])
                full_file_path = base_path / file_path
                with open(full_file_path, "rb") as f:
                    data += f.read()
            for i in range(0, len(data), piece_size):
                piece = data[i : i + piece_size]
                piece_hashes.append(hashlib.sha1(piece).digest())

        info[b"pieces"] = b"".join(piece_hashes)

        metainfo[b"info"] = info
        metainfo[b"created by"] = b"Duc An"

        torrent_data = bencodepy.encode(metainfo)

        torrent_filename = f"{base_path.stem}.torrent"
        torrent_file_path = torrent_dir_path / torrent_filename
        with open(torrent_file_path, "wb") as f:
            f.write(torrent_data)
        print("Torrent file created:", torrent_file_path)

        return torrent_file_path
