from torf import Torrent
from threading import Thread
import urllib.parse
import hashlib
import bencodepy
import aiohttp
import asyncio
import struct
import socket

client_prefix = "-ST0001-"

class Peer:
    def __init__(self, host, port, file_queue):
        self.host = host
        self.port = port
        self.file_queue = file_queue
        self.peer_choking = True
        self.peer_interested = False
    
        unique_component = os.urandom(12).hex()
        self.peer_id = f"{client_prefix}{unique_component}"

    def _prepare_params(self, torrent_file):
        """Prepare the parameters for the tracker request.

        Args:
            torrent_file (string): .torrent file path 

        Returns:
            dict: dictionary containing the parameters for the tracker request 
        """
        with open(torrent_file, 'rb') as f:
            torrent = Torrent.read(f)
            info_hash = hashlib.sha1(bencodepy.encode(torrent.info)).digest()    
            params = {
                'info_hash': info_hash,
                'peer_id': self.peer_id,
                'port': self.port,
                'uploaded': 0,
                'downloaded': 0,
                'left': torrent.info['length'],
                'compact': 0,
                'event': 'started',
                'numwant': 50,
            }
        return params

    async def request_peers(self, tracker_url, params):
        """Request peers from the tracker.

        Args:
            tracker_url (string): URL to the tracker
            params (dict): dictionary containing the parameters for the tracker request 

        Returns:
            dict: dictionary containing the peers received from the tracker
        """
        # TODO: check for response status for error handling
        async with aiohttp.ClientSession() as session:
            resp = await session.get(tracker_url, params=params)
            resp_data = await resp.read()
            peers = bencodepy.decode(resp_data)['peers']
            return peers

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

        if pstrlen != 19 or pstr != "Bittorrent protocol":
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

    async def connect_single_peer(self, peer, info_hash):
        """Connect to a single peer and perform handshake.

        Args:
            peer (_type_): Dictionary type with keys 'ip' and 'port'
            info_hash (_type_): the info hash of the torrent file to download
        """
        print(f"Connecting to {peer['ip']}:{peer['port']}")
        try:
            reader, writer = await asyncio.open_connection(peer['ip'], peer['port'])
            print(f"Connected to {peer['ip']}:{peer['port']}")
            # Send handshake (pstrlen, pstr, reserved, info_hash, peer_id)
            handshake = b"\x13Bittorrent protocol" + b"\x00" * 8 + info_hash + self.peer_id.encode()
            writer.write(handshake)
            await writer.drain()
            # Receive handshake
            peer_handshake = await reader.read(68)
            if self.validate_handshake(peer_handshake, info_hash):
                print(f"Handshake successful with {peer['ip']}:{peer['port']}")
            else:
                print(f"Handshake failed with {peer['ip']}:{peer['port']}")
                writer.close()
                await writer.wait_closed()

        except Exception as e:
            print(f"Failed to connect to {peer['ip']}:{peer['port']}")
            print(e)

    async def request_piece(self, piece_index):
        # TODO
        pass

    async def download_torrent(self, torrent_file, tracker_url): 
        self._read_torrent_file(torrent_file)
        peers = await self.request_peers(tracker_url, params)
        await self.connect_to_peers(peers)   

    def get_host_default_interface_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

if __name__ == "__main__":
    host = Peer.get_host_default_interface_ip()
    port = 8386 
    peer = Peer(host, port, None)