from flask.helpers import make_response


def success_response_json(response_content):
    return make_response({"status": "OK", "content": response_content}, 200)


def error_response_json(message: str, code: int = 500):
    return make_response({"status": "ERROR", "message": message}, code)


class dotdict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def format_currency(fval: str):
    return (
        "€ {:_.2f}".format(float(fval))
        .replace(".", ",")
        .replace("_", ".")
        .replace(",00", ",-")
    )
