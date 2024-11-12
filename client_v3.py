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
        unique_component = os.urandom(12).hex()
        self.peer_id = f"{client_prefix}{unique_component}"
        self.params = None

    def _read_torrent(self, torrent_file):
        return Torrent.read(torrent_file)

    def _prepare_params(self, torrent_file):
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

    async def _request_peers(self, tracker_url, torrent_file):
        self._prepare_params(torrent_file)
        print("requesting to tracker")
        async with aiohttp.ClientSession() as session:
            async with session.get(tracker_url, params=self.params) as resp:
                raw_resp_data = await resp.read()
                resp_data = bencodepy.decode(raw_resp_data)
                resp_data = {k.decode("utf-8"): v for k, v in resp_data.items()}

                if "failure reason" in resp_data:
                    print(resp_data["failure reason"])
                    return None

                peers = resp_data["peers"]
                return peers

    async def _download_piece(self, peer, info_hash, piece_index, expected_piece_hash):
        print(f"Connecting to {peer['ip']}:{peer['port']}")
        try:
            reader, writer = await asyncio.open_connection(peer["ip"], peer["port"])
            print(f"Connected to {peer['ip']}:{peer['port']}")
            
            handshake = (
                struct.pack("B", 19)
                + b"\x13BitTorrent protocol"
                + b"\x00" * 8
                + info_hash
                + self.peer_id.encode()
            )
            writer.write(handshake)
            await writer.drain()
            
            peer_handshake = await reader.read(68)
            if validate_handshake(peer_handshake, info_hash):
                print(f"Handshake successful with {peer['ip']}:{peer['port']}")

                piece_length = self._read_torrent(self.torrent_file).piece_size
                offset = piece_length * piece_index

                request_message = (
                    struct.pack(">I", 13)
                    + b"\x06"
                    + struct.pack(">III", piece_index, offset, piece_length)
                )
                writer.write(request_message)
                await writer.drain()

                piece_message_length = await reader.read(4)
                piece_message_length = struct.unpack(">I", piece_message_length)[0]
                if piece_message_length == piece_length + 1:
                    message_id = await reader.read(1)
                    if message_id == b"\x07":
                        piece_data = await reader.read(piece_length)
                        piece_hash = hashlib.sha1(piece_data).hexdigest()
                        if piece_hash != expected_piece_hash:
                            print(f"Piece {piece_index} from {peer['ip']}:{peer['port']} has invalid hash")
                            return None

                        return piece_index, piece_data
                    else:
                        print(f"Unexpected message ID received: {message_id}")
                        return None

                else:
                    print(f"Invalid piece message length received: {piece_message_length}")
                    return None

            else:
                print(f"Handshake failed with {peer['ip']}:{peer['port']}")
                writer.close()
                await writer.wait_closed()

        except Exception as e:
            print(f"Failed to connect to {peer['ip']}:{peer['port']}: {e}")
        return None

    async def download_torrent(self, tracker_url, torrent_file):
        peers = await self._request_peers(tracker_url, torrent_file)
        if peers:
            print(f"Received {len(peers)} peers from the tracker.")
        else:
            print("Failed to receive any peers from the tracker.")
            return

        torrent = self._read_torrent(torrent_file)
        info_hash = torrent.infohash
        piece_length = torrent.piece_size
        num_pieces = len(torrent.pieces)
        
        peer_idx = 0
        tasks = []

        async with aiofiles.open(torrent.files[0].name, "wb") as file:
            for piece_index in range(num_pieces):
                expected_piece_hash = torrent.pieces[piece_index]
                task = asyncio.create_task(
                    self._download_piece(peers[peer_idx], info_hash, piece_index, expected_piece_hash)
                )
                tasks.append(task)
                peer_idx = (peer_idx + 1) % len(peers)

            for completed_task in asyncio.as_completed(tasks):
                result = await completed_task
                if result:
                    piece_index, piece_data = result
                    offset = piece_index * piece_length
                    await file.seek(offset)
                    await file.write(piece_data)
                    print(f"Successfully wrote piece {piece_index}")

def validate_handshake(peer_handshake, expected_info_hash):
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

async def handle_client(reader, writer, torrent_file):
    peer_addr = writer.get_extra_info('peername')
    print(f"Incoming connection from {peer_addr}")

    try:
        peer_handshake = await reader.read(68)
        if validate_handshake(peer_handshake, Torrent.read(torrent_file).infohash):
            print(f"Handshake successful with {peer_addr}")

            while True:
                message_length_bytes = await reader.read(4)
                if not message_length_bytes:
                    break

                message_length = struct.unpack(">I", message_length_bytes)[0]
                message_id = await reader.read(1)
                message_payload = await reader.read(message_length - 1)

                if message_id == b"\x06":  # Request message
                    piece_index, offset, length = struct.unpack(">III", message_payload)
                    print(f"Received request for piece {piece_index}")

                    async with aiofiles.open(torrent_file, "rb") as file:
                        await file.seek(piece_index * Torrent.read(torrent_file).piece_size + offset)
                        piece_data = await file.read(length)

                    piece_message = (
                        struct.pack(">I", 9 + length)
                        + b"\x07"
                        + struct.pack(">II", piece_index, offset)
                        + piece_data
                    )
                    writer.write(piece_message)
                    await writer.drain()
                else:
                    print(f"Received message: {message_id}")
        else:
            print(f"Handshake failed with {peer_addr}")
    except Exception as e:
        print(f"Error handling client {peer_addr}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    parser = argparse.ArgumentParser(
        prog="Client",
        description="Connect to tracker",
        epilog="!!!It requires the tracker is running and listening!!!"
    )
    parser.add_argument("--tracker-url", type=str, required=True)
    args = parser.parse_args()
    
    host = get_host_default_interface_ip()
    port = 6881
    print(f"Client running on {host}:{port}")

    torrent_file = input("Enter the path to the torrent file: ")
    while not os.path.exists(torrent_file):
        print("Invalid file path. Please try again.")
        torrent_file = input("Enter the path to the torrent file: ")

    # Start the upload server
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, torrent_file),
        host, 
        port
    )
    async with server:
        # Start the download client
        peer = Peer(host, port, torrent_file)
        download_task = asyncio.create_task(
            peer.download_torrent(args.tracker_url, torrent_file)
        )
        
        await asyncio.gather(
            server.serve_forever(),
            download_task
        )

if __name__ == "__main__":
    asyncio.run(main())