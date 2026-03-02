import socket
import threading
import paramiko
import logging
import os

# ─── CONFIG ───────────────────────────────────────────
HOST        = "::"       # listen on all IPv6 interfaces
PORT        = 2222       # tunnel server port
USERNAME    = "tunnel"   # client must use this username
PASSWORD    = "Enter_Your_Pass_Here"  # change this!
BANNER      = "NEOX Tunnel Server"
# ──────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("server")

# ── Generate or load host key ──────────────────────────
KEY_FILE = "server_host.key"

def load_host_key():
    if not os.path.exists(KEY_FILE):
        log.info("Generating new RSA host key...")
        k = paramiko.RSAKey.generate(2048)
        k.write_private_key_file(KEY_FILE)
        log.info(f"Host key saved to {KEY_FILE}")
    return paramiko.RSAKey(filename=KEY_FILE)

# ── SSH Server Interface ───────────────────────────────
class TunnelServerInterface(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        if username == USERNAME and password == PASSWORD:
            log.info(f"[+] Auth success: {username}")
            return paramiko.AUTH_SUCCESSFUL
        log.warning(f"[-] Auth failed: {username}")
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_direct_tcpip_request(self, chanid, origin, destination):
        return paramiko.OPEN_SUCCEEDED

    def check_port_forward_request(self, address, port):
        log.info(f"[+] Port forward requested: {address}:{port}")
        return port

    def cancel_port_forward_request(self, address, port):
        log.info(f"[-] Port forward cancelled: {address}:{port}")

# ── Forward data between two sockets ──────────────────
def forward(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try: src.close()
        except: pass
        try: dst.close()
        except: pass

# ── Handle each SSH client connection ─────────────────
def handle_client(sock, addr, host_key):
    log.info(f"[+] Connection from {addr}")
    transport = None
    try:
        transport = paramiko.Transport(sock)
        transport.add_server_key(host_key)
        transport.set_gss_host(socket.getfqdn(""))
        transport.local_version = f"SSH-2.0-{BANNER}"

        server = TunnelServerInterface()
        transport.start_server(server=server)

        log.info(f"[*] Client {addr} authenticated, tunnel active")

        # Keep transport alive
        while transport.is_active():
            threading.Event().wait(1)

    except Exception as e:
        log.error(f"Client error: {e}")
    finally:
        if transport:
            transport.close()
        sock.close()
        log.info(f"[-] Connection closed: {addr}")

# ── Main ───────────────────────────────────────────────
def main():
    host_key = load_host_key()

    srv = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    except Exception:
        pass
    srv.bind((HOST, PORT, 0, 0))  # IPv6 bind needs 4-tuple
    srv.listen(10)

    log.info(f"[*] NEOX Tunnel Server listening on port {PORT}")
    log.info(f"[*] Username: {USERNAME}")
    log.info(f"[*] Press Ctrl+C to stop\n")

    try:
        while True:
            sock, addr = srv.accept()
            t = threading.Thread(target=handle_client, args=(sock, addr, host_key), daemon=True)
            t.start()
    except KeyboardInterrupt:
        log.info("\n[*] Server stopped")
    finally:
        srv.close()

if __name__ == "__main__":
    main()
