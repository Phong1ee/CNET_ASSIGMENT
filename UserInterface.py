from time import sleep

class UserInterface:
    def __init__(self, download_manager):
        self.download_manager = download_manager

    def run(self):
        while True:
            self.clear()
            option = self.menu()

            match option:
                case "1":
                    self.clear()
                    self.download()
                case "2":
                    self.clear()
                    self.show_downloading()
                case "4":
                    self.clear()
                    self.upload_status()
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

    def download(self):
        # Input the .torrent file
        while True:
            torrent_file = input(
                "Enter the path to the torrent file ('cancel' to return): "
            )
            if torrent_file == "cancel":
                break
            if not os.path.exists(torrent_file):
                print("File not found. Please try again.")
            else:
                break
        if torrent_file == "cancel":
            return

        # Read the torrent file
        torrent = Torrent.read(torrent_file)

        # Display the file information
        print("--------------------------------------------")
        print("Torrent file information:")
        print(f"Name: {torrent.name}")
        print(f"Size: {torrent.size} bytes")
        print(f"Piece size: {torrent.piece_size} bytes")
        print(f"Number of files: {len(torrent.files)}")
        print(f"Number of pieces: {torrent.pieces}")
        print("--------------------------------------------")

        # Prepare the parameters
        params = {
            "info_hash": torrent.infohash,
            "peer_id": self.peer.id,
            "ip": self.peer.host,
            "port": self.peer.port,
            "uploaded": 0,
            "downloaded": 0,
            "left": torrent.size,
            "compact": 0,
            "event": "started",
            "numwant": 50,
        }

        # Get peer list from tracker
        print(f"Requesting peers from tracker {args.tracker_url+'/announce'}...")
        peers = self.peer._request_peers(args.tracker_url + "/announce", params)
        if peers == 1:
            print("[Error] Connection to tracker failed.")
        elif peers == 2:
            pass
        elif peers == 3:
            print("[Error] No peers found.")
        else:
            print("Starting download...")
            download_thread = Thread(target=peer.download_thread, args=(peers, torrent))
            download_thread.start()
        print("--------------------------------------------")
        input("Enter to return...")

    def donwload_status(self):
        num_downloading = self.peer.downloading

        print("--------------------------------------------")
        print("Currently downloading: ", num_downloading)
        print("--------------------------------------------")
        print("File name \t Speed \t Connected")

        download_info = downloadManager.

        print("--------------------------------------------")
        input("Enter to return...")

    def upload_status(self):
        uploading = self.peer.uploading

        print("--------------------------------------------")
        print("Currently uploading: ", uploading)
        print("--------------------------------------------")
        print("File name \t Peer ID \t Uploaded")

        for info in peer.client_being_uploaded.values():
            print(f"{info['file']}", end="\t")
            print(f"{info['peer_id']}", end="\t")
            print(f"{info['uploaded']}")

        print("--------------------------------------------")
        input("Enter to return...")

    def clear(self):
        os.system("cls" if os.name == "nt" else "clear")

    def exit(self):
        print("Exiting...")
        # TODO: announce exit to tracker
        exit()
