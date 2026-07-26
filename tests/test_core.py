# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import unittest

from beatflow_core import __version__
from beatflow_core.composition_compiler import compile_composition
from beatflow_core.models import Project
from beatflow_core.renderer import materialize_notes
from beatflow_core.validation import validate_project

from test_composition import small_composition


class BeatFlowProjectTests(unittest.TestCase):
    def test_public_product_and_schema_versions(self) -> None:
        composition = small_composition()
        project = compile_composition(composition)
        self.assertEqual(__version__, "2.0")
        self.assertEqual(composition.schema_version, "1.1")
        self.assertEqual(project.schema_version, "1.0")

    def test_composition_1_0_remains_readable(self) -> None:
        composition = small_composition()
        payload = composition.model_dump(mode="json")
        payload["schema_version"] = "1.0"
        for section in payload["sections"]:
            section.pop("phrases", None)
            section.pop("phrase_stages", None)
            section.pop("arrivals", None)
            section.pop("silences", None)
        legacy = type(composition).model_validate(payload)
        self.assertEqual(legacy.schema_version, "1.0")
        self.assertTrue(validate_project(compile_composition(legacy)).valid)

    def test_compiled_project_is_semantically_valid(self) -> None:
        project = compile_composition(small_composition())
        report = validate_project(project)
        self.assertTrue(report.valid, report.model_dump_json(indent=2))
        self.assertGreater(report.stats["bars"], 0)

    def test_materialization_is_deterministic(self) -> None:
        project = compile_composition(small_composition())
        self.assertEqual(materialize_notes(project), materialize_notes(project))

    def test_missing_reference_is_reported(self) -> None:
        payload = compile_composition(small_composition()).model_dump(mode="json")
        payload["links"][0]["clip_id"] = "clip_missing"
        report = validate_project(Project.model_validate(payload))
        self.assertFalse(report.valid)
        self.assertIn("missing_clip", {issue.code for issue in report.issues})

    def test_schema_rejects_unknown_fields(self) -> None:
        payload = compile_composition(small_composition()).model_dump(mode="json")
        payload["surprise"] = True
        with self.assertRaises(Exception):
            Project.model_validate(payload)

    def test_json_round_trip(self) -> None:
        project = compile_composition(small_composition())
        reloaded = Project.model_validate_json(
            json.dumps(project.model_dump(mode="json"))
        )
        self.assertEqual(reloaded, project)


if __name__ == "__main__":
    unittest.main()
