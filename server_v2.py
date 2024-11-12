import socket
from threading import Thread
from aiohttp import web
import bencodepy


class Tracker:
    def __init__(self):
        # List of swarms (dict):
        #    {info_hash: str,
        #     peers[]: {seeder, peer_id, ip, port}})
        self.swarms = []

    def _update_swarms(self, info_hash, peer_id, ip, port):
        """Update the swarm with the new peer information.

        Args:
            info_hash (str): Info hash of the torrent
            peer_id (str): Peer ID
            ip (str): IP address of the peer
            port (int): Port number of the peer

        Returns:
            None
        """
        for swarm in self.swarms:
            if swarm["info_hash"] == info_hash:
                swarm["peers"].append(
                    {"seeder": 0, "peer_id": peer_id, "ip": ip, "port": port}
                )
                return

        self.swarms.append(
            {
                "info_hash": info_hash,
                "peers": [{"seeder": 0, "peer_id": peer_id, "ip": ip, "port": port}],
            }
        )

    def _prepare_response_params(self, info_hash, error_flag, numwant, peer_id):
        """Prepare the response parameters for the tracker.

        Args:
            info_hash (str): Info hash of the torrent
            error_flag (int): Error flag
            numwant (int): number of peer wanted by client in GET request
            peer_id (int): peer id of the client

        Returns:
            dict: Response parameters
        """

        if error_flag:
            print("error_flag in _prepare_response_params")
            return bencodepy.encode({"failure reason": "Missing required parameters"})

        response = {"interval": 1800, "complete": 0, "incomplete": 0, "peers": []}

        for swarm in self.swarms:
            if swarm["info_hash"] == info_hash:
                count = 0
                for peer in swarm["peers"]:
                    if peer["peer_id"] == peer_id:
                        continue
                    response["peers"].append(peer)
                    if peer["seeder"]:
                        response["complete"] += 1
                    else:
                        response["incomplete"] += 1
                    count += 1
                    if count == numwant:
                        break
        print(response)
        return bencodepy.encode(response)

    async def announce(self, request):
        """Handle the announce request from the client.

        Args:
            request: Request object

        Returns:
            web.Response: Response object
        """
        error_flag = 0

        # Extract necessary parameters from the query
        info_hash = request.query.get("info_hash")
        peer_id = request.query.get("peer_id")
        ip = request.query.get("ip")
        port = request.query.get("port")
        numwant = request.query.get("numwant")
        print(
            f"Extracted keys from client {peer_id}: {info_hash}, {peer_id}, {ip}, {port}, {numwant}"
        )

        if not (info_hash and peer_id and port):
            print(f"Missing required parameters from client {peer_id}")
            error_flag = 1

        response = self._prepare_response_params(info_hash, error_flag, numwant, peer_id)

        # Update the swarms
        if error_flag == 0:
            print(f"Updating swarms for client {peer_id}")
            self._update_swarms(info_hash, peer_id, ip, port)

        print(f"Responding to client {peer_id}")
        return web.Response(body=response, content_type="text/plain")


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


if __name__ == "__main__":
    tracker = Tracker()

    app = web.Application()
    app.router.add_get("/announce", tracker.announce)
    hostip = get_host_default_interface_ip()
    port = 22236
    print("Listening on: {}:{}".format(hostip, port))
    web.run_app(app, host=hostip, port=port)
