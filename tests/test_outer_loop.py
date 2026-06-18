import tempfile
import unittest
from pathlib import Path

from outer_loop import (
    OuterLoopStore, OuterLoopWorker, RunRecord, classify_edit,
    generate_candidate_lessons, run_replay_eval, write_agteo_brain_note,
)


class TestOuterLoop(unittest.TestCase):
    def make_run(self, task_type="email", draft="We will deliver Friday.", final="We could likely deliver Friday if confirmed by the source of truth."):
        return RunRecord.completed(task_type=task_type, prompt="draft", draft_output=draft, final_output=final, scope_type="project", scope_value="acme")

    def test_run_record_serialization_and_retrieval(self):
        with tempfile.TemporaryDirectory() as td:
            store = OuterLoopStore(Path(td) / "outer.sqlite")
            run = self.make_run()
            store.record_run(run)
            loaded = store.get_run(run.run_id)
            self.assertEqual(loaded.run_id, run.run_id)
            self.assertEqual(loaded.draft_output, run.draft_output)
            self.assertEqual(loaded.final_output, run.final_output)
            self.assertTrue(loaded.human_edit_diff)

    def test_diff_classification(self):
        self.assertEqual(classify_edit("We will do it.", "We could maybe do it."), "commitment softened")
        self.assertEqual(classify_edit("Hi", "According to the source, the date is June 18 with more context."), "missing fact added")
        self.assertEqual(classify_edit("long rejected content", "No"), "rejection/deletion")

    def test_candidate_generation_and_clustering(self):
        runs = [self.make_run(), self.make_run()]
        candidates = generate_candidate_lessons(runs)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].frequency, 2)
        with tempfile.TemporaryDirectory() as td:
            store = OuterLoopStore(Path(td) / "outer.sqlite")
            c1 = store.upsert_candidate(candidates[0])
            c2 = store.upsert_candidate(generate_candidate_lessons(runs)[0])
            self.assertEqual(c1.candidate_id, c2.candidate_id)
            self.assertEqual(len(store.list_candidates()), 1)

    def test_gate_blocks_without_eval_and_promotes_after_pass(self):
        with tempfile.TemporaryDirectory() as td:
            store = OuterLoopStore(Path(td) / "outer.sqlite")
            runs = [self.make_run(), self.make_run()]
            candidate = store.upsert_candidate(generate_candidate_lessons(runs)[0])
            with self.assertRaises(ValueError):
                store.promote(candidate, "title", "body")
            result = run_replay_eval(candidate, runs)
            self.assertTrue(result.passed)
            store.save_eval(result)
            lesson_id = store.promote(candidate, "title", "body")
            self.assertEqual(len(store.active_lessons("project", "acme")), 1)
            self.assertEqual(len(store.active_lessons("project", "other")), 0)
            store.rollback(lesson_id, "regression")
            self.assertEqual(store.active_lessons("project", "acme"), [])

    def test_worker_and_agteo_note(self):
        with tempfile.TemporaryDirectory() as td:
            store = OuterLoopStore(Path(td) / "outer.sqlite")
            store.record_run(self.make_run())
            store.record_run(self.make_run())
            candidates = OuterLoopWorker(store).run_once()
            self.assertEqual(len(candidates), 1)
            path = write_agteo_brain_note(Path(td) / "brain", candidates[0], "lesson-1")
            self.assertTrue(path.exists())
            self.assertIn("## Evidence", path.read_text())


if __name__ == "__main__":
    unittest.main()
