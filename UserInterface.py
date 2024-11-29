import os
import msvcrt
import time
import sys
from time import sleep

from torf import Torrent

from DownloadManager import DownloadManager
from FileManager import FileManager
from TrackerCommunicator import TrackerCommunicator
from UploadManager import UploadManager


class UserInterface:
    def __init__(
        self,
        ip: str,
        port: int,
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
        self.ip = ip
        self.port = port
        self.torrent_dir = torrent_dir
        self.dest_dir = dest_dir
        self.downloadManager = downloadManager
        self.uploadManager = uploadManager
        self.trackerCommunicator = trackerCommunicator
        self.fileManager = fileManager

    def run(self):
        while True:
            self._clear()
            option = self.menu()

            match option:
                case "1":
                    self._clear()
                    self.new_download()
                case "2":
                    self._clear()
                    self.new_upload()
                case "3":
                    self._clear()
                    self.show_downloading()
                case "4":
                    self._clear()
                    self.show_uploading()
                case "5":
                    self.exit()
                case _:
                    print("Invalid option, only input 1->5")
                    sleep(1)

    def menu(self):
        print(f"Welcome to our Simple BitTorrent client! You are {self.ip}:{self.port}")
        print("You are Online!, other peers may connect to you")
        print("--------------------------------------------")
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
        # print("Peer list: ", peer_list)
        if peer_list is None:
            print("No peers found.")
            input("Enter to return...")
            return

        # Start the download process
        print("Download started for infohash: ", torrent.infohash)
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
            return

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
        print("Upload started for infohash: ", torrent.infohash)

        # Announce the completed event to the tracker
        self.trackerCommunicator.upload_announce(torrent)
        print("Announced to tracker.")

        # print("--------------------------------------------")
        input("Enter to return...")

    def show_downloading(self):
        last_it_progresses = [0] * len(self.downloadManager.get_downloaded())
        last_it_totals = [0] * len(self.downloadManager.get_total())

        while True:
            self._clear()
            download_info = self._get_download_info(last_it_progresses, last_it_totals)

            print("--------------------------------------------")
            print(f"Currently downloading: {len(download_info)}")
            print("--------------------------------------------")
            print(
                f"{'File Name':<20}{'Progress':<30}{'Speed':<15}{'Peers':<10}{'Connected':<10}"
            )
            # print(download_info)

            for info in download_info:
                print(
                    f"{info['file_name']:<20}{info['progress']:<30}{info['rate']:<15}{info['peers']:<10}{info['connected_peers']:<10}"
                )

            print("--------------------------------------------")
            print("Press 'q' to return.")

            time.sleep(0.05)

            if self._input_quit():
                break

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
            torrent_list = self.fileManager.list_torrents()
            print("Choose one of the availabe torrents:")
            print("--------------------------------------------")
            for i, torrent in enumerate(torrent_list):
                print(f"[{i}] {torrent}")
            print("--------------------------------------------")
            option = input("Enter the index or 'q' to return: ")
            try:
                if option == "q":
                    break
                if int(option) < 0 or int(option) > (len(torrent_list) - 1):
                    raise ValueError
                torrent_name = torrent_list[int(option)]
                torrent_file = self.torrent_dir + torrent_name
                if not os.path.exists(torrent_file):
                    print("File not found. Please try again.")
                    input("Enter to continue...")
                torrent = Torrent.read(torrent_file)

                return torrent

            except ValueError:
                print(
                    f"Invalid option. Please ony input 0->{len(torrent_list)-1} or 'q'"
                )
                input("Enter to continue...")
                self._clear()
                continue

    def _get_download_info(self, last_it_progresses, last_it_totals):
        """
        Fetch download information for all active downloads.

        Args:
            last_it_progresses (list[int]): The previously recorded downloaded bytes for each file.
            last_it_totals (list[int]): The previously recorded total bytes for each file.

        Returns:
            list[dict]: A list of dictionaries containing download information.
        """
        # Get the current state of downloads
        file_names = self.downloadManager.get_file_names()
        progresses = self.downloadManager.get_downloaded()
        totals = self.downloadManager.get_total()
        num_peers = self.downloadManager.get_num_peers()
        num_connected_peers = self.downloadManager.get_num_connected_peers()
        # Print all the above information
        # print("progresses:", progresses)
        # print("totals", totals)
        # print("num peers", num_peers)
        # print("num connected peers", num_connected_peers)

        # Calculate download rates and format them appropriately
        print("rates:")
        download_rates = []
        for i, progress in enumerate(progresses):
            rate = (progress - last_it_progresses[i]) * 20
            download_rates.append(self._format_rate(rate))

        # Update the last iteration's values
        last_it_progresses[:] = progresses[:]
        last_it_totals[:] = totals[:]

        info = [
            {
                "file_name": file_names[i],
                "progress": f"{self._format_size(progress)} / {self._format_size(total)}",
                "rate": download_rates[i],
                "peers": num_peers[i],
                "connected_peers": num_connected_peers[i],
            }
            for i, (progress, total) in enumerate(zip(progresses, totals))
        ]

        return info

    def _format_size(self, size):
        """
        Convert file size (bytes) into a human-readable format.

        Args:
            size (int): File size in bytes.

        Returns:
            str: Human-readable format (e.g., "512.00 KB", "1.23 MB").
        """
        if size >= 1_000_000:
            return f"{size / 1_000_000:.2f} MB"
        elif size >= 1_000:
            return f"{size / 1_000:.2f} KB"
        else:
            return f"{size} B"

    def _format_rate(self, rate):
        """
        Convert download rate (bytes/s) into a human-readable format.

        Args:
            rate (int): Download speed in bytes per second.

        Returns:
            str: Human-readable format (e.g., "512.00 KB/s", "1.23 MB/s").
        """
        if rate >= 1_000_000:
            return f"{rate / 1_000_000:.2f} MB/s"
        elif rate >= 1_000:
            return f"{rate / 1_000:.2f} KB/s"
        else:
            return f"{rate} B/s"

    def _input_quit(self):
        """
        Check for user input to quit the process without blocking.

        Returns:
            bool: True if the user wants to quit, False otherwise.
        """
        # Check for Windows
        if sys.platform == "win32":
            if msvcrt.kbhit():  # Check if a key was pressed
                key = msvcrt.getch()  # Read the key
                if key == b"q":  # Check if it matches 'q'
                    return True
            return False
        else:
            import select

            i, o, e = select.select([sys.stdin], [], [], 0)
            if i:
                key = sys.stdin.read(1)  # Read one character
                if key.lower() == "q":  # Check if it matches 'q'
                    return True
            return False

    def _clear(self):
        os.system("cls" if os.name == "nt" else "clear")

    def exit(self):
        print("Exiting...")
        self.uploadManager.stop()
        self.trackerCommunicator.stopping_announce()
        exit()
