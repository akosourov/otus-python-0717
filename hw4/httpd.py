# coding: utf-8

import argparse
import os
import socket
import threading
import urllib
import multiprocessing
from email.utils import formatdate

DEBUG = True

DOCUMENT_ROOT = os.getcwd()

GET = "GET"
HEAD = "HEAD"


class HTTPRequest(object):
    def __init__(self, request_msg):
        self.request_msg = request_msg
        self.method_type = None
        self.uri = None
        self.query_str = None
        self.parse_request_msg()

    def parse_request_msg(self):
        request = self.request_msg.split("\r\n")
        self.method_type, uri, _ = request[0].split(" ")
        uri = urllib.unquote(uri)
        query_index = uri.find('?')
        if query_index > 0:
            self.uri = uri[:query_index]
        else:
            self.uri = uri


class HTTPResponse(object):
    STATUS_TEXT = {
        200: "OK",
        400: "Bad request",
        404: "Not found",
        403: "Forbidden",
        405: "Method not allowed"
    }

    def __init__(self, status, content_type=None, body_msg=None, only_headers=False):
        self.status = status
        self.content_type = content_type
        self.body_msg = body_msg
        self.only_headers = only_headers
        self.headers = {}
        self.set_common_headers()

    def set_common_headers(self):
        self.headers["Date"] = formatdate(usegmt=True)
        self.headers["Server"] = "otus-simple-server"
        if self.content_type:
            self.headers["Content-Type"] = self.content_type
        else:
            self.headers["Content-Type"] = "text/html"
        if self.body_msg:
            self.headers["Content-Length"] = len(self.body_msg)

    def get_response_msg(self):
        msg = "HTTP/1.1 {} {}\r\n".format(self.status, self.STATUS_TEXT[self.status])
        for name, text in self.headers.items():
            msg += "{}: {}\r\n".format(name, text)
        msg += "\r\n"
        if self.body_msg and not self.only_headers:
            msg += "{}\r\n".format(self.body_msg)
        return msg


def handle_client(s):
    chunks = []
    method_type = None
    uri = None
    while True:
        chunk = s.recv(1024)
        chunks.append(chunk)
        if chunk.endswith("\r\n\r\n") or not chunk:
            break

    request_msg = "".join(chunks)

    debug_print("Current process: {}, thread: {}".format(os.getpid(), threading.currentThread().ident))
    debug_print("<-")
    debug_print("".join(request_msg))

    try:
        request = HTTPRequest(request_msg)
    except Exception as exc:
        debug_print(exc)
        resp_msg = HTTPResponse(400).get_response_msg()
        debug_print("->")
        debug_print(resp_msg)
        s.send(resp_msg)
        s.close()
        return

    method_type = request.method_type
    uri = request.uri
    if method_type in (GET, HEAD):
        if uri and uri.startswith('/'):
            if uri == '/':
                # index.html
                body = "<ul>"
                filenames = []
                for name in os.listdir("."):
                    filenames.append(name)
                body_msg = "<ul><li>" + "</li><li>".join(filenames) + "</li><ul>"
                resp_msg = HTTPResponse(200, body_msg=body_msg).get_response_msg()
            elif uri.endswith('/'):
                # directory
                index_name = os.path.join(DOCUMENT_ROOT, uri[1:len(uri)-1], "index.html")
                if os.path.isfile(index_name):
                    # index.html exists
                    body_msg = read_file(index_name)
                    content_type = get_content_type(index_name)
                    if method_type == GET:
                        only_headers = False
                    else:
                        only_headers = True
                    resp_msg = HTTPResponse(200, body_msg=body_msg,
                                            only_headers=only_headers,
                                            content_type=content_type).get_response_msg()
                else:
                    resp_msg = HTTPResponse(403).get_response_msg()
            else:
                # file
                filename = os.path.join(DOCUMENT_ROOT, uri[1:])
                if os.path.isfile(filename):
                    body_msg = read_file(filename)
                    content_type = get_content_type(filename)
                    if method_type == GET:
                        only_headers = False
                    else:
                        only_headers = True
                    resp_msg = HTTPResponse(200, body_msg=body_msg,
                                            only_headers=only_headers,
                                            content_type=content_type).get_response_msg()
                else:
                    resp_msg = HTTPResponse(404).get_response_msg()
        else:
            # bad request
            resp_msg = HTTPResponse(405).get_response_msg()
    else:
        resp_msg = HTTPResponse(405).get_response_msg()

    debug_print("->")
    debug_print(resp_msg)
    s.send(resp_msg)
    s.close()


def read_file(filename):
    file_data = []
    with open(filename, 'rb') as f:
        for line in f:
            file_data.append(line)
    return "".join(file_data)


def get_content_type(filename):
    content_type = "text/plain"
    if filename.endswith(".html"):
        content_type = "text/html"
    elif filename.endswith(".css"):
        content_type = "text/css"
    elif filename.endswith(".js"):
        content_type = "text/javascript"
    elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
        content_type = "image/jpeg"
    elif filename.endswith("png"):
        content_type = "image/png"
    elif filename.endswith(".gif"):
        content_type = "image/gif"
    elif filename.endswith(".swf"):
        content_type = "application/x-shockwave-flash"
    return content_type


def debug_print(msg):
    if DEBUG:
        print msg


def start_server():
    debug_print("Mainloop   Current process: {}, thread: {}".format(os.getpid(), threading.currentThread().ident))
    serv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # serv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serv_socket.bind(("", 80))
    serv_socket.listen(5)
    debug_print("Server started in folder {}".format(DOCUMENT_ROOT))
    while True:
        cl_socket, addr = serv_socket.accept()
        # cl_socket.settimeout(5)
        debug_print("Connection accepted {}\n".format(str(addr)))
        t = threading.Thread(target=handle_client, args=(cl_socket,))
        t.start()
        debug_print(t.isAlive())
        # handle_client(cl_socket)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple threaded web server")
    parser.add_argument('-w', type=int, help="Amount of workers")
    parser.add_argument('-r', type=str, help="Document root for web server")
    args = parser.parse_args()
    if args.w:
        workers = args.w
    else:
        workers = 1
    if args.r:
        DOCUMENT_ROOT = args.r
    debug_print("Master " + str(os.getpid()))
    # Запускаем необходимое инстансов сервера
    # for _ in range(workers):
    #     p = multiprocessing.Process(target=start_server())
    #     p.start()
    start_server()
