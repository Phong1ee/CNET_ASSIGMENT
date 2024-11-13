from torf import Torrent
import threading
from threading import Thread
import argparse
import bencodepy
import aiofiles
import struct
import socket
import os
import requests
from math import ceil

client_prefix = "-ST0001-"

def get_host_default_interface_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

class Peer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        unique_component = os.urandom(12).hex()
        self.id = f"{client_prefix}{unique_component}"

    def download_thread(self, host, port, tracker_url):    
        # Input the .torrent file
        while True:
            torrent_file = input("Enter the path to the torrent file: ")
            if not os.path.exists(torrent_file):
                print("File not found. Please try again.")
            else:
                break
        
        # Read the torrent file
        torrent = Torrent.read(torrent_file)

        # Prepare the parameters
        params = {
            "info_hash": torrent.infohash,
            "peer_id": self.id,
            "ip": self.host,
            "port": self.port,
            "uploaded": 0,
            "downloaded": 0,
            "left": torrent.size,
            "compact": 0,
            "event": "started",
            "numwant": 50,
        }

        # Get peer list from tracker
        peers = self._request_peers(tracker_url, params)
        if peers == 1 or peers == 2:
            return 1

        # Initialize tracking variables
        downloaded_data = {}
        files = {} # List of files to be downloaded
        pointer = 0
        for f in torrent.files:
            trailing_start = 0
            trailing_end = 0
            size = f.size
            name = f.name
            if pointer % torrent.piece_size != 0:
                trailing_start = torrent.piece_size - pointer % torrent.piece_size 
                # print("trailing_start: ", trailing_start)
            end = pointer + size
            if end % torrent.piece_size != 0:
                trailing_end = end % torrent.piece_size
                # print("trailing_end: ", trailing_end)
            pointer += size 
            files[name] = {"trail_start": trailing_start, "trail_end": trailing_end}

        # Connect to peers
        peer_idx = 0
        download_threads = []
        for piece_idx in range(torrent.pieces):
            download_threads.append(Thread(target=self._download_piece, args=(peers[peer_idx], torrent.infohash, piece_idx, torrent.piece_size)))
            peer_idx = (peer_idx + 1) % len(peers)

        [thread.start() for thread in download_threads]
        for thread in download_threads:
            thread.join()
            piece_idx, piece_data = thread.result()
            downloaded_data[piece_idx] = piece_data

        # Save downloaded data to file
        piece_idx = 0
        for f in torrent.files:
            trailing_start = files[f.name]['trail_start']
            trailing_end = files[f.name]['trail_end']
            name = f.name
            size = f.size
            with open(name, "wb") as file:
                if trailing_start:
                    file.write(downloaded_data[piece_idx][-trailing_start:])
                    size -= trailing_start
                    piece_idx += 1
                while size >= torrent.piece_size:
                    file.write(downloaded_data[piece_idx])
                    size -= torrent.piece_size
                    piece_idx += 1
                if trailing_end:            
                    file.write(downloaded_data[piece_idx][:trailing_end])

        return 0

    def upload_thread(self, host, port):
        pass

    def _request_peers(self, tracker_url, params):
        # Send GET request with params to tracker
        raw_response = requests.get(tracker_url, params=params)
        response = bencodepy.decode(raw_response.content)
        response = {k.decode('utf-8'): v for k, v in response.items()}
        if "failure reason" in response:
            print(f"[{self.id}] Error: {response['failure reason']}")
            return 1  
        
        peers = response["peers"]
        for peer in peers:
            new_peer = {}
            for key, value in peer.items():
                new_key = key.decode('utf-8')
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                new_peer[new_key] = value
            peers[peers.index(peer)] = new_peer 

        if peers:
            return peers
        else:
            print(f"[{self.id}] No peers found.")
            return 2

    def _download_piece(self, peer, info_hash, piece_index, piece_length):
        print(f"Connecting to {peer['ip']}:{peer['port']}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((peer['ip'], int(peer['port'])))

        # Handshake
        pstrlen = struct.pack("B", 19)
        pstr = b"BitTorrent protocol"
        reserved = b"\x00" * 8
        handshake = pstrlen + pstr + reserved + info_hash + self.id.encode()

        # Send handshake
        sock.send(handshake)

        # Receive handshake
        peer_handshake = sock.recv(68)

        if self._validate_handshake(peer_handshake, info_hash):
            # Receive unchoke message
            unchoke = sock.recv(5)
            if unchoke[-1] == 1:
                # Send request message
                offset = piece_length * piece_index
                request = struct.pack(">IBIII", 13, 6, piece_index, offset, piece_length)
                sock.send(request)

                # Receive piece message
                piece = sock.recv(piece_length + 9)

                # Validate piece
                received_piece_length = struct.unpack(">I", piece[0:4])[0]
                received_piece_index = struct.unpack(">I", piece[4:8])[0]
                piece_data = piece[9:]
                if received_piece_length == piece_length + 1 and received_piece_index == piece_index:
                    return piece_index, piece_data
                return 3
            return 2
        else:
            print(f"[{self.id}] Handshake failed.")
            return 1

    def _validate_handshake(peer_handshake, expected_info_hash, expected_peer_id):
        if len(peer_handshake) != 68:
            return False

        pstrlen = struct.unpack("B", peer_handshake[0:1])[0]
        pstr = peer_handshake[1:20].decode("utf-8", errors="ignore")

        if pstrlen != 19 or pstr != "BitTorrent protocol":
            print("Invalid protocol string.")
            return False

        info_hash = peer_handshake[28:48]
        peer_id = peer_handshake[48:68]

        if info_hash != expected_info_hash:
            print("Info hash mismatch.")
            return False
        if peer_id == expected_peer_id:
            print("Peer ID mismatch.")
            return False

        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Client",
        description="Connect to tracker",
        epilog="!!!It requires the tracker is running and listening!!!"
    )
    parser.add_argument("--tracker-url", type=str, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    
    host = get_host_default_interface_ip()
    port = args.port 
    print(f"Client running on {host}:{port}")

    peer = Peer(host, port)

    download_thread = Thread(target=peer.download_thread, args=(host, port, args.tracker_url))
    upload_thread = Thread(target=peer.upload_thread, args=(host, port))

    download_thread.start()
    upload_thread.start()

    download_thread.join()
    upload_thread.join()