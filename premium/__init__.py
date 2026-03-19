"""Premium tier detection stub.

Placeholder module for future tier detection logic. Currently returns "free"
for all users. Will be extended when payment integration is added.
"""


def get_tier(user_id: str) -> str:
    """Return the premium tier for a given user.

    Args:
        user_id: The user identifier to look up.

    Returns:
        The tier string. Currently always "free".
    """
    return "free"
