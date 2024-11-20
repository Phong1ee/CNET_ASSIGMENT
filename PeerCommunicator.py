from socket import socket
import struct


class PeerCommunicator:
    def __init__(self):
        pass

    def _validate_handshake(self, peer_handshake, expected_info_hash, expected_peer_id):
        if len(peer_handshake) != 68:
            return False

        pstrlen = struct.unpack("B", peer_handshake[0:1])[0]
        pstr = peer_handshake[1:20].decode()

        if pstrlen != 19 or pstr != "BitTorrent protocol":
            print("Invalid protocol string.")
            return False

        info_hash = peer_handshake[28:48].hex()
        peer_id = peer_handshake[48:].decode("utf-8")

        if info_hash != expected_info_hash:
            print(
                f"Info hash mismatch. Expected: {expected_info_hash}, received: {info_hash}"
            )
            return False
        if peer_id != expected_peer_id:
            print(
                f"Peer ID mismatch. Expected: {expected_peer_id}, Received: {peer_id}"
            )
            return False

        return True

    def send_handshake(self, socket: socket, id: str, infohash: str):
        """Sends a handshake message to a peer.
        Args:
            socket (socket): The socket object connected to the peer.
            id (str): The peer ID.
            infohash (str): The infohash of the torrent.
        Returns:
            None
        """
        # Handshake
        pstrlen = struct.pack("B", 19)
        pstr = b"BitTorrent protocol"
        reserved = b"\x00" * 8
        infohash_as_bytes = bytes.fromhex(infohash)
        peer_id = id.encode("utf-8")
        handshake = pstrlen + pstr + reserved + infohash_as_bytes + peer_id

        # Send handshake
        socket.send(handshake)
        print(f"sent handshake: {handshake!r}")

    def receive_handshake(self, socket: socket, id: str, infohash: str):
        """Receives and validates a handshake message from a peer.
        Args:
            socket (socket): The socket object connected to the peer.
            id (str): The peer ID.
            infohash (str): The infohash of the torrent.
        Returns:
            True if the handshake is valid, False otherwise.
        """

        # Receive handshake
        peer_handshake = socket.recv(68)
        print(f"received handshake: {peer_handshake!r}")

        # validate handshake
        if self._validate_handshake(peer_handshake, infohash, id):
            return True
        else:
            return False
