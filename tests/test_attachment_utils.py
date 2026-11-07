import tempfile
import unittest
from pathlib import Path

from app.api.attachment_utils import remove_attachment, session_directory


class RemoveAttachmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        temporary_root = Path(self.temporary_directory.name)
        self.upload_root = temporary_root / "updated"
        self.output_root = temporary_root / "output"
        self.thread_id = "test-002"
        self.upload_dir = session_directory(self.upload_root, self.thread_id)
        self.output_dir = session_directory(self.output_root, self.thread_id)
        self.upload_dir.mkdir(parents=True)
        self.output_dir.mkdir(parents=True)

    def write_staged(self, filename: str, content: str) -> Path:
        path = self.upload_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def write_work_copy(self, filename: str, content: str) -> Path:
        path = self.output_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def test_removes_unchanged_work_copy(self) -> None:
        staged = self.write_staged("same_copy.txt", "same")
        work_copy = self.write_work_copy("same_copy.txt", "same")

        result = remove_attachment(
            self.upload_root,
            self.output_root,
            self.thread_id,
            "same_copy.txt",
        )

        self.assertEqual(result.work_copy, "removed")
        self.assertFalse(staged.exists())
        self.assertFalse(work_copy.exists())

    def test_preserves_modified_work_copy(self) -> None:
        staged = self.write_staged("changed_copy.txt", "original")
        work_copy = self.write_work_copy("changed_copy.txt", "changed")

        result = remove_attachment(
            self.upload_root,
            self.output_root,
            self.thread_id,
            "changed_copy.txt",
        )

        self.assertEqual(result.work_copy, "kept_modified")
        self.assertFalse(staged.exists())
        self.assertEqual(work_copy.read_text(encoding="utf-8"), "changed")

    def test_removes_staged_file_without_work_copy(self) -> None:
        staged = self.write_staged("only_upload.txt", "upload")

        result = remove_attachment(
            self.upload_root,
            self.output_root,
            self.thread_id,
            "only_upload.txt",
        )

        self.assertEqual(result.work_copy, "not_found")
        self.assertFalse(staged.exists())

    def test_rejects_missing_attachment(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "上传附件不存在"):
            remove_attachment(
                self.upload_root,
                self.output_root,
                self.thread_id,
                "missing.txt",
            )

    def test_rejects_invalid_filenames(self) -> None:
        for filename in ("", ".", "..", "../private.txt", "folder/file.txt", "C:\\private.txt"):
            with self.subTest(filename=filename):
                with self.assertRaisesRegex(ValueError, "无效的文件名"):
                    remove_attachment(
                        self.upload_root,
                        self.output_root,
                        self.thread_id,
                        filename,
                    )

    def test_rejects_invalid_thread_ids(self) -> None:
        for thread_id in ("", ".", "..", "../other", "other/session", "含中文"):
            with self.subTest(thread_id=thread_id):
                with self.assertRaisesRegex(ValueError, "无效的会话编号"):
                    session_directory(self.upload_root, thread_id)


if __name__ == "__main__":
    unittest.main()
