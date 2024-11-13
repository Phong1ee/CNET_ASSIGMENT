from torf import Torrent
import threading
from threading import Thread
import argparse
import bencodepy
import struct
import socket
import os
import requests
import hashlib
import time

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

class UI:
    def __init__(self, peer):
        self.peer = peer

    def run(self):
        while True:
            self.clear()
            option = self.menu()

            if option == '1':
                self.download_torrent()
            elif option == '2':
                self.clear()
                self.donwload_status()
            elif option == '3':
                self.clear()
                self.upload_status()
            elif option == '4':
                return
            else:
                print('Invalid option')
    
    def menu(self):
        print('--------------------------------------------')
        print('Welcome to out Simple BitTorrent client! You are Online!, other peers may connect to you')
        print('[1] Download')
        print('[2] View downloading files')
        print('[3] View uploading files')
        print('[4] Exit')
        print('--------------------------------------------')
        option = input('Choose an option: ')

        return option

    def download_torrent(self):
        # Input the .torrent file
        while True:
            torrent_file = input("Enter the path to the torrent file ('cancel' to return): ")
            if torrent_file == "cancel":
                break
            if not os.path.exists(torrent_file):
                print("File not found. Please try again.")
            else:
                break
        if torrent_file == "cancel":
            return
        download_thread = Thread(target=peer.download_thread, args=(torrent_file, args.tracker_url))
        download_thread.start()

    def donwload_status(self):
        downloading = self.peer.downloading

        print('--------------------------------------------')
        print('Currently downloading: ', downloading)
        print('--------------------------------------------')
        print('File name \t Speed \t Connected')
        
        for info_hash, info in peer.downloading_data.items():
            print(f"{info['name']}",end='\t')
            print(f"{info['download_speed']}",end='\t')
            print(f"{info['connected_peers']} / {info['num_peers']}")

        print('--------------------------------------------')
        input('Enter to return...')

    def upload_status(self):
        uploading = self.peer.uploading

        print('--------------------------------------------')
        print('Currently uploading: ', uploading)
        print('--------------------------------------------')
        print('File name \t Peer ID \t Uploaded')
        
        for address, info in peer.client_being_uploaded.items():
            print(f"{info['file']}",end='\t')
            print(f"{info['peer_id']}",end='\t')
            print(f"{info['uploaded']}")

        print('--------------------------------------------')
        input('Enter to return...')

    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')


class Peer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        unique_component = os.urandom(12).hex()
        self.id = f"{client_prefix}{unique_component}"
        self.uploading = 0
        self.downloading = 0
        self.client_being_uploaded = {}
        self.downloading_data = {}
        self.upload_lock = threading.Lock()
        self.download_lock = threading.Lock()

    def download_thread(self, torrent_file, tracker_url):    
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
        peers = self._request_peers(tracker_url+'/announce', params)
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
        
        self.download_lock.acquire()
        self.downloading += 1
        self.downloading_data[torrent.infohash] = {'name': torrent.name,
                                                   'num_peers': len(peers),
                                                   'connected_peers': 0,
                                                   'total_downloaded': 0, 
                                                   'downloaded': 0,
                                                   'total': torrent.size,
                                                   'download_speed': 0,
                                                   'last_seen': time.time()}
        self.download_lock.release()

        # Connect to peers
        peer_idx = 0
        download_threads = []
        for piece_idx in range(torrent.pieces):
            download_threads.append(Thread(target=self._download_piece, args=(peers[peer_idx], torrent.infohash, piece_idx, torrent.hashes, torrent.piece_size)))
            peer_idx = (peer_idx + 1) % len(peers)

        [thread.start() for thread in download_threads]
        timer = threading.Timer(1, self._update_download_speeds)
        timer.start()

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
        # Create a server socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host, port))
        server_socket.listen(6)

        # Listen for incoming connections
        upload_threads = []
        while True:
            try:
                client_socket, address = server_socket.accept()
                new_upload_thread = Thread(target=self._upload_piece, args=(client_socket, address))
                new_upload_thread.start()
                upload_threads.append(new_upload_thread)
            except KeyboardInterrupt:
                server_socket.close()
                [thread.join() for thread in upload_threads]
                return 0

    def _download_piece(self, peer, info_hash, piece_index, hashes, piece_length):
        print(f"Connecting to {peer['ip']}:{peer['port']}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)

        try:
            sock.connect((peer['ip'], int(peer['port'])))
            # Handshake
            pstrlen = struct.pack("B", 19)
            pstr = b"BitTorrent protocol"
            reserved = b"\x00" * 8
            handshake = pstrlen + pstr + reserved + info_hash.encode() + self.id.encode()

            # Send handshake
            sock.send(handshake)

            # Receive handshake
            peer_handshake = sock.recv(68).decode()

            if self._validate_handshake(peer_handshake, info_hash, peer['peer_id']):
                self.download_lock.acquire()
                self.downloading_data[info_hash]['connected_peers'] += 1
                self.download_lock.release()

                # Receive unchoke message
                unchoke = sock.recv(5).decode()
                if unchoke[-1] == 1:
                    # Send request message
                    offset = 0
                    request = struct.pack(">IBIII", 13, 6, piece_index, offset, piece_length)
                    sock.send(request)

                    # Receive piece message
                    piece = sock.recv(piece_length + 9).decode()

                    # Validate piece
                    piece_data = piece[9:]
                    piece_hash = hashlib.sha1(piece_data).digest() 
                    if piece_hash == hashes[piece_index]:
                        self.download_lock.acquire()
                        self.downloading_data[info_hash]['downloaded'] += len(piece_data)
                        self.downloading_data[info_hash]['total_downloaded'] += len(piece_data)
                        self.download_lock.release()
                        return piece_index, piece_data
                    return 3
                return 2
            else:
                print(f"[{self.id}] Handshake failed.")
                return 1
        except socket.timeout:
            print(f"Connection to {peer['ip']}:{peer['port']} timed out.")
        finally:
            sock.close()
            self.download_lock.acquire()
            self.downloading_data[info_hash]['connected_peers'] -= 1
            self.download_lock.release()

    def _upload_piece(self, sock, address):
        print(f"{address} is requesting connection.")

        # Receive handshake
        peer_handshake = sock.recv(68).decode()

        info_hash = peer_handshake[28:48]
        peer_id = peer_handshake[48:68]
        torrent_file = self._check_local_repo(info_hash)
        
        if torrent_file:
            torrent = Torrent.read(torrent_file)
            if not self._validate_handshake(peer_handshake, torrent.infohash, peer_id):
                print(f"{address} handshake failed.")
                sock.close()
                return

            # Handshake
            pstrlen = struct.pack("B", 19)
            pstr = b"BitTorrent protocol"
            reserved = b"\x00" * 8
            handshake = pstrlen + pstr + reserved + torrent.infohash.encode() + self.id.encode()

            # Send handshake
            sock.send(handshake)

            # Send unchoke message
            unchoke = struct.pack(">IB", 1, 1)
            sock.send(unchoke)

            self.upload_lock.acquire()
            self.uploading += 1
            self.client_being_uploaded[address] = {'connection_time': time.time(),
                                                   'file': torrent.name,
                                                   'peer_id': peer_id,
                                                   'uploaded': 0,}
            self.upload_lock.release()

            # Receive request message
            request = sock.recv(17).decode()
            piece_index = struct.unpack(">I", request[5:9])[0]
            offset = struct.unpack(">I", request[9:13])[0]
            piece_length = struct.unpack(">I", request[13:17])[0]

            # Read piece data
            piece_data = self._read_piece(torrent, piece_index)

            # Send piece message
            piece = struct.pack(">IBIII", piece_length + 9, 7, piece_index, offset, piece_data)
            sock.send(piece)
            self.upload_lock.acquire()
            self.client_being_uploaded[address]['uploaded'] += len(piece_data)
            self.upload_lock.release()

            print(f"{address} uploaded piece {piece_index}.")
        else:
            print("Torrent file not found.")
            sock.close()
            return
        sock.close()
        return

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

    def _check_local_repo(self, info_hash):
        torrent_files = [f for f in os.listdir() if f.endswith(".torrent")]
        for torrent_file in torrent_files:
            torrent = Torrent.read(torrent_file)
            if torrent.infohash == info_hash:
                return torrent_file
        return None

    def _read_piece(torrent, piece_idx):
        if torrent.mode == "singlefile":
            offset = piece_idx * torrent.piece_size
            try:
                with open(torrent.name, "rb") as file:
                    file.seek(offset)
                    data = file.read(torrent.piece_size)
                    if not data:
                        return None
                    return data
            except FileNotFoundError as e:
                print(f"File not found: {e}")
                return None
            except IOError as e:
                print(f"Error reading file: {e}")
                return None
        else: # multifile
            pass

    def _update_download_speeds(self):
        self.download_lock.acquire()
        for info_hash, info in self.downloading_data.items():
            elapsed_time = time.time() - info["last_seen"]
            if elapsed_time > 0:
                info["download_speed"] = info["downloaded"] / elapsed_time
                info["downloaded"] = 0  # Reset uploaded bytes for the next interval
                info["last_seen"] = time.time()

        self.download_lock.release()
        timer = threading.Timer(1, self._update_download_speeds)
        timer.start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Client",
        description="Connect to tracker",
        epilog="!!!It requires the tracker is running and listening!!!"
    )
    parser.add_argument("--tracker-url", type=str, required=True)
    # parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    
    host = get_host_default_interface_ip()
    port = 6881
    print(f"Client running on {host}:{port}")

    peer = Peer(host, port)
    
    upload_thread = Thread(target=peer.upload_thread, args=(host, port), daemon=True)
    upload_thread.start()
    download_threads = []

    ui = UI(peer)
    ui.run()