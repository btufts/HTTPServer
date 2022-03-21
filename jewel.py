#!/usr/bin/env python3

from email.header import decode_header
import socket
import sys
import selectors
import types
import os
import time

from file_reader import FileReader


class Jewel:

    # For Decoding the Request Headers
    def decode_headers(self, data):
        header_end = data.find('\r\n\r\n')
        if header_end > -1:
            header_string = data[:header_end]
            lines = header_string.split('\r\n')

            request_fields = lines[0].split()
            headers = lines[1:]

            cook = ""
            for header in headers:
                header_fields = header.split(':')
                key_2 = header_fields[0].strip()
                val = header_fields[1].strip()
                if key_2 == "Cookie":
                    cook = val
        return request_fields, cook

    # If it is an error we don't need content type or content length?
    def build_headers(self, current_file, size, status):
        header = ""
        if status == 200:
            if os.path.isfile(current_file):
                kind = current_file.split(".")
                mime = "text"
                if(kind[2] == "png" or kind[2] == "jpeg" or kind[2] == "gif"):
                    mime = "image"
                header = "HTTP/1.1 200 OK\nContent-Length: " + \
                    str(size)+"\r\nContent-Type: "+mime+"/" + \
                    kind[2]+"\r\nServer: bt3qzd\r\nConnection: Closed\r\n"
            else:
                header = "HTTP/1.1 200 OK\r\nContent-Length: " + \
                    str(size)+"\r\nContent-Type: text/html\r\nServer: bt3qzd\r\nConnection: Closed\r\n"
        elif status == 400:
            header = "HTTP/1.1 400 Bad Request\r\nServer: bt3qzd\r\nConnection: Closed\r\n"
        elif status == 404:
            header = "HTTP/1.1 404 Not Found\r\nServer: bt3qzd\r\nConnection: Closed\r\n"
        elif status == 500:
            header = "HTTP/1.1 500 Internal Server Error\r\nServer: bt3qzd\r\nConnection: Closed\r\n"
        elif status == 501:
            header = "HTTP/1.1 501 Method Unimplemented\r\nServer: bt3qzd\r\nConnection: Closed\r\n"
        return header.encode()

    # Mulitple Connect Queue
    def accept(self, sock):
        conn, addr = sock.accept()
        print(f"[CONN] Connection from {addr[0]} on port {addr[1]}")
        conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr)
        events = selectors.EVENT_READ
        self.sel.register(conn, events, data=data)

    # Multiple Connect Handle
    def service(self, key, mask):
        client = key.fileobj
        key_data = key.data
        header = None
        content = None
        fin = False
        try:
            data = ''
            # Check if there was already a bit of request
            if self.data_store.get(key_data.addr[1]) != None:
                data = self.data_store.get(key_data.addr[1])
            try:
                # get more of the request
                data += client.recv(1024).decode()
                # check if request is finished
                self.decode_headers(data)
            except:
                # Will come here if request isn't finished and store what we have so far
                self.data_store[key_data.addr[1]] = data
                return
            fin = True
            request_fields = []
            cook = ""
            try:
                request_fields, cook = self.decode_headers(data)
                current_file = self.file_path + request_fields[1]
                size = self.file_reader.head(current_file, cook)
                if(request_fields[0] == "GET" or request_fields[0] == "HEAD"):
                    print(
                        f"[REQU] [{key_data.addr[0]}:{key_data.addr[1]}] {request_fields[0]} request for {request_fields[1]}")
                    if os.path.isfile(current_file):
                        content = self.file_reader.get(current_file, cook)
                    elif os.path.isdir(current_file):
                        content = self.file_reader.get(
                            request_fields[1], cook)
                    else:
                        content = None
                    if size == None and content != None:
                        # Possibly so I can return None from head for directory
                        # request but return the bit string from get so I will
                        # overwrite size with string bits here
                        size = len(content)
                    # If content is None then file and directory were not found
                    if content == None:
                        print(
                            f"[ERRO] [{key_data.addr[0]}:{key_data.addr[1]}] {request_fields[0]} request returned error 404")  # Not Found
                        # Build Headers
                        header = self.build_headers(current_file, size, 404)
                    else:  # OK
                        # Build Headers
                        header = self.build_headers(current_file, size, 200)
                        if(request_fields[0] == "HEAD"):
                            content = None
                else:
                    print(
                        f"[ERRO] [{key_data.addr[0]}:{key_data.addr[1]}] {request_fields[0]} request returned error 501")  # Method Unimplemented
                    # Build Headers
                    header = self.build_headers("", 0, 501)
            except:
                print(
                    f"[ERRO] [{key_data.addr[0]}:{key_data.addr[1]}] UNKNOWN request returned error 400")  # Bad Request
                # Build Headers
                header = self.build_headers("", 0, 400)
        except:
            print(
                f"[ERRO] [{key_data.addr[0]}:{key_data.addr[1]}] UNKNOWN request returned error 500")  # Internal Server Error
            # Build Headers
            header = self.build_headers("", 0, 500)
        finally:
            # Send Headers and Content and then Close
            if fin:
                if self.data_store.get(key_data.addr[1]) != None:
                    self.data_store.pop(key_data.addr[1])
                client.send(header+b'\r\n')
                if content != None:
                    client.send(content)
                self.sel.unregister(client)
                client.close()

    def __init__(self, port, file_path, file_reader):
        self.file_path = file_path
        self.file_reader = file_reader

        self.data_store = {}

        self.sel = selectors.DefaultSelector()
        host = "0.0.0.0"  # Not completely sure what this is supposed to be?

        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.bind((host, int(os.environ.get('PORT', 80))))
        lsock.listen()
        print(f"Listening on {(host, port)}")
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)

        try:
            while True:
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept(key.fileobj)
                    else:
                        self.service(key, mask)
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            self.sel.close()


# How do I host this on a public webserver??
if __name__ == "__main__":
    port = int(sys.argv[1])
    file_path = sys.argv[2]

    FR = FileReader()

    J = Jewel(port, file_path, FR)
