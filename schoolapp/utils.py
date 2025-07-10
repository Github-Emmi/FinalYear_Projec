from django.conf import settings
from agora_token_builder import RtcTokenBuilder
from datetime import datetime, timedelta
from datetime import datetime, timedelta

TOKEN_EXPIRATION_SECONDS = 3600 * 24  # 24 hours

def build_agora_token(user, channel_name):
    """
    Builds Agora RTC token for a user on a given channel.
    """
    uid = user.id
    role = 1  # 1 = publisher
    expire_ts = int((datetime.now(datetime.timezone.utc) + timedelta(seconds=TOKEN_EXPIRATION_SECONDS)).timestamp())

    token = RtcTokenBuilder.buildTokenWithUid(
        settings.AGORA_APP_ID,
        settings.AGORA_APP_CERTIFICATE,
        channel_name,
        uid,
        role,
        expire_ts
    )
    return token, uid