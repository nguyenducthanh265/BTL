"""One fragmented POST on a real loopback socket, with body-read instrumentation."""
import json
import select
import socket
import threading

from gameai.demo.server import DemoServer, Handler


class BodyReader:
    def __init__(self, stream):
        self.stream = stream
        self.read_bytes = 0

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def read(self, size=-1):
        data = self.stream.read(size)
        self.read_bytes += len(data)
        return data

    def read1(self, size=-1):
        data = self.stream.read1(size)
        self.read_bytes += len(data)
        return data


observations = []


class ObservedHandler(Handler):
    def setup(self):
        super().setup()
        self.rfile = BodyReader(self.rfile)

    def _send_json(self, status, data):
        if self.command == 'POST' and self.path == '/nope':
            observations.append({'status': status, 'declared_body_bytes': 2,
                                 'body_bytes_consumed_before_response': self.rfile.read_bytes})
        super()._send_json(status, data)


server = DemoServer(('127.0.0.1', 0), ObservedHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    with socket.create_connection(server.server_address, timeout=5) as client:
        client.sendall(b'POST /nope HTTP/1.0\r\nHost: localhost\r\nContent-Length: 2\r\n\r\n{')
        early = bool(select.select([client], [], [], 0.2)[0])
        result = {'response_before_final_body_byte': early}
        try:
            client.sendall(b'}')
            chunks = []
            while chunk := client.recv(8192):
                chunks.append(chunk)
            response = b''.join(chunks)
            result['response_status_line'] = response.split(b'\r\n', 1)[0].decode('ascii')
            result['response_json'] = json.loads(response.split(b'\r\n\r\n', 1)[1])
        except OSError as error:
            result['socket_error'] = str(error)
        result['handler_observations'] = observations
        print(json.dumps(result, ensure_ascii=False, indent=2))
finally:
    server.shutdown()
    server.server_close()
    thread.join()
