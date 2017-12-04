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
# client_ids - массив чисел, обязательно, не пустое
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
    empty_values = (None,)

    def __init__(self, required=True, nullable=False):
        self.required = required
        self.nullable = nullable
        self.name = None

    @abc.abstractmethod
    def parse_validate(self, value):
        """Try parse and then validate or raise ValueError"""


class CharField(Field):
    empty_values = ('', None)

    def parse_validate(self, value):
        if not isinstance(value, (str, unicode)):
            raise ValueError("CharField must be a string")
        return value


class ArgumentsField(Field):
    empty_values = ({}, None)

    def parse_validate(self, value):
        if not isinstance(value, dict):
            raise ValueError("ArgumentsField must be a dict")
        return value


class EmailField(CharField):
    def parse_validate(self, value):
        value = super(EmailField, self).parse_validate(value)
        if '@' not in value:
            raise ValueError("EmailField must be a valid email, need '@'")
        return value
    

class PhoneField(Field):
    empty_values = ('', 0, None)

    def parse_validate(self, value):
        if not isinstance(value, (str, unicode, int, long)):
            raise ValueError("PhoneField must be a string or integer")
        value = str(value)
        if not (len(value) == 11 and value.startswith('7') and value.isdigit()):
            raise ValueError("PhoneField must contains 7 with 11 character length")
        return value
        

class DateField(Field):
    empty_values = ('', None)

    def parse_validate(self, value):
        if not isinstance(value, (str, unicode)):
            raise ValueError("DateField must be a string")
        value = str(value)
        try:
            dt = datetime.datetime.strptime(value, '%d.%m.%Y')
        except ValueError:
            raise ValueError("DateField does not match %d.%m.%Y")
        return dt.date()


class BirthDayField(DateField):
    def parse_validate(self, value):
        date = super(BirthDayField, self).parse_validate(value)
        today = datetime.date.today()
        if date > today or today.year - date.year > 70:
            raise ValueError("BirthDayField must be in [today-70 ... today]")
        return date


class GenderField(Field):
    def parse_validate(self, value):
        gender = GENDERS.get(value)
        if not gender:
            raise ValueError("GenderField must be %s" % GENDERS.keys())
        return gender


class ClientIDsField(Field):
    empty_values = ([], None)

    def parse_validate(self, value):
        if not (isinstance(value, list) and all(isinstance(c, int) for c in value)):
            raise ValueError("ClientIDsField must be a list of integers")
        return value


class RequestMeta(type):
    def __new__(mcs, name, bases, attr_dict):
        fields = []
        for attr, v in attr_dict.items():
            if isinstance(v, Field):
                v.name = attr
                fields.append(v)
        cls = type.__new__(mcs, name, bases, attr_dict)
        cls.fields = fields
        return cls


class Request(object):
    __metaclass__ = RequestMeta   # creates cls.fields = [field1, ...]

    def __init__(self, request):
        self.request = request
        self.clean_done = False
        self.invalid_fieldnames = []

    def clean(self):
        """Parse fields and set values to instance:
        e.x. self.fieldname = parsed_value"""
        for field in self.fields:
            field_name = field.name

            # empty fields
            if field_name not in self.request:
                if field.required:
                    self.invalid_fieldnames.append(field_name)
                setattr(self, field_name, None)
                continue
            value = self.request[field_name]
            if value in field.empty_values:
                if not field.nullable:
                    self.invalid_fieldnames.append(field_name)
                setattr(self, field_name, value)
                continue

            # not empty fields
            try:
                parsed_value = field.parse_validate(value)
            except ValueError:
                self.invalid_fieldnames.append(field_name)
                continue
            setattr(self, field_name, parsed_value)
        self.clean_done = True

    def is_valid(self):
        if not self.clean_done:
            self.clean()
        return not self.invalid_fieldnames

    def errors_text(self):
        return ', '.join(self.invalid_fieldnames)

    @property
    def not_empty_fieldnames(self):
        if not self.clean_done:
            self.clean()
        not_empty = []
        for field in self.fields:
            value = getattr(self, field.name)
            if value not in field.empty_values:
                not_empty.append(field.name)
        return not_empty


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

    def clean(self):
        super(OnlineScoreRequest, self).clean()
        if not self.invalid_fieldnames:
            valid_pair_exists = False   # not empty pair
            for fieldname1, fieldname2 in self._valid_pairs:
                value1 = getattr(self, fieldname1)
                value2 = getattr(self, fieldname2)
                if value1 and value2:
                    valid_pair_exists = True
                    break
            if not valid_pair_exists:
                self.invalid_fieldnames.append(str(self._valid_pairs[0]))
            self.clean_done = True


def check_auth(request):
    if request.login == ADMIN_LOGIN:
        digest = hashlib.sha512(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512(request.account + request.login + SALT).hexdigest()
    if digest == request.token:
        return True
    return False


class MethodHandler(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, method_request, ctx):
        assert isinstance(method_request, MethodRequest)
        assert isinstance(ctx, dict)
        assert issubclass(self.cls_request, Request)

        self.method_request = method_request
        self.ctx = ctx
        self.request = self.cls_request(method_request.arguments)

    def handle(self):
        if not self.request.is_valid():
            return self.request.errors_text(), INVALID_REQUEST
        return self.process_request()

    @abc.abstractproperty
    def cls_request(self):
        """Get request class"""

    @abc.abstractmethod
    def process_request(self):
        """Process request and return response and status code"""


class MethodHandlerOnlineScore(MethodHandler):
    cls_request = OnlineScoreRequest

    def process_request(self):
        self.ctx['has'] = self.request.not_empty_fieldnames
        if self.method_request.is_admin:
            return {'score': 42}, OK
        else:
            return {'score': random.randrange(0, 100)}, OK


class MethodHandlerClientsInterests(MethodHandler):
    cls_request = ClientsInterestsRequest

    def process_request(self):
        interests = ['coding', 'sport', 'tv', 'books', 'education']

        res = {c: random.sample(interests, random.randint(1, len(interests)))
               for c in self.request.client_ids}
        self.ctx['nclients'] = len(self.request.client_ids)
        return res, OK


def method_handler(request_raw, ctx):
    request = MethodRequest(request_raw['body'])

    if not request.is_valid():
        return request.errors_text(), INVALID_REQUEST
    if not request.check_auth():
        return None, FORBIDDEN

    api_handler_class = {
        'online_score': MethodHandlerOnlineScore,
        'clients_interests': MethodHandlerClientsInterests
    }

    if request.method not in api_handler_class:
        return None, NOT_FOUND

    return api_handler_class[request.method](request, ctx).handle()


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
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
