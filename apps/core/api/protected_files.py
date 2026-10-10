import mimetypes
import logging
from pathlib import Path

from django.http import HttpResponse
from botocore.exceptions import BotoCoreError, ClientError
from rest_framework.exceptions import NotFound, APIException
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class BinaryContentNegotiation(DefaultContentNegotiation):
    def select_renderer(self, request, renderers, format_suffix=None):
        # Successful responses are raw bytes, not JSON-rendered data. Accept:
        # image/* or application/pdf must not produce DRF's JSON-only 406.
        return renderers[0], renderers[0].media_type


class BinaryFileView(APIView):
    content_negotiation_class = BinaryContentNegotiation


class UploadStorageUnavailable(APIException):
    status_code = 503
    default_detail = 'File storage is temporarily unavailable. Please retry.'


def protected_file_response(field_file) -> HttpResponse:
    """
    Return a small protected verification document as a normal byte response.

    Verification uploads are capped at 10 MB, so reading the file once is a
    deliberate trade-off here: it is more reliable for authenticated browser
    XHR/fetch clients than a streaming FileResponse while keeping memory usage
    bounded.
    """
    if not field_file or not field_file.name:
        raise NotFound("Verification document was not found.")

    try:
        field_file.open("rb")
        payload = field_file.read()
    except FileNotFoundError as exc:
        raise NotFound('The uploaded file is missing from server storage. Ask the owner to upload it again.') from exc
    except ClientError as exc:
        if exc.response.get('Error', {}).get('Code') in ('404', 'NoSuchKey', 'NotFound'):
            raise NotFound('The uploaded file is missing from server storage. Ask the owner to upload it again.') from exc
        logger.warning('Upload object storage could not be read (%s).', type(exc).__name__)
        raise UploadStorageUnavailable() from exc
    except (OSError, BotoCoreError) as exc:
        logger.warning('Upload storage could not be read (%s).', type(exc).__name__)
        raise UploadStorageUnavailable() from exc
    finally:
        try:
            field_file.close()
        except Exception:
            pass

    if not payload:
        raise NotFound("Verification document is empty.")

    content_type = (
        mimetypes.guess_type(field_file.name)[0]
        or "application/octet-stream"
    )
    filename = Path(field_file.name).name.replace('"', "")

    response = HttpResponse(
        payload,
        content_type=content_type,
    )
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    response["Content-Length"] = str(len(payload))
    response["Cache-Control"] = "private, no-store, max-age=0"
    response["Pragma"] = "no-cache"
    response["X-Content-Type-Options"] = "nosniff"
    return response
