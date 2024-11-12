from torf import Torrent
import threading
from threading import Thread
import argparse
import hashlib
import bencodepy
import aiohttp
import aiofiles
import asyncio
import struct
import socket
import os

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
    def __init__(self, host, port, torrent_file):
        self.host = host
        self.port = port
        self.torrent_file = torrent_file
        # self.peer_choking = True
        # self.peer_interested = False
        # self.am_choking = True
        # self.am_interested = False

        unique_component = os.urandom(12).hex()
        self.peer_id = f"{client_prefix}{unique_component}"

        self.params = None
    def _parse_message(message):
        """Parses a BitTorrent message.

        Args:
            message: The raw message bytes.

        Returns:
            A tuple containing the message ID and payload, or None if the message is invalid.
        """

        if len(message) < 4:
            return None

        # Parse the message length
        message_length = struct.unpack(">I", message[:4])[0]

        if len(message) < message_length + 4:
            return None

        # Parse the message ID
        message_id = message[4]

        # Parse the message payload
        payload = message[5:message_length + 4]

        return message_id, payload

    def _read_torrent(self, torrent_file):
        return Torrent.read(torrent_file)

    def _prepare_params(self, torrent_file):
        """Prepare the parameters for the tracker request.

        Args:
            torrent_file (string): .torrent file path

        Returns:
            None
        """
        torrent = self._read_torrent(torrent_file)
        info_hash = torrent.infohash
        self.params = {
            "info_hash": info_hash,
            "peer_id": self.peer_id,
            "ip": self.host,
            "port": self.port,
            "uploaded": 0,
            "downloaded": 0,
            "left": torrent.size,
            "compact": 0,
            "event": "started",
            "numwant": 50,
        }

    def _request_peers(self, tracker_url, torrent_file):
        """Request peers from the tracker.

        Args:
            tracker_url (string): URL to the tracker
            params (dict): dictionary containing the parameters for the tracker request

        Returns:
            dict: dictionary containing the peers received from the tracker
        """
        # TODO: check for response status for error handling
        with aiohttp.ClientSession() as session:
            self._prepare_params(torrent_file)
            print("requesting to tracker")
            resp = session.get(tracker_url, params=self.params)
            raw_resp_data = resp.read()

            resp_data = bencodepy.decode(raw_resp_data)
            resp_data = {k.decode("utf-8"): v for k, v in resp_data.items()}

            if "failure reason" in resp_data:
                print(resp_data["failure reason"])
                return None

            peers = resp_data["peers"]
            return peers


    async def _download_piece(self, peer, info_hash, piece_index, expected_piece_hash):
        """Download a piece from the peer.

        Args:
            peer (dict): dictionary having two keys: ip and port 
            info_hash (string): info hash of the torrent file
            piece_index (int): index of the piece to download
            expected_piece_hash (string): expected hash of the piece

        Returns:
            tuple: piece index and piece data
        """
        print(f"Connecting to {peer['ip']}:{peer['port']}")
        try:
            reader, writer = await asyncio.open_connection(peer["ip"], peer["port"])
            print(f"Connected to {peer['ip']}:{peer['port']}")
            # Send handshake (pstrlen, pstr, reserved, info_hash, peer_id)
            handshake = (
                struct.pack("B", 19)
                + b"\x13BitTorrent protocol"
                + b"\x00" * 8
                + info_hash
                + self.peer_id.encode()
            )
            writer.write(handshake)
            await writer.drain()
            # Receive handshake
            peer_handshake = await reader.read(68)
            if validate_handshake(peer_handshake, info_hash):
                print(f"Handshake successful with {peer['ip']}:{peer['port']}")

                # send request msg
                piece_length = self._read_torrent(self.torrent_file).piece_size
                offset = piece_length * piece_index

                request_message = (
                    struct.pack(">I", 13)  
                    + b"\x06"  
                    + struct.pack(">III", piece_index, offset, piece_length)
                )
                writer.write(request_message)
                await writer.drain()

                # Receive piece message (length, message ID, piece data)
                piece_message_length = await reader.read(4)  # Read the message length
                piece_message_length = struct.unpack(">I", piece_message_length)[0]
                if piece_message_length == piece_length + 1:  # Check for correct message length
                    message_id = await reader.read(1)  # Read message ID (should be 7 for Piece)
                    if message_id == b"\x07":
                        piece_data = await reader.read(piece_length)

                        # Validate piece data integrity (optional)
                        piece_hash = hashlib.sha1(piece_data).hexdigest()
                        if piece_hash != expected_piece_hash:
                            print(f"Piece {piece_index} from {peer['ip']}:{peer['port']} has invalid hash")
                            return None  # Or handle invalid piece data differently

                        return piece_index, piece_data
                    else:
                        print(f"Unexpected message ID received: {message_id}")
                        return None  # Or handle unexpected message

                else:
                    print(f"Invalid piece message length received: {piece_message_length}")
                    return None  # Or handle invalid message length

            else:
                print(f"Handshake failed with {peer['ip']}:{peer['port']}")
                writer.close()
                await writer.wait_closed()

        except Exception as e:
            print(f"Failed to connect to {peer['ip']}:{peer['port']}")
            print(e)
        

    async def download_torrent(self, tracker_url, torrent_file):
        peers = self._request_peers(tracker_url, torrent_file)
        if peers:
            print(f"Received {len(peers)} peers from the tracker.")
        else:
            print("Failed to receive any peers from the tracker.")
            return

        torrent = Torrent.read(torrent_file)
        info_hash = torrent.infohash
        piece_length = torrent.piece_size
        num_pieces = torrent.pieces
        
        peer_idx = 0

        downloaded_pieces = [False] * num_pieces
        download_queue = asyncio.Queue()

        async with aiofiles.open(torrent.files[0].name, "wb") as file:
            for piece_index in range(num_pieces):
                expected_piece_hash = torrent.pieces[piece_index]
                task = asyncio.create_task(self._download_piece(peers[peer_idx], info_hash, piece_index, expected_piece_hash))
                peer_idx = (peer_idx + 1) % len(peers)
                download_queue.put_nowait(task)
            while not download_queue.empty():
                task = await download_queue.get()
                piece_index, piece_data = await task
                offset = piece_index * piece_length
                await file.seek(offset)
                await file.write(piece_data)
                download_queue.task_done()

def validate_handshake(peer_handshake, expected_info_hash):
    """Validate the handshake received from a peer.

    Args:
        peer_handshake (string): handshake received from a peer
        expected_info_hash (string): info hash of the torrent file to download

    Returns:
        bool: True if handshake is valid, False otherwise
    """
    if len(peer_handshake) != 68:
        return False

    pstrlen = struct.unpack("B", peer_handshake[0:1])[0]
    pstr = peer_handshake[1:20].decode("utf-8", errors="ignore")

    if pstrlen != 19 or pstr != "BitTorrent protocol":
        print("Invalid protocol string.")
        return False

    reserved = peer_handshake[20:28]

    info_hash = peer_handshake[28:48]
    peer_id = peer_handshake[48:68]

    if info_hash != expected_info_hash:
        print("Info hash mismatch.")
        return False

    print(f"Reserved Bytes: {reserved}")
    print(f"Peer ID: {peer_id}")

    return True

async def download_thread(host, port, tracker_url):
    torrent_file = input("Enter the path to the torrent file: ")
    while True:
        if not os.path.exists(torrent_file):
            print("Invalid file path. Please try again.")
        else:
            peer = Peer(host, port, torrent_file)
            asyncio.run(peer.download_torrent(tracker_url, torrent_file))

async def upload_thread(host, port, torrent_file):
    """Starts an asynchronous server listening for incoming connections
       from peers and handles uploading pieces."""

    receiving_peer = Peer(host, port, torrent_file)
    
    async def handle_client(reader, writer):
        peer_addr = writer.get_extra_info('peername')
        print(f"Incoming connection from {peer_addr}")

        # Receive handshake
        peer_handshake = await reader.read(68)
        if validate_handshake(peer_handshake, receiving_peer._read_torrent(torrent_file).infohash):
            print(f"Handshake successful with peer_addr")

        else:
            print(f"Handshake failed with {peer_addr}")
            writer.close()
            await writer.wait_closed()
        # Handle incoming messages
        while True:
            message_length_bytes = await reader.read(4)
            if not message_length_bytes:
                break  # Connection closed

            message_length = struct.unpack(">I", message_length_bytes)[0]
            message_id = await reader.read(1)
            message_payload = await reader.read(message_length - 1)

            if message_id == 6:  # Request message
                # Parse the request message
                piece_index, offset, length = struct.unpack(">III", message_payload)
                print(f"Received request for piece {piece_index}")

                # Read the piece data from the file
                piece_length = receiving_peer._read_torrent(torrent_file).piece_size
                with open(torrent_file, "rb") as file:
                    file.seek(piece_index * piece_length + offset)
                    piece_data = file.read(length)

                # Send the piece message
                piece_message = (
                    struct.pack(">I", 9 + length)
                    + b"\x07"
                    + struct.pack(">II", piece_index, offset)
                    + piece_data
                )
                writer.write(piece_message)
                await writer.drain()
            else:
                # Handle other message types (optional)
                print(f"Received message: {message_id}")

            # ... send choke/unchoke messages as needed ...

        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_client, host, port)
    addrs = ', '.join(str(s.getsockname()) for s in server.sockets)
    print(f'Listening for uploads request on {addrs}')

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Client",
        description="Connect to tracker",
        epilog="!!!It requires the tracker is running and listening!!!",
    )
    parser.add_argument("--tracker-url", type=str, required=True)

    args = parser.parse_args()
    tracker_url = args.tracker_url

    host = get_host_default_interface_ip()
    port = 6881
    print(f"Client running on {host}:{port}")

    async def main():
        download_task = asyncio.create_task(
            download_thread(host, port, tracker_url)
        )
        upload_task = asyncio.create_task(upload_thread(host, port, "pic.torrent"))

        await download_task
        await upload_task

    asyncio.run(main())
