from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.bootstrap import build_default_registry
from backend.core.task import Task
from backend.agents.assessment_agent import AssessmentAgent
from backend.agents.master_agent import MasterAgent
from backend.agents.evaluation_agent import EvaluationAgent
from backend.services.assessment_approval import approve_assessment
from backend.workflows.assessment_delivery import AssessmentDeliveryWorkflow


class TestBackendAgents(unittest.TestCase):
    def setUp(self):
        self.registry = build_default_registry()

    def test_master_agent_catalog(self):
        master = MasterAgent(self.registry)
        catalog = master._build_capability_catalog()
        self.assertIn("assessment.create", catalog)
        self.assertIn("assessment_agent", catalog)

    def test_assessment_agent_execution(self):
        agent = AssessmentAgent()
        task = Task(
            capability="assessment.create",
            input_data={
                "topic": "Newton Laws of Motion",
                "question_count": 3,
                "marks": 15,
                "generation_mode": "llm_generated",
                "class_level": "Class 11",
                "subject": "Physics"
            }
        )
        state = {
            "topic": "Newton Laws of Motion",
            "question_count": 3,
            "marks": 15,
            "generation_mode": "llm_generated"
        }
        res = agent.run(state, task)
        self.assertIn(res.get("status"), ["assessment_ready_for_review", "assessment_generated"])
        questions = res.get("questions", [])
        self.assertEqual(len(questions), 3)
        self.assertEqual(len(questions[0]["options"]), 4)
        self.assertIn("correct_option", questions[0])

    def test_assessment_approval_service(self):
        state = {
            "assessment_review_status": "passed",
            "status": "assessment_ready_for_review",
            "topic": "Calculus"
        }
        approved = approve_assessment(state, approved_by="teacher-1", comment="Approved by teacher")
        self.assertEqual(approved["status"], "assessment_approved")
        self.assertEqual(approved["approval_status"], "approved")

    def test_evaluation_agent_scoring(self):
        agent = EvaluationAgent()
        questions = [
            {
                "id": "q1",
                "question_number": 1,
                "question": "What is 2 + 2?",
                "options": ["2", "3", "4", "5"],
                "correct_option": 3,
                "marks": 5.0
            }
        ]
        answer_key = [{"question_id": "q1", "correct_option": 3}]
        marking_scheme = [{"question_id": "q1", "marks": 5.0}]
        submission_correct = {
            "student_id": "STU101",
            "student_name": "Alice",
            "answers": [{"question_id": "q1", "answer": "4"}]
        }
        res_correct = agent.evaluate_submission(
            questions=questions,
            answer_key=answer_key,
            marking_scheme=marking_scheme,
            submission=submission_correct
        )
        self.assertEqual(res_correct["obtained_marks"], 5.0)
        self.assertEqual(res_correct["correct_answers"], 1)

        submission_wrong = {
            "student_id": "STU102",
            "student_name": "Bob",
            "answers": [{"question_id": "q1", "answer": "2"}]
        }
        res_wrong = agent.evaluate_submission(
            questions=questions,
            answer_key=answer_key,
            marking_scheme=marking_scheme,
            submission=submission_wrong
        )
        self.assertEqual(res_wrong["obtained_marks"], 0.0)
        self.assertEqual(res_wrong["wrong_answers"], 1)


if __name__ == "__main__":
    unittest.main()
