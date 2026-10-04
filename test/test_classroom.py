from __future__ import annotations

from pathlib import Path

from backend.tools.classroom import (
    ClassroomTool,
    ClassroomToolError,
)


def main() -> None:
    print()
    print("=" * 50)
    print("TCO GOOGLE CLASSROOM TOOL TEST")
    print("=" * 50)
    print()

    root = Path(__file__).resolve().parents[1]

    credentials_file = root / "credentials.json"
    token_file = root / "token.json"

    print(f"Credentials file: {credentials_file}")
    print(f"Token file:       {token_file}")
    print()

    if not credentials_file.exists():
        print("ERROR:")
        print("credentials.json not found.")
        print()
        print(
            "Place your Google OAuth desktop-app "
            "credentials.json in E:\\TCO"
        )
        return

    try:
        classroom = ClassroomTool(
            credentials_file=str(credentials_file),
            token_file=str(token_file),
        )

        # -----------------------------------------------------
        # COURSES
        # -----------------------------------------------------

        print("-" * 50)
        print("STEP 1 — LIST CLASSROOM COURSES")
        print("-" * 50)

        courses = classroom.list_courses()

        print()
        print(f"Courses found: {len(courses)}")
        print()

        if not courses:
            print(
                "No ACTIVE Classroom courses were returned."
            )
            print()
            print(
                "The API connection and authentication may "
                "still be working, but the account currently "
                "has no visible active course."
            )
            return

        for index, course in enumerate(
            courses,
            start=1,
        ):
            print(
                f"{index}. "
                f"{course.get('name', 'Unnamed')} "
                f"| id={course.get('id')} "
                f"| section={course.get('section', '')}"
            )

        # -----------------------------------------------------
        # FIRST COURSE MATERIALS
        # -----------------------------------------------------

        course = courses[0]

        course_id = course.get("id")

        if not course_id:
            raise ClassroomToolError(
                "First course does not contain an ID."
            )

        print()
        print("-" * 50)
        print("STEP 2 — LIST COURSE MATERIALS")
        print("-" * 50)

        print()
        print(
            f"Course: {course.get('name', '')}"
        )
        print(
            f"Course ID: {course_id}"
        )

        materials = classroom.list_course_materials(
            course_id
        )

        print()
        print(
            f"Course materials found: {len(materials)}"
        )

        # -----------------------------------------------------
        # DISPLAY MATERIALS
        # -----------------------------------------------------

        for index, material in enumerate(
            materials,
            start=1,
        ):
            print()
            print(
                f"{index}. "
                f"{material.get('title', 'Untitled')}"
            )

            print(
                f"   material_id: "
                f"{material.get('material_id')}"
            )

            print(
                f"   state: "
                f"{material.get('state')}"
            )

            attachments = material.get(
                "materials",
                [],
            )

            print(
                f"   attachments: "
                f"{len(attachments)}"
            )

            for attachment in attachments:
                print(
                    f"      - "
                    f"type={attachment.get('type')}"
                )

                if attachment.get("title"):
                    print(
                        f"        title="
                        f"{attachment.get('title')}"
                    )

                if attachment.get("file_id"):
                    print(
                        f"        file_id="
                        f"{attachment.get('file_id')}"
                    )

                if attachment.get("url"):
                    print(
                        f"        url="
                        f"{attachment.get('url')}"
                    )

        # -----------------------------------------------------
        # DRIVE ATTACHMENT CHECK
        # -----------------------------------------------------

        print()
        print("-" * 50)
        print("STEP 3 — CHECK DRIVE ATTACHMENTS")
        print("-" * 50)

        drive_attachments = []

        for material in materials:
            for attachment in material.get(
                "materials",
                [],
            ):
                if (
                    attachment.get("type")
                    == "drive_file"
                    and attachment.get("file_id")
                ):
                    drive_attachments.append(
                        attachment
                    )

        print()
        print(
            f"Drive attachments found: "
            f"{len(drive_attachments)}"
        )

        for attachment in drive_attachments:
            file_id = attachment["file_id"]

            info = classroom.get_supported_file_info(
                file_id
            )

            metadata = info.get(
                "metadata",
                {},
            )

            print()
            print(
                f"File: "
                f"{metadata.get('name', '')}"
            )

            print(
                f"File ID: "
                f"{file_id}"
            )

            print(
                f"MIME: "
                f"{info.get('mime_type', '')}"
            )

            print(
                f"Supported: "
                f"{info.get('supported')}"
            )

            print(
                f"Mode: "
                f"{info.get('mode')}"
            )

        # -----------------------------------------------------
        # SUCCESS
        # -----------------------------------------------------

        print()
        print("=" * 50)
        print("GOOGLE CLASSROOM TOOL TEST PASSED")
        print("=" * 50)
        print()

    except ClassroomToolError as exc:
        print()
        print("=" * 50)
        print("GOOGLE CLASSROOM TOOL TEST FAILED")
        print("=" * 50)
        print()
        print(str(exc))
        print()

    except Exception as exc:
        print()
        print("=" * 50)
        print("UNEXPECTED ERROR")
        print("=" * 50)
        print()
        print(type(exc).__name__)
        print(str(exc))
        print()


if __name__ == "__main__":
    main()