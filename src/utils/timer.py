"""Timer decorator, using config bool to run or not."""

import inspect
import logging
import time
from functools import wraps

import pandas as pd

from config.logging import INDENT_SIZE, TIMER

logging.basicConfig(level=logging.INFO, format="%(message)s")


def _format_args_short(func, args, kwargs, arg_sep: str = ", ", max_len: int = 50):
    """Format function arguments as string (each separated by ', '),
    or return empty string if error.
    Example:
        myfunc(arg1, arg2, arg3)
        args=(a, b), kwargs={'arg3'=c}
        -> 'arg1=a, arg2=b, arg3=c'
    """
    formatted = []

    # Bind arg and kwarg arguments to param names
    try:
        bound = inspect.signature(func).bind(*args, **kwargs)
        bound.apply_defaults()
    except TypeError:
        return ""

    for arg_name, arg_value in bound.arguments.items():
        # If arg is df/series, or arg_name is 'self', deal with differently
        if arg_name == "self":
            # Don't print arg_value as its something like '<__main__.Class object at 0x000001D0...>'
            rep = ""
        elif isinstance(arg_value, pd.DataFrame):
            # Just print shape of df, not any of values in it
            rep = f"=DataFrame({arg_value.shape[0]}x{arg_value.shape[1]})"
        elif isinstance(arg_value, pd.Series):
            # Just print shape of df, not any of values in it
            rep = f"=Series({arg_value.shape[0]})"
        else:
            try:
                rep = f"={repr(arg_value)}"
            except Exception:
                rep = "=<error_generating_repr>"

        # Add rep or rep with elipses if too long
        if len(rep) <= max_len:
            formatted.append(f"{arg_name}{rep}")
        else:
            formatted.append(f"{arg_name}{rep[: max_len - 3] + '...'}")

    return arg_sep.join(formatted)


def timer(func):
    """Decorator to print time taken to run a function with its args."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        if TIMER:
            # Instead of .__name__ use .__qualname__
            # as this will include the class. part of the method/function
            func_name = func.__qualname__

            indent = ""
            if func_name[0] == "_":
                indent += " " * INDENT_SIZE

            func_str = f"{func_name}({_format_args_short(func, args, kwargs)}))"
            log_msg = f"{indent}{func_str} - {time.perf_counter() - start:.2f}s"
            logging.info(log_msg)
        return result

    return wrapper
