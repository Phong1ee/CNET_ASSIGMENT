import PieceManager
import DownloadManager
import FileManager
import threading

if __name__ == "__name__":
    # Initialize the download manager
    download_manager = DownloadManager.get_instance()

    # Start the download manager
    download_manager.start()

    ui = UserInterface(download_manager)
    ui.run()
