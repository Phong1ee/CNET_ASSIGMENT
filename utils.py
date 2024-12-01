import socket
import random


client_prefix = "-ST0001-"


def get_ip():
    """Get the IP address of the client machine.
    Returns:
        ip (str): The IP address of the client machine.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def get_id():
    """Generate a unique client ID.
    Returns:
        id (str): A unique client ID.
    """
    unique_component = str(random.randint(0, 999999999999)).zfill(12)
    id = f"{client_prefix}{unique_component}"
    return id


def decode_val(val):
    if isinstance(val, bytes):
        try:
            return bytes.decode(val, "utf-8", "strict")
        except UnicodeDecodeError:
            return val
    elif isinstance(val, list):
        return decode_list(val)
    elif isinstance(val, dict):
        return decode_dict(val)
    else:
        return val


def decode_list(list):
    return [decode_val(val) for val in list]


def decode_dict(dict):
    return {decode_val(k): decode_val(v) for k, v in dict.items()}
