from rest_framework.exceptions import APIException


class Conflict(APIException):
    status_code = 409
    default_detail = "The request conflicts with the current resource state."
    default_code = "conflict"


class Gone(APIException):
    status_code = 410
    default_detail = "The requested resource is no longer available."
    default_code = "gone"


class UnprocessableEntity(APIException):
    status_code = 422
    default_detail = "The request could not be processed."
    default_code = "unprocessable_entity"


class Locked(APIException):
    status_code = 423
    default_detail = "The resource is locked."
    default_code = "locked"


class TooManyRequests(APIException):
    status_code = 429
    default_detail = "Too many requests."
    default_code = "too_many_requests"


class DeliveryUnavailable(APIException):
    status_code = 503
    default_detail = "Verification delivery is unavailable. Please contact support."
    default_code = "delivery_unavailable"
