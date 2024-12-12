import traceback
import struct
import time
import select
from socket import socket


class PeerCommunicator:
    def __init__(self, socket: socket, timeout=10, max_retries=5):
        self.socket = socket
        self.timeout = timeout
        self.max_retries = max_retries

    def _wait_for_data(self):
        """Wait for data with retries, returns True if data is ready."""
        for attempt in range(self.max_retries):
            try:
                ready, _, _ = select.select([self.socket], [], [], self.timeout)
                if ready:
                    return True
            except Exception as e:
                print(f"Wait for data error (attempt {attempt + 1}): {e}")
        raise TimeoutError("Multiple attempts to wait for data failed")

    def validate_handshake(self, peer_handshake, expected_info_hash, expected_peer_id):
        """Validate the handshake received from the peer."""
        if len(peer_handshake) != 68:
            print("Invalid handshake length. Received:", len(peer_handshake))
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
                f"Peer ID mismatch. Expected: {expected_peer_id}, received: {peer_id}"
            )
            return False

        return True

    def send_handshake(self, id: str, infohash: str):
        """Send a handshake to the peer."""
        pstrlen = struct.pack("B", 19)
        pstr = b"BitTorrent protocol"
        reserved = b"\x00" * 8
        infohash_as_bytes = bytes.fromhex(infohash)
        peer_id = id.encode("utf-8")
        handshake = pstrlen + pstr + reserved + infohash_as_bytes + peer_id
        self.socket.send(handshake)

    def receive_handshake(self):
        """Receive the handshake from the peer."""
        self._wait_for_data()
        return self.socket.recv(68)

    def _send_message(self, message_id, payload=None):
        """Helper function to send messages with or without payload."""
        length = len(payload) + 1 if payload else 1
        message = struct.pack(">I", length) + struct.pack(">B", message_id)
        if payload:
            message += payload
        self.socket.send(message)

    def _receive_message(self):
        """Helper function to receive messages."""
        self._wait_for_data()
        length_bytes = self.socket.recv(4)
        if not length_bytes:
            raise ConnectionError("Peer disconnected")
        length = struct.unpack(">I", length_bytes)[0]
        message_id = struct.unpack(">B", self.socket.recv(1))[0]
        try:
            payload = self.socket.recv(length - 1) if length > 1 else b""
        except Exception as e:
            print("[ERROR-_receive_message] error upon receiving message")
            # print(
            #     "[TRACEBACK] ",
            #     "".join(
            #         traceback.format_exception(
            #             etype=type(e), value=e, tb=e.__traceback__
            #         )
            #     ),
            # )
        return message_id, payload

    def send_choke(self):
        self._send_message(0)

    def send_unchoke(self):
        self._send_message(1)

    def send_interested(self):
        self._send_message(2)

    def send_not_interested(self):
        self._send_message(3)

    def send_have(self, piece_index):
        """Send a 'have' message indicating the peer has a piece."""
        self._send_message(4, struct.pack(">I", piece_index))

    def send_bitfield(self, bitfield):
        """Send the bitfield indicating the pieces the peer has."""
        self._send_message(5, bitfield)

    def send_request(self, piece_index):
        """Send a request for a specific piece from the peer."""
        # print(f"PeerCommunicator: Sending request for piece {piece_index}")
        self._send_message(6, struct.pack(">I", piece_index))

    def send_piece(self, piece_index, piece_data):
        """Send a piece of data, divided into blocks."""
        block_size = 4 * 1024
        divided_piece = [
            piece_data[i : i + block_size]
            for i in range(0, len(piece_data), block_size)
        ]

        try:
            for i, piece_block in enumerate(divided_piece):
                is_last_block = 1 if i == len(divided_piece) - 1 else 0
                payload = (
                    struct.pack(">I", piece_index)
                    + struct.pack(">B", is_last_block)
                    + piece_block
                )
                try:
                    self._send_message(7, payload)
                except (ConnectionResetError, BrokenPipeError):
                    print(f"Connection lost while sending piece {piece_index}")
                    raise

        except Exception as e:
            print(f"Error sending piece {piece_index}: {e}")
            raise

    def receive_message_type(self):
        """Receive and return the message type from the peer."""
        self._wait_for_data()
        message_id, _ = self._receive_message()
        return message_id

    def receive_have(self):
        """Receive a 'have' message and return the piece index."""
        self._wait_for_data()
        _, payload = self._receive_message()
        return struct.unpack(">I", payload)[0]

    def receive_bitfield(self) -> bytes:
        """Receive a bitfield from the peer."""
        self._wait_for_data()
        _, payload = self._receive_message()
        return payload

    def receive_request(self):
        """Receive a 'request' message and return the piece index requested."""
        self._wait_for_data()
        _, payload = self._receive_message()
        if not payload:
            return None
        piece_index = struct.unpack(">I", payload)[0]
        # print(f"PeerCommunicator: Received request for piece {piece_index}")
        return piece_index

    def receive_piece(self):
        """Receive a piece from the peer, handling multiple chunks."""
        piece_data = bytearray()
        piece_index = None

        while True:
            try:
                self._wait_for_data()
                _, payload = self._receive_message()

                if piece_index is None:
                    piece_index = struct.unpack(">I", payload[:4])[0]

                is_last_chunk = struct.unpack(">B", payload[4:5])[0]
                piece_data.extend(payload[5:])

                if is_last_chunk == 1:
                    break
                time.sleep(0.0015)
            except Exception as e:
                # print(f"Error receiving piece: {e}")
                raise

        # Join all chunks into the final piece data
        # print(f"Received piece {piece_index}")
        return piece_index, piece_data

    def receive_choke(self):
        """Receive a 'choke' message."""
        self._wait_for_data()
        return self.receive_message_type() == 0

    def receive_unchoke(self):
        """Receive an 'unchoke' message."""
        self._wait_for_data()
        return self.receive_message_type() == 1

    def receive_interested(self):
        """Receive an 'interested' message."""
        self._wait_for_data()
        return self.receive_message_type() == 2

    def receive_not_interested(self):
        """Receive a 'not interested' message."""
        self._wait_for_data()
        return self.receive_message_type() == 3
