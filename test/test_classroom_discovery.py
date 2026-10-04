from __future__ import annotations

from backend.services.classroom_discovery import (
    ClassroomDiscoveryError,
    ClassroomMaterialDiscoveryService,
)


COURSE_ID = "871538502094"

QUERIES = [
    "Booth Algorithm",
    "Booth multiplication",
    "Computer Organization Booth Algorithm",
]


def print_result(
    result: dict,
) -> None:
    print()
    print(
        f"Title: {result.get('title', '')}"
    )

    print(
        f"Material ID: "
        f"{result.get('material_id', '')}"
    )

    print(
        f"Score: "
        f"{result.get('relevance_score')}"
    )

    print(
        f"Matched terms: "
        f"{result.get('matched_terms')}"
    )

    attachments = result.get(
        "attachments",
        [],
    )

    print(
        f"Attachments: "
        f"{len(attachments)}"
    )

    for attachment in attachments:
        print(
            f"   - "
            f"type={attachment.get('type')} "
            f"title={attachment.get('title')}"
        )

        if attachment.get(
            "file_id"
        ):
            print(
                f"     file_id="
                f"{attachment.get('file_id')}"
            )

        if "supported" in attachment:
            print(
                f"     supported="
                f"{attachment.get('supported')}"
            )

        if attachment.get(
            "mode"
        ):
            print(
                f"     mode="
                f"{attachment.get('mode')}"
            )

        if attachment.get(
            "mime_type"
        ):
            print(
                f"     mime="
                f"{attachment.get('mime_type')}"
            )


def main() -> None:
    print()
    print("=" * 50)
    print("TCO GOOGLE CLASSROOM MATERIAL DISCOVERY TEST")
    print("=" * 50)

    print()
    print(
        f"Course ID: {COURSE_ID}"
    )

    service = (
        ClassroomMaterialDiscoveryService()
    )

    for query in QUERIES:
        print()
        print("-" * 50)
        print(
            f"QUERY: {query}"
        )
        print("-" * 50)

        try:
            results = service.discover(
                course_id=COURSE_ID,
                query=query,
                top_k=5,
            )
        except ClassroomDiscoveryError as exc:
            raise AssertionError(
                f"Discovery failed: {exc}"
            ) from exc

        print()
        print(
            f"Results found: {len(results)}"
        )

        assert results, (
            f"No Classroom material found "
            f"for query: {query}"
        )

        for index, result in enumerate(
            results,
            start=1,
        ):
            print()
            print(
                f"RESULT #{index}"
            )

            print_result(
                result
            )

        # -----------------------------------------------------
        # VERIFY RESULT STRUCTURE
        # -----------------------------------------------------

        for result in results:
            assert result.get(
                "course_id"
            ) == COURSE_ID

            assert result.get(
                "material_id"
            )

            assert result.get(
                "title"
            )

            assert (
                result.get(
                    "relevance_score",
                    0,
                )
                > 0
            )

            assert isinstance(
                result.get(
                    "matched_terms"
                ),
                list,
            )

            assert isinstance(
                result.get(
                    "attachments"
                ),
                list,
            )

    # ---------------------------------------------------------
    # SPECIFIC BOOTH ALGORITHM TEST
    # ---------------------------------------------------------

    print()
    print("-" * 50)
    print("SPECIFIC BOOTH ALGORITHM ASSERTION")
    print("-" * 50)

    booth_results = service.discover(
        course_id=COURSE_ID,
        query="Booth Algorithm",
        top_k=5,
    )

    assert booth_results

    booth_found = False

    for result in booth_results:
        title = result.get(
            "title",
            "",
        ).lower()

        attachments = result.get(
            "attachments",
            [],
        )

        attachment_text = " ".join(
            str(
                attachment.get(
                    "title",
                    "",
                )
            )
            for attachment in attachments
        ).lower()

        combined_text = (
            title
            + " "
            + attachment_text
        )

        if (
            "booth" in combined_text
            and "algorithm" in combined_text
        ):
            booth_found = True

            print()
            print(
                "Booth Algorithm material found:"
            )

            print_result(
                result
            )

            break

    assert booth_found, (
        "Expected a Booth Algorithm related "
        "Classroom material but none was found."
    )

    print()
    print(
        "Booth Algorithm discovery test passed."
    )

    # ---------------------------------------------------------
    # TOP-K TEST
    # ---------------------------------------------------------

    print()
    print("-" * 50)
    print("TOP-K TEST")
    print("-" * 50)

    limited_results = service.discover(
        course_id=COURSE_ID,
        query="Computer Organization",
        top_k=2,
    )

    print()
    print(
        f"Requested top_k=2, "
        f"received={len(limited_results)}"
    )

    assert len(limited_results) <= 2

    print(
        "Top-K test passed."
    )

    # ---------------------------------------------------------
    # FINAL
    # ---------------------------------------------------------

    print()
    print("=" * 50)
    print(
        "GOOGLE CLASSROOM MATERIAL DISCOVERY TEST PASSED"
    )
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()