#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Нужно реализовать простое HTTP API сервиса скоринга. Шаблон уже есть в api.py, тесты в test.py.
# API необычно тем, что польщователи дергают методы POST запросами. Чтобы получить результат
# пользователь отправляет в POST запросе валидный JSON определенного формата на локейшн /method

# Структура json-запроса:

# {"account": "<имя компании партнера>", "login": "<имя пользователя>", "method": "<имя метода>",
#  "token": "<аутентификационный токен>", "arguments": {<словарь с аргументами вызываемого метода>}}

# account - строка, опционально, может быть пустым
# login - строка, обязательно, может быть пустым
# method - строка, обязательно, может быть пустым
# token - строка, обязательно, может быть пустым
# arguments - словарь (объект в терминах json), обязательно, может быть пустым

# Валидация:
# запрос валиден, если валидны все поля по отдельности

# Структура ответа:
# {"code": <числовой код>, "response": {<ответ вызываемого метода>}}
# {"code": <числовой код>, "error": {<сообщение об ошибке>}}

# Аутентификация:
# смотри check_auth в шаблоне. В случае если не пройдена, нужно возвращать
# {"code": 403, "error": "Forbidden"}

# Метод online_score.
# Аргументы:
# phone - строка или число, длиной 11, начинается с 7, опционально, может быть пустым
# email - строка, в которой есть @, опционально, может быть пустым
# first_name - строка, опционально, может быть пустым
# last_name - строка, опционально, может быть пустым
# birthday - дата в формате DD.MM.YYYY, с которой прошло не больше 70 лет, опционально, может быть пустым
# gender - число 0, 1 или 2, опционально, может быть пустым

# Валидация аругементов:
# аргументы валидны, если валидны все поля по отдельности и если присутсвует хоть одна пара
# phone-email, first name-last name, gender-birthday с непустыми значениями.

# Контекст
# в словарь контекста должна прописываться запись  "has" - список полей,
# которые были не пустые для данного запроса

# Ответ:
# в ответ выдается произвольное число, которое больше или равно 0
# {"score": <число>}
# или если запрос пришел от валидного пользователя admin
# {"score": 42}
# или если произошла ошибка валидации
# {"code": 422, "error": "<сообщение о том какое поле невалидно>"}


# $ curl -X POST  -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95", "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "Стансилав", "last_name": "Ступников", "birthday": "01.01.1990", "gender": 1}}' http://127.0.0.1:8080/method/
# -> {"code": 200, "response": {"score": 5.0}}

# Метод clients_interests.
# Аргументы:
# client_ids - массив числе, обязательно, не пустое
# date - дата в формате DD.MM.YYYY, опционально, может быть пустым

# Валидация аругементов:
# аргументы валидны, если валидны все поля по отдельности.

# Контекст
# в словарь контекста должна прописываться запись  "nclients" - количество id'шников,
# переденанных в запрос


# Ответ:
# в ответ выдается словарь <id клиента>:<список интересов>. Список генерировать произвольно.
# {"client_id1": ["interest1", "interest2" ...], "client2": [...] ...}
# или если произошла ошибка валидации
# {"code": 422, "error": "<сообщение о том какое поле невалидно>"}

# $ curl -X POST  -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "admin", "method": "clients_interests", "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f24091386050205c324687a0", "arguments": {"client_ids": [1,2,3,4], "date": "20.07.2017"}}' http://127.0.0.1:8080/method/
# -> {"code": 200, "response": {"1": ["books", "hi-tech"], "2": ["pets", "tv"], "3": ["travel", "music"], "4": ["cinema", "geek"]}}

# Требование: в результате в git должно быть только два(2!) файлика: api.py, test.py.
# Deadline: следующее занятие

import abc
import json
import random
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler


SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class Field(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, required=True, nullable=False):
        self.required = required
        self.nullable = nullable
        self.name = None

    @abc.abstractmethod
    def validate_value(self, value):
        return True or False

    def parse_value(self, value):
        return value

    def validate_req_null(self, value):
        if self.required and value is None:
            return False
        if not self.nullable and not value:
            return False
        return True


class CharField(Field):
    def validate_value(self, value):
        if not self.required and not value:
            return True
        if isinstance(value, (str, unicode)):
            return True
        return False

    def parse_value(self, value):
        if isinstance(value, unicode) or not value:
            return value
        else:
            return value.decode('utf-8')


class ArgumentsField(Field):
    def validate_value(self, value):
        if not self.required and not value:
            return True
        if isinstance(value, dict):
            return True
        return False

    def parse_value(self, value):
        return value


class EmailField(CharField):
    def validate_value(self, value):
        if not self.required and not value:
            return True
        if not super(EmailField, self).validate_value(value):
            return False
        value = super(EmailField, self).parse_value(value)
        if value and '@' in value:
            return True
        return False
    

class PhoneField(Field):
    def validate_value(self, value):
        if not self.required and not value:
            return True
        if isinstance(value, (str, int, long)):
            value = str(value)
            if value == '':
                return True
            if len(value) == 11 and value[0] == '7' and value.isdigit():
                return True
        return False
        

class DateField(Field):
    # DD.MM.YYYY
    def validate_value(self, value):
        if not self.required and not value:
            return True
        if isinstance(value, basestring):
            try:
                datetime.datetime.strptime(str(value), '%d.%m.%Y')
                return True
            except ValueError:
                pass
        return False

    def parse_value(self, value):
        return datetime.datetime.strptime(str(value), '%d.%m.%Y') if value else None


class BirthDayField(DateField):
    def validate_value(self, value):
        if not self.required and not value:
            return True
        if super(BirthDayField, self).validate_value(value):
            date = self.parse_value(value)
            days = (datetime.datetime.today() - date).days
            years = days/float(365)
            if 0 <= years <= 70:
                return True
        return False


class GenderField(Field):
    def validate_value(self, value):
        if not self.required and not value:
            return True
        if value in GENDERS:
            return True
        return False


class ClientIDsField(Field):
    def validate_value(self, value):
        if not self.required and not value:
            return True
        if isinstance(value, list):
            if all(isinstance(c, int) for c in value):
                return True
        return False


class RequestMeta(type):
    def __new__(mcs, name, bases, dct):
        fields = []
        for k, v in dct.items():
            if isinstance(v, Field):
                v.name = k
                fields.append(v)
        cls = type.__new__(mcs, name, bases, dct)
        cls.fields = fields
        return cls


class Request(object):
    __metaclass__ = RequestMeta   # creates cls.fields = [field1, ...]

    def __init__(self, rawrequest, ctx):
        self.rawrequest = rawrequest
        self.ctx = ctx
        self.validation_done = False
        self.invalid_fields = []
        self.validate()

    def validate(self):
        for field in self.fields:
            value = self.rawrequest.get(field.name)
            if field.validate_req_null(value) and field.validate_value(value):
                parsed_value = field.parse_value(value)
                setattr(self, field.name, parsed_value)
            else:
                self.invalid_fields.append(field.name)
        self.validation_done = True

    def is_valid(self):
        if not self.validation_done:
            self.validate()
        return not self.invalid_fields

    def validation_errors(self):
        return ', '.join(self.invalid_fields)


class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN

    def check_auth(self):
        return check_auth(self)


class ClientsInterestsRequest(Request):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def getresult(self):
        if not self.is_valid():
            return self.validation_errors(), INVALID_REQUEST

        res = {cl: ['interest1', 'interest2'] for cl in self.client_ids}
        self.ctx['nclients'] = len(res)
        return res, OK


class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    _valid_pairs = (
        ('phone', 'email'),
        ('first_name', 'last_name'),
        ('gender', 'birthday')
    )

    def __init__(self, rawrequest, ctx, methodrequest):
        super(OnlineScoreRequest, self).__init__(rawrequest, ctx)
        self.methodrequest = methodrequest

    def validate(self):
        super(OnlineScoreRequest, self).validate()
        if not self.invalid_fields:
            self.ctx['has'] = []
            for field in self.__class__.fields:
                value = self.rawrequest.get(field.name)
                if not field.validate_req_null(value):
                    self.invalid_fields.append(field.name)
                if value is not None:
                    self.ctx['has'].append(field.name)

            has_valid_pair = False
            for pair in self._valid_pairs:
                value1 = getattr(self, pair[0])
                value2 = getattr(self, pair[1])
                if value1 is not None and value2 is not None:
                    has_valid_pair = True
            if not has_valid_pair:
                self.invalid_fields.append(str(self._valid_pairs[0]))
            self.validation_done = True

    def getresult(self):
        if not self.is_valid():
            return self.validation_errors(), INVALID_REQUEST
        if self.methodrequest.is_admin:
            return {'score': 42}, OK
        else:
            return {'score': random.randrange(0, 100)}, OK


def check_auth(request):
    if request.login == ADMIN_LOGIN:
        digest = hashlib.sha512(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512(request.account + request.login + SALT).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx):
    req = MethodRequest(request['body'], ctx)

    if not req.is_valid():
        return req.validation_errors(), INVALID_REQUEST
    if not req.check_auth():
        return None, FORBIDDEN

    if req.method == 'online_score':
        score_req = OnlineScoreRequest(request['body']['arguments'], ctx, req)
        resp, code = score_req.getresult()
        return resp, code
    elif req.method == 'clients_interests':
        clients_req = ClientsInterestsRequest(request['body']['arguments'], ctx)
        resp, code = clients_req.getresult()
        return resp, code

    return None, BAD_REQUEST


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string, 'utf8')
        except Exception as e:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context)
                except Exception, e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r))
        return

if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
