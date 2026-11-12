import functools

from .. import config, db
from ..db import t
from ..ui import ack


def subscribers_only(handler):
    """Callback buttons outlive subscriptions; check access again when one is pressed."""

    @functools.wraps(handler)
    async def wrapper(client, query):
        if query.message is None:
            await ack(query)
            return
        uid = query.from_user.id
        if not db.has_access(uid):
            await ack(query)
            await client.send_message(
                query.message.chat.id,
                t(uid, "no_subscription", purchase=config.PURCHASE_USERNAME, uid=uid))
            return
        await handler(client, query)

    return wrapper
