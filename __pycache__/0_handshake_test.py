from torf import Torrent
import socket
from PeerCommunicator import PeerCommunicator
from PieceManager import PieceManager
from UploadManager import UploadManager
from FileManager import FileManager
import argparse


def main(mode, client_id, server_id, torrent, ip, port):
    if mode == "server":
        fileManager = FileManager("./torrents/", "./download_path/")
        uploadManager = UploadManager(
            server_id,
            ip,
            port,
            "./torrents/",
            fileManager,
        )
        infohash = torrent.infohash
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((ip, port))
        server.listen(1)
        conn, _ = server.accept()
        print("Connected to client")

        peer_communicator = PeerCommunicator(conn)

        # Receive handshake from the peer
        handshake = peer_communicator.receive_handshake()
        requested_infohash = handshake[28:48].hex()
        print(
            "[INFO-UploadManager-_upload_piece_thread] Requested infohash:",
            requested_infohash,
        )

        # Check if local torrent folder has the requested infohash
        torrent_exist = fileManager.check_local_torrent(requested_infohash)
        if not torrent_exist:
            print("[INFO-UploadManager-_upload_piece_thread] Torrent does not exist")
            conn.close()
            return None

        # Get the torrent file path
        file_path = fileManager.get_original_file_path(requested_infohash)
        print("[INFO-UploadManager-_upload_piece_thread] File path:", file_path)
        pieceManager = PieceManager(torrent, file_path)

        # Send handshake to the peer
        peer_communicator.send_handshake(server_id, infohash)

        # Send unchoke message to the peer
        peer_communicator.send_unchoke()

        # Receive interested message from the peer
        peer_communicator.receive_interested()

        # Get the bitfield of the torrent
        bitfield = pieceManager.bitfield
        print("[INFO-UploadManager-_upload_piece_thread] Bitfield:", bitfield)

        # Send bitfield message to the peer
        peer_communicator.send_bitfield(bitfield)

        # Receive request message from the peer
        piece_idx = peer_communicator.receive_request()
        print(
            "[INFO-UploadManager-_upload_piece_thread] Received request for piece",
            piece_idx,
        )

        # Get the piece data
        piece_data = pieceManager.get_piece_data(piece_idx)

        # Send piece message to the peer
        peer_communicator.send_piece(piece_idx, piece_data)
        # manager = PieceManager(torrent, "./download_path/asm1.pdf")
        # server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # server.bind((ip, port))
        # server.listen(1)
        # conn, addr = server.accept()
        # comm = PeerCommunicator(conn)
        # comm.send_unchoke()
        # comm.receive_interested()
        # comm.send_bitfield(manager.bitfield)
        # piece_idx = comm.receive_request()
        # comm.send_piece(piece_idx, manager.get_piece_data(piece_idx))

    if mode == "client":
        manager = PieceManager(torrent, "./download_path/asm1.pdf")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        print("Connected to server")
        comm = PeerCommunicator(sock)
        comm.send_handshake(client_id, torrent.infohash)
        comm.receive_handshake()
        comm.receive_unchoke()
        comm.send_interested()
        bitfield = comm.receive_bitfield()
        print("Received bitfield", bitfield)
        comm.send_request(0)
        piece_idx, piece_data = comm.receive_piece()
        # print("Received piece data", piece_data)
        if manager.verify_piece(piece_data, piece_idx):
            print("piece verified!")
            with open("./download_test/asm1.pdf", "wb") as file:
                file.write(piece_data)
        else:
            print("piece not verified!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Handshake Test",
        description="Test the handshake between peers.",
    )
    parser.add_argument("--mode", type=str, help="server or client")
    parser.add_argument("--port", type=int, help="Port number to listen on.")
    args = parser.parse_args()

    mode = args.mode
    ip = "192.168.1.6"
    port = 6881

    torrent = Torrent.read("./torrents/asm1.torrent")
    server_id = "-ST0001-699544607770"
    client_id = "-ST0001-699544607771"

    main(mode, client_id, server_id, torrent, ip, port)
