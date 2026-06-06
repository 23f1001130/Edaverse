from slowapi import Limiter
from slowapi.util import get_remote_address
from app.services.auth import get_request_user_id


def user_or_ip(request):
    user_id = get_request_user_id(request)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=user_or_ip)
