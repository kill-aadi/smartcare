"""Ten patients press "Book" at the same instant on a session with five seats.

Each thread has its own database connection, so this is real concurrency against PostgreSQL.
Without ``select_for_update()`` in ``book_session`` this test fails: threads read the same
"max token" and either collide on the unique constraint or overfill the session.
"""

import threading

import pytest
from django.db import connection

from bookings.services import SessionFull, book_session
from core.factories import PatientFactory, SessionFactory


@pytest.mark.django_db(transaction=True)
def test_concurrent_bookings_get_unique_sequential_tokens_and_respect_capacity():
    session = SessionFactory(capacity=5)
    patients = PatientFactory.create_batch(10)
    barrier = threading.Barrier(10)
    results, errors, unexpected = [], [], []

    def worker(patient):
        try:
            barrier.wait()
            results.append(book_session(patient, session.pk).token_no)
        except SessionFull:
            errors.append("full")
        except Exception as error:  # noqa: BLE001 - surfaced by the assertion below
            unexpected.append(repr(error))
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(p,)) for p in patients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert unexpected == []
    assert sorted(results) == [1, 2, 3, 4, 5]
    assert len(errors) == 5
    assert session.bookings.count() == 5
