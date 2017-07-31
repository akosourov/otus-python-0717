# coding: utf-8

import os
import socket
from email.utils import formatdate

GET = "GET"
HEAD = "HEAD"


class HTTPResponse(object):
    STATUS_TEXT = {
        200: "OK",
        404: "Not found",
        403: "Forbidden",
        405: "Method not allowed"
    }

    def __init__(self, status, content_type=None, body_msg=None):
        self.status = status
        self.content_type = content_type
        self.headers = {}
        self.set_common_headers()
        self.body_msg = body_msg
    
    def set_common_headers(self):
        self.headers["Date"] = formatdate(usegmt=True)
        self.headers["Server"] = "otus-simple-server"
        if not self.content_type:
            self.headers["Content-Type"] = "text/html; charset=utf-8"

    def get_response_msg(self):
        msg = "HTTP/1.1 {} {}\r\n".format(self.status, self.STATUS_TEXT[self.status])
        for name, text in self.headers.items():
            msg += "{}: {}\r\n".format(name, text)
        if self.body_msg:
            msg += "\r\n{}".format(self.body_msg)
        return msg


def handle_client(s):
    f = s.makefile()
    chunks = []
    method_type = None
    uri = None
    while True:
        chunk = f.readline()
        if not method_type:
            if chunk.startswith(GET):
                method_type = GET
                uri = chunk.split(" ")[1]
            elif chunk.startswith(HEAD):
                method_type = HEAD
                uri = chunk.split(" ")[1]
        chunks.append(chunk)
        if chunk == '\r\n' or chunk == '\n':
            # print "End of msg"
            break
    print "".join(chunks)

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
                s.send(resp_msg)
            elif uri.endswith('/'):
                # directory
                index_name = os.path.join(uri[1:len(uri)-1], "index.html")
                if os.path.isfile(index_name):
                    pass
                else:
                    resp_msg = HTTPResponse(403).get_response_msg()
                    s.send(resp_msg)
            else:
                # file
                filename = uri[1:]
                if os.path.isfile(filename):
                    print "SEND FILE"
                    file_data = []
                    with open(filename, 'r') as f:
                        for line in f:
                            file_data.append(line)
                    file_data_msg = "".join(file_data)
                    print file_data_msg
                    resp_msg = HTTPResponse(200, body_msg=file_data_msg).get_response_msg()
                    s.send(resp_msg)
        else:
            # bad request
            resp_msg = HTTPResponse(405).get_response_msg()
            s.send(resp_msg)
    else:
        resp_msg = HTTPResponse(405).get_response_msg()
        s.send(resp_msg)
    s.close()
    print "closed socket"


def start_server():
    serv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serv_socket.bind(("", 80))
    serv_socket.listen(5)
    print 'Server started...'
    while True:
        cl_socket, addr = serv_socket.accept()
        cl_socket.settimeout(5)
        print "Connection accepted", addr
        handle_client(cl_socket)


if __name__ == "__main__":
    start_server()
