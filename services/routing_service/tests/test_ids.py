import time
from services.routing_service.ids import is_duplicate, is_rate_limited

def test_duplicate_detection():
    msg_id = "abc123"

    assert is_duplicate(msg_id) == False   # first time → not duplicate
    assert is_duplicate(msg_id) == True    # second time → duplicate


def test_rate_limiting():
    peer = "peer-x"

    # flood quickly to trigger rate limit
    limited = False
    for _ in range(50):
        if is_rate_limited(peer):
            limited = True
            break
    assert limited == True
