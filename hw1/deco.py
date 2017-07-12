#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import update_wrapper


def disable(func):
    '''
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:

    >>> memo = disable

    '''
    return func


def decorator(f):
    '''
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    '''
    def decor(func):
        def wrapper(*args, **kwargs):
            res = func(*args, **kwargs)
            if getattr(f, 'calls', None) is not None:
                update_wrapper(wrapper, f, assigned=('calls',))
            return res

        update_wrapper(wrapper, f)
        return wrapper
    return decor


def countcalls(func):
    '''Decorator that counts calls made to the function decorated.'''
    @decorator(func)
    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        return func(*args, **kwargs)
    wrapper.calls = 0
    return wrapper


def memo(func):
    '''
    Memoize a function so that it caches all return values for
    faster future lookups.
    '''
    @decorator(func)
    def wrapper(*args, **kwargs):
        wrapper.memo_args.append(args)
        res = func(*args, **kwargs)
        wrapper.memo_res.append(res)
        return res

    wrapper.memo_args = []
    wrapper.memo_res = []
    return wrapper


def n_ary(func):
    '''
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    '''
    def wrapper(*args):
        def call(a, b):
            # a - int
            # b - list
            if len(b) == 1:
                return func(a, b[0])
            else:
                return func(a, call(b[0], b[1:]))

        if len(args) == 1:
            res = args[0]
        else:
            # len(args) >= 2
            res = call(args[0], args[1:])
        return res

    return wrapper


fn_calls = 0


def trace(placeholder):
    '''Trace calls made to function decorated.

    @trace("____")
    def fib(n):
        ....

    >>> fib(3)
     --> fib(3)
    ____ --> fib(2)
    ________ --> fib(1)
    ________ <-- fib(1) == 1
    ________ --> fib(0)
    ________ <-- fib(0) == 1
    ____ <-- fib(2) == 2
    ____ --> fib(1)
    ____ <-- fib(1) == 1
     <-- fib(3) == 3

    '''
    def decor(func):
        @decorator(func)
        def wrapper(*args, **kwargs):
            global fn_calls
            ph = placeholder * fn_calls
            print "{} --> {}({})".format(ph, func.__name__, args[0])
            fn_calls += 1

            res = func(*args, **kwargs)

            fn_calls -= 1
            ph = placeholder * fn_calls
            print "{} <-- {}({}) == {}".format(ph, func.__name__, args[0], res)
            return res
        return wrapper
    return decor


@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


@countcalls
@trace("####")
@memo
def fib(n):
    """Fibonacci number"""
    return 1 if n <= 1 else fib(n-1) + fib(n-2)


def main():
    print foo(4, 3)
    print foo(4, 3, 2)
    print foo(4, 3)
    print "foo was called", foo.calls, "times"

    print bar(4, 3)
    print bar(4, 3, 2)
    print bar(4, 3, 2, 1)
    print "bar was called", bar.calls, "times"

    print fib.__doc__
    fib(3)
    print fib.calls, 'calls made'


if __name__ == '__main__':
    main()
