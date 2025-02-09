import threading

_custom_context = threading.local()


def set_custom_context(key, value):
    if not hasattr(_custom_context, 'data'):
        _custom_context.data = {}
    _custom_context.data[key] = value


def get_custom_context(key, default=None):
    return getattr(_custom_context, 'data', {}).get(key, default)


def clear_custom_context():
    if hasattr(_custom_context, 'data'):
        del _custom_context.data
