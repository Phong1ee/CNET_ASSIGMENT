import bencodepy
import math
import hashlib
import pathlib
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
