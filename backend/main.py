from backend.graph import workflow


def run_tco(request: str):

    initial_state = {
        "teacher_request": request
    }

    final_state = workflow.invoke(initial_state)

    print("\nFINAL STATE:")
    print(final_state)


if __name__ == "__main__":

    request = input("Teacher: ")

    run_tco(request)