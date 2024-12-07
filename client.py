from DownloadManager import DownloadManager
from UploadManager import UploadManager
from UserInterface import UserInterface
from TrackerCommunicator import TrackerCommunicator
import utils
import argparse
from threading import Thread


def main(host: str, port: int):
    # Initialize the tracker communicator
    trackerCommunicator = TrackerCommunicator(
        id,
        tracker_url,
        host,
        port,
    )

    # Initialize the upload manager
    uploadManager = UploadManager(id, host, port, torrent_dir, dest_dir)
    server_thread = Thread(target=uploadManager.run_server, daemon=True)
    server_thread.start()

    # Initialize the download manager
    downloadManager = DownloadManager(
        id, torrent_dir, dest_dir, uploadManager, trackerCommunicator
    )

    ui = UserInterface(
        host,
        port,
        torrent_dir,
        dest_dir,
        downloadManager,
        uploadManager,
        trackerCommunicator,
    )
    ui.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Client",
        description="BitTorrent client",
        epilog="!!!It requires the tracker running and listening!!!",
    )
    parser.add_argument("--tracker-url", type=str, required=False)
    parser.add_argument("--torrent_dir", type=str, required=False)
    parser.add_argument("--dest-dir", type=str, required=False)
    parser.add_argument("--port", type=int, required=False)
    args = parser.parse_args()

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
    if args.port:
        port = args.port

    main(host, port)
