from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.workspace_core import (
    RequirementExtractor,
    WorkspaceManager,
    TASK_ASSESSMENT,
    TASK_EVALUATION,
    PHASE_CONFIRMATION,
    PHASE_REVIEW_REQUIRED,
    PHASE_APPROVED,
    PHASE_PUBLISHED,
    PHASE_COMPLETED,
    SOURCE_GENERAL_KNOWLEDGE,
)


class TestRequirementExtraction(unittest.TestCase):
    def test_example_1_standard_assessment(self):
        text = "Create an assessment of 5 MCQs for 20 marks on Machine Learning Basics."
        reqs = RequirementExtractor.extract_requirements(text, {})
        self.assertEqual(reqs.get("question_count"), 5)
        self.assertEqual(reqs.get("marks"), 20)
        self.assertEqual(reqs.get("question_type"), "MCQ")
        self.assertIn("Machine Learning Basics", reqs.get("topic", ""))
        next_key = RequirementExtractor.get_next_question_key(reqs)
        self.assertEqual(next_key, "source", "Must ask for source selection next")

    def test_example_2_spelling_mistakes(self):
        text = "create assement of the 5mcq of 20 marks of machine learning basics"
        reqs = RequirementExtractor.extract_requirements(text, {})
        self.assertEqual(reqs.get("question_count"), 5)
        self.assertEqual(reqs.get("marks"), 20)
        self.assertEqual(reqs.get("question_type"), "MCQ")
        self.assertIn("Machine Learning Basics", reqs.get("topic", "").title())
        next_key = RequirementExtractor.get_next_question_key(reqs)
        self.assertEqual(next_key, "source")

    def test_example_3_all_known_fields(self):
        text = "Create 10 easy MCQs on Python loops for BTech first year, Computer Programming, total 30 marks, using general knowledge."
        reqs = RequirementExtractor.extract_requirements(text, {})
        self.assertEqual(reqs.get("question_count"), 10)
        self.assertEqual(reqs.get("marks"), 30)
        self.assertEqual(reqs.get("source"), "General Knowledge")
        self.assertEqual(reqs.get("difficulty"), "Easy")
        self.assertIn("Btech", reqs.get("class_level", ""))
        self.assertEqual(reqs.get("subject"), "Computer Programming")
        self.assertIn("Python Loops", reqs.get("topic", ""))
        next_key = RequirementExtractor.get_next_question_key(reqs)
        self.assertIn(next_key, ["chapter", "difficulty", None])

    def test_example_4_only_topic_provided(self):
        text = "Create an assessment on binary search."
        reqs = RequirementExtractor.extract_requirements(text, {})
        self.assertIn("Binary Search", reqs.get("topic", ""))
        next_key = RequirementExtractor.get_next_question_key(reqs)
        self.assertIn(next_key, ["question_count", "marks"])

    def test_example_5_multiple_missing_details_in_one_reply(self):
        curr = {
            "topic": "Newton Laws",
            "question_count": 5,
            "marks": 20,
            "source": "General Knowledge"
        }
        reply = "Subject is Physics, for Class 12"
        reqs = RequirementExtractor.extract_requirements(reply, curr, current_question_key="subject")
        self.assertEqual(reqs.get("subject"), "Physics")
        self.assertEqual(reqs.get("class_level"), "Class 12")
        next_key = RequirementExtractor.get_next_question_key(reqs)
        self.assertNotIn(next_key, ["subject", "class_level"])

    def test_example_6_skip_optional_chapter(self):
        curr = {
            "topic": "Newton Laws",
            "question_count": 5,
            "marks": 20,
            "source": "General Knowledge",
            "subject": "Physics",
            "class_level": "Class 12"
        }
        reply = "skip"
        reqs = RequirementExtractor.extract_requirements(reply, curr, current_question_key="chapter")
        self.assertIn("chapter", reqs)
        next_key = RequirementExtractor.get_next_question_key(reqs)
        self.assertNotEqual(next_key, "chapter")


class TestStateMachineAndWorkflow(unittest.TestCase):
    def setUp(self):
        self.wm = WorkspaceManager()

    def test_end_to_end_assessment_and_evaluation(self):
        # Turn 1: Initial request
        conv = self.wm.handle_user_message("Create an assessment of 5 MCQs for 20 marks on Machine Learning Basics.")
        self.assertEqual(len(conv["messages"]), 2)
        latest = conv["messages"][-1]
        self.assertIsNotNone(latest.get("quick_replies"))

        # Turn 2: Source selection
        conv = self.wm.handle_user_message("General Knowledge")
        latest = conv["messages"][-1]

        # Turn 3: Class level
        conv = self.wm.handle_user_message("BTech 1st Year")
        latest = conv["messages"][-1]

        # Turn 4: Chapter (skip)
        conv = self.wm.handle_user_message("No specific chapter. Cover the fundamentals.")
        latest = conv["messages"][-1]

        # Turn 5: Difficulty
        conv = self.wm.handle_user_message("Easy to medium")
        latest = conv["messages"][-1]
        self.assertEqual(conv["phase"], PHASE_CONFIRMATION)
        self.assertIn("Shall I generate it?", latest["content"])

        # Turn 6: Confirm generation
        conv = self.wm.handle_user_message("Yes, Generate")
        self.assertEqual(conv["phase"], PHASE_REVIEW_REQUIRED)
        self.assertIsNotNone(conv.get("active_artifact"))
        art = conv["active_artifact"]
        self.assertEqual(art["artifact_type"], "assessment")
        self.assertEqual(art["question_count"], 5)
        self.assertEqual(art["status"], "draft")
        self.assertTrue(conv["show_artifact_panel"])

        # Approval
        app_res = self.wm.approve_assessment()
        self.assertTrue(app_res["success"])
        self.assertEqual(art["status"], "approved")

        # Publishing
        pub_res = self.wm.publish_assessment()
        self.assertTrue(pub_res["success"])
        self.assertEqual(art["status"], "published")
        self.assertIn("https://docs.google.com/forms/", pub_res["published_url"])

        # Evaluation
        conv = self.wm.handle_user_message("Evaluate student responses for this assessment.")
        self.assertEqual(conv["active_artifact"]["artifact_type"], "evaluation")
        self.assertEqual(conv["active_artifact"]["total_students"], 3)
        self.assertGreater(conv["active_artifact"]["average_score"], 0)

    def test_multi_conversation_isolation(self):
        c1_id = self.wm.active_conversation_id
        self.wm.handle_user_message("Create an assessment on binary search.")
        c1_msg_count = len(self.wm.get_active_conversation()["messages"])

        # Start second conversation
        c2_id = self.wm.create_new_conversation("Second Chat")
        self.assertEqual(self.wm.active_conversation_id, c2_id)
        self.assertEqual(len(self.wm.get_active_conversation()["messages"]), 0)

        # Switch back to first conversation
        self.wm.switch_conversation(c1_id)
        self.assertEqual(self.wm.active_conversation_id, c1_id)
        self.assertEqual(len(self.wm.get_active_conversation()["messages"]), c1_msg_count)

    def test_panel_toggle(self):
        state1 = self.wm.toggle_artifact_panel()
        state2 = self.wm.toggle_artifact_panel()
        self.assertNotEqual(state1, state2)


if __name__ == "__main__":
    unittest.main()
