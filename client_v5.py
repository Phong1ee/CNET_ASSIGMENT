from DownloadManager import DownloadManager
from UploadManager import UploadManager
from FileManager import FileManager
from UserInterface import UserInterface
from TrackerCommunicator import TrackerCommunicator
import utils
import argparse


def main(host: str, port: int):
    # Initialize the file manager
    fileManager = FileManager(torrent_dir, dest_dir)

    # Initialize the download manager
    downloadManager = DownloadManager(id, dest_dir, fileManager)

    # Initialize the upload manager
    uploadManager = UploadManager(id, host, port, torrent_dir, fileManager)

    # Initialize the tracker communicator
    trackerCommunicator = TrackerCommunicator(
        id,
        tracker_url,
        downloadManager,
        uploadManager,
        host,
        port,
    )

    ui = UserInterface(
        torrent_dir,
        dest_dir,
        downloadManager,
        uploadManager,
        trackerCommunicator,
        fileManager,
    )
    ui.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Client",
        description="Connect to tracker",
        epilog="!!!It requires the tracker running and listening!!!",
    )
    parser.add_argument("--tracker-url", type=str, required=False)
    parser.add_argument("--torrent_dir", type=str, required=False)
    parser.add_argument("--dest-dir", type=str, required=False)
    args = parser.parse_args()

    tracker_url = "http://192.168.1.106"

    id = utils.get_id()
    host = utils.get_ip()
    port = 6881
    torrent_dir = "./torrents/"
    dest_dir = "./download_path/"

    if args.tracker_url:
        tracker_url = args.tracker_url
    if args.dest_dir:
        dest_dir = args.dir
    if args.torrent_dir:
        dest_dir = args.torrent_dir

    main(host, port)
