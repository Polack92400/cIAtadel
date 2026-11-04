import logging

from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """Uniform error envelope; never leak stack traces or internals.

    Unhandled exceptions return None here, so Django produces a generic 500
    (DEBUG is off outside local dev) and the details only go to the logs.
    """
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error")
        return None
    request = context.get("request")
    detail = response.data
    response.data = {
        "error": {
            "status": response.status_code,
            "detail": detail,
            "request_id": getattr(request, "request_id", None),
        }
    }
    return response


class ServiceUnavailable(APIException):
    status_code = 503
    default_detail = "Service temporarily unavailable."
    default_code = "service_unavailable"
