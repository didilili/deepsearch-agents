import tempfile
import unittest
from pathlib import Path

from app.utils.path_utils import resolve_path


class ResolvePathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.output_root = Path(self.temporary_directory.name) / "output"
        self.session_dir = (self.output_root / "session_practice").resolve()
        self.session_dir.mkdir(parents=True)

    def assert_resolves_inside_session(self, filename: str, expected: str) -> None:
        resolved = Path(resolve_path(filename, str(self.session_dir)))
        self.assertEqual(resolved, (self.session_dir / expected).resolve())
        self.assertTrue(resolved.is_relative_to(self.session_dir))

    def test_allows_session_relative_paths(self) -> None:
        self.assert_resolves_inside_session("report.md", "report.md")
        self.assert_resolves_inside_session("notes/report.md", "notes/report.md")
        self.assert_resolves_inside_session("report..md", "report..md")

    def test_allows_supported_virtual_paths(self) -> None:
        self.assert_resolves_inside_session("/workspace/report.md", "report.md")
        self.assert_resolves_inside_session("/mnt/data/report.md", "report.md")
        self.assert_resolves_inside_session(
            "output/session_practice/report.md",
            "report.md",
        )

    def test_allows_absolute_path_inside_session(self) -> None:
        filename = self.session_dir / "report.md"
        self.assertEqual(
            Path(resolve_path(str(filename), str(self.session_dir))),
            filename,
        )

    def test_collapses_duplicate_session_directory(self) -> None:
        filename = self.session_dir / "session_practice" / "notes" / "report.md"
        self.assertEqual(
            Path(resolve_path(str(filename), str(self.session_dir))),
            self.session_dir / "notes" / "report.md",
        )

    def test_rejects_parent_directory_segments(self) -> None:
        for filename in (
            "../outside.md",
            "../session_other/report.md",
            "../session_practice/../../outside.md",
            "notes/../report.md",
        ):
            with self.subTest(filename=filename):
                with self.assertRaisesRegex(ValueError, "父目录"):
                    resolve_path(filename, str(self.session_dir))

    def test_rejects_absolute_path_outside_session(self) -> None:
        filename = self.output_root / "outside.md"
        with self.assertRaisesRegex(ValueError, "当前会话目录之外"):
            resolve_path(str(filename), str(self.session_dir))

    def test_rejects_upload_staging_path(self) -> None:
        with self.assertRaisesRegex(ValueError, "上传暂存路径"):
            resolve_path("updated/session_other/private.txt", str(self.session_dir))


if __name__ == "__main__":
    unittest.main()
