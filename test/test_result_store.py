from __future__ import annotations

from backend.services.result_store import (
    ResultStore,
    ResultStoreError,
)


def main() -> None:
    print("=" * 60)
    print("TCO RESULT STORE TEST")
    print("=" * 60)

    store = ResultStore()

    print(f"Database: {store.db_path}")

    # ---------------------------------------------------------
    # 1. Empty result query should work
    # ---------------------------------------------------------
    results = store.query_results(
        limit=10,
    )

    print(f"All current results: {len(results)}")

    # ---------------------------------------------------------
    # 2. Pending result-email query should work
    # ---------------------------------------------------------
    pending = store.get_pending_result_emails(
        limit=10,
    )

    print(
        "Pending result emails:",
        len(pending),
    )

    # ---------------------------------------------------------
    # 3. Student history lookup
    # ---------------------------------------------------------
    student_results = store.get_student_results(
        student_name="student-that-does-not-exist",
        limit=10,
    )

    print(
        "Non-existing student results:",
        len(student_results),
    )

    assert student_results == []

    # ---------------------------------------------------------
    # 4. Validation test
    # ---------------------------------------------------------
    try:
        store.get_student_results(
            limit=10,
        )
    except ResultStoreError as exc:
        print(
            "Validation test passed:",
            str(exc),
        )
    else:
        raise AssertionError(
            "Expected ResultStoreError was not raised."
        )

    print("=" * 60)
    print("RESULT STORE TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()