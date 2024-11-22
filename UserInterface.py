import os
from time import sleep

from torf import Torrent

from DownloadManager import DownloadManager
from FileManager import FileManager
from TrackerCommunicator import TrackerCommunicator
from UploadManager import UploadManager


class UserInterface:
    def __init__(
        self,
        torrent_dir: str,
        dest_dir: str,
        downloadManager: DownloadManager,
        uploadManager: UploadManager,
        trackerCommunicator: TrackerCommunicator,
        fileManager: FileManager,
    ):
        """Initialize a UserInterface object

        Args:
            torrent_dir (str): Path to the folder storing the torrents
            dest_dir (str): Path to desired download folder
            downloadManager (DownloadManager.DownloadManager): DownloadManager object
            uploadManager (UploadManager.UploadManager): UploadManager object
            trackerCommunicator (TrackerCommunicator.TrackerCommunicator): TrackerCommunicator object
            fileManager (FileManager.FileManager): FileManager object
        """
        self.torrent_dir = torrent_dir
        self.dest_dir = dest_dir
        self.downloadManager = downloadManager
        self.uploadManager = uploadManager
        self.trackerCommunicator = trackerCommunicator
        self.fileManager = fileManager

    def run(self):
        while True:
            self.clear()
            option = self.menu()

            match option:
                case "1":
                    self.clear()
                    self.new_download()
                case "2":
                    self.clear()
                    self.new_upload()
                case "3":
                    self.clear()
                    self.show_downloading()
                case "4":
                    self.clear()
                    self.show_uploading()
                case "5":
                    self.exit()
                case _:
                    print("Invalid option, only input 1->5")
                    sleep(1)

    def menu(self):
        print("Welcome to our Simple BitTorrent client!")
        print("--------------------------------------------")
        print("You are Online!, other peers may connect to you")
        print("[1] Download a Torrent")
        print("[2] Upload a Torrent")
        print("[3] View downloading files")
        print("[4] View uploading files")
        print("[5] Exit")
        print("--------------------------------------------")
        option = input("Choose an option: ")

        return option

    def new_download(self):
        # Input the .torrent file
        torrent = self._input_torrent()
        if torrent is None:
            return 1

        # Display the file information
        print("--------------------------------------------")
        print("Torrent file information:")
        print(f"Name: {torrent.name}")
        print(f"Size: {torrent.size} bytes")
        print(f"Piece size: {torrent.piece_size} bytes")
        print(f"Number of files: {len(torrent.files)}")
        print(f"Number of pieces: {torrent.pieces}")
        print("--------------------------------------------")

        # Send GET request to the tracker and get the peer list
        peer_list = self.trackerCommunicator.download_announce(torrent)
        if peer_list is None:
            input("Enter to return...")
            return

        # Start the download process
        self.downloadManager.new_download(
            torrent,
            peer_list,
        )

        # print("--------------------------------------------")
        input("Enter to return...")

    def new_upload(self):
        # Input the .torrent file
        torrent = self._input_torrent()
        if torrent is None:
            return 1

        # Display the file information
        print("--------------------------------------------")
        print("Torrent file information:")
        print(f"Name: {torrent.name}")
        print(f"Size: {torrent.size} bytes")
        print(f"Piece size: {torrent.piece_size} bytes")
        print(f"Number of files: {len(torrent.files)}")
        print(f"Number of pieces: {torrent.pieces}")
        print("--------------------------------------------")

        # Create the tracking variable in UploadManager
        self.uploadManager.new_upload(torrent)

        # Announce the completed event to the tracker
        self.trackerCommunicator.upload_announce(torrent)

        # print("--------------------------------------------")
        input("Enter to return...")

    def show_downloading(self):
        num_downloading = self.downloadManager.get_num_downloading()

        print("--------------------------------------------")
        print("Currently downloading: ", num_downloading)
        print("--------------------------------------------")
        print("File name \t Speed \t Connected")

        download_info = self.downloadManager.send_info_to_ui()

        # Display the download information

        print("--------------------------------------------")
        input("Enter to return...")

    def show_uploading(self):
        uploading = self.uploadManager.get_num_uploading()

        print("--------------------------------------------")
        print("Currently uploading: ", uploading)
        print("--------------------------------------------")
        print("File name \t Peer ID \t Uploaded")

        print("--------------------------------------------")
        input("Enter to return...")

    def _input_torrent(self):
        """Get user input the path to a torrent file and return the Torrent object.

        Returns:
            torrent: The Torrent object.
        """
        while True:
            torrent_name = input(
                "Enter the path to the torrent file ('cancel' to return): "
            )
            if torrent_name == "cancel":
                return
            torrent_file = self.torrent_dir + torrent_name
            if not os.path.exists(torrent_file):
                print("File not found. Please try again.")
            else:
                break
        torrent = Torrent.read(torrent_file)

        return torrent

    def clear(self):
        os.system("cls" if os.name == "nt" else "clear")

    def exit(self):
        print("Exiting...")
        self.trackerCommunicator.stopping_announce()
        exit()
