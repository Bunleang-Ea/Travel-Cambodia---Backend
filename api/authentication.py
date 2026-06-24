from rest_framework.authentication import TokenAuthentication, get_authorization_header
from rest_framework.authtoken.models import Token
from rest_framework import exceptions
from django.utils.translation import gettext_lazy as _


class BearerOrTokenAuthentication(TokenAuthentication):
    """Compatibility authentication that accepts both 'Token <key>' and 'Bearer <key>'.

    This keeps the existing Token model but accepts the more common Bearer header
    used by many frontends.
    """

    keyword_variants = (b"token", b"bearer")

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth:
            return None

        if len(auth) == 1:
            # Invalid header - no credentials
            return None

        if auth[0].lower() not in self.keyword_variants:
            return None

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Token string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, key):
        try:
            token = Token.objects.select_related('user').get(key=key)
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid token.'))

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

        return (token.user, token)
