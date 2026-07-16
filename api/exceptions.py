from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return Response(
            {'detail': 'An unexpected error occurred. Please try again later.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if response.status_code == status.HTTP_400_BAD_REQUEST:
        data = response.data
        if isinstance(data, dict) and 'detail' not in data:
            return Response({'errors': data}, status=response.status_code)

    return response
