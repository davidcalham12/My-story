"""G2 - no more than the capacity is ever in flight at once."""

import threading

import pytest

from backend.commons.context.semaphore import ContextCeilingExceeded, TokenSemaphore

CAPACITY = 100_000


def test_five_critics_never_exceed_capacity():
    """The case the ceiling exists for.

    Five calls of 30,000 satisfy any PER-CALL limit and put 150,000 in the air.
    Under the semaphore they must total no more than the capacity at any instant,
    and all five must still finish - waiting is the price, not a failure.
    """
    sem = TokenSemaphore(CAPACITY)
    observations: list[tuple[int, int]] = []
    lock = threading.Lock()
    done: list[int] = []

    def critic(n: int) -> None:
        with sem.hold(30_000) as reservation:
            with lock:
                observations.append(
                    (reservation.in_flight_at_dispatch, reservation.tokens)
                )
            # Work happens here; the reservation is held for its duration.
            for _ in range(2000):
                pass
        with lock:
            done.append(n)

    threads = [threading.Thread(target=critic, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert len(done) == 5, "all five critics must complete"
    for in_flight, reserved in observations:
        assert in_flight + reserved <= CAPACITY
    assert sem.in_flight == 0, "every reservation released"


def test_oversized_reservation_raises_before_waiting():
    """Waiting for capacity that can never exist is a deadlock, not patience."""
    sem = TokenSemaphore(CAPACITY)
    with pytest.raises(ContextCeilingExceeded) as exc:
        sem.acquire(CAPACITY + 1)
    assert "run error" in str(exc.value)
    assert sem.in_flight == 0


def test_waiting_is_recorded_not_punished():
    """A call that waited produces the same result; the wait is measured."""
    sem = TokenSemaphore(1000)
    first = sem.acquire(900)
    waited: list[int] = []

    def second() -> None:
        with sem.hold(900) as reservation:
            waited.append(reservation.wait_ms)

    t = threading.Thread(target=second)
    t.start()
    import time

    time.sleep(0.05)
    sem.release(first)
    t.join(timeout=5)

    assert waited, "the second call completed rather than failing"
    assert waited[0] >= 10, "and its wait was recorded"


def test_release_on_exception():
    sem = TokenSemaphore(1000)
    with pytest.raises(RuntimeError):
        with sem.hold(500):
            raise RuntimeError("boom")
    assert sem.in_flight == 0
