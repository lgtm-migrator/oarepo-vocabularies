from flask import current_app
from werkzeug.local import LocalProxy


def _ext_proxy(attr):
    return LocalProxy(lambda: getattr(current_app.extensions["mock_module_gen"], attr))


current_service = _ext_proxy("service")
"""Proxy to the instantiated vocabulary service."""


current_resource = _ext_proxy("resource")
"""Proxy to the instantiated vocabulary resource."""
