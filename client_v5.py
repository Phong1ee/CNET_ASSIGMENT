from DownloadManager import DownloadManager
from UploadManager import UploadManager
from FileManager import FileManager
from UserInterface import UserInterface
from TrackerCommunicator import TrackerCommunicator
import utils
import argparse

if __name__ == "__name__":
    parser = argparse.ArgumentParser(
        prog="Client",
        description="Connect to tracker",
        epilog="!!!It requires the tracker running and listening!!!",
    )
    parser.add_argument("--tracker-url", type=str, required=False)
    parser.add_argument("--target-path", type=str, required=False)
    parser.add_argument("--dest-path", type=str, required=False)
    args = parser.parse_args()

    tracker_url = "http://192.168.1.106"

    id = utils.get_id()
    host = utils.get_ip()
    port = 6881
    target_path = "./torrents"
    dest_path = "./download_path"

    if args.tracker_url:
        tracker_url = args.tracker_url
    if args.dest_path:
        dest_path = args.dest_path
    if args.target_path:
        dest_path = args.target_path

    # Initialize the file manager
    fileManager = FileManager(target_path, dest_path)

    # Initialize the download manager
    downloadManager = DownloadManager(id, dest_path, fileManager)

    # Initialize the upload manager
    uploadManager = UploadManager(target_path, fileManager)

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
        dest_path, downloadManager, uploadManager, trackerCommunicate, fileManager
    )
    ui.run()
