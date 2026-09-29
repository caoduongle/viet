"""Kiểm thử bắt lỗi nghiêm ngặt định dạng tệp không được hỗ trợ (UnsupportedFormatError)."""
import pytest

from chuviettay.importer.base import UnsupportedFormatError, get_importer_for_path
from chuviettay.importer.docx_importer import DocxImporter
from chuviettay.importer.markdown_importer import MarkdownImporter
from chuviettay.importer.txt_importer import TxtImporter


@pytest.mark.parametrize("invalid_path", [
    "document.pdf",
    "spreadsheet.xlsx",
    "photo.png",
    "archive.zip",
    "data.json",
])
def test_unsupported_extensions_raise_error(invalid_path):
    with pytest.raises(UnsupportedFormatError, match="không được hỗ trợ"):
        get_importer_for_path(invalid_path, format_name="auto")


@pytest.mark.parametrize("invalid_fmt", ["pdf", "xlsx", "html", "epub"])
def test_unsupported_format_name_raises_error(invalid_fmt):
    with pytest.raises(UnsupportedFormatError, match="không được hỗ trợ"):
        get_importer_for_path("test.txt", format_name=invalid_fmt)


def test_supported_formats_return_correct_importer():
    from chuviettay.importer.dependency import OptionalDependencyError

    assert isinstance(get_importer_for_path("file.txt"), TxtImporter)
    try:
        assert isinstance(get_importer_for_path("file.md"), MarkdownImporter)
        assert isinstance(get_importer_for_path("file.markdown"), MarkdownImporter)
    except OptionalDependencyError as exc:
        assert exc.package_name == "markdown_it"

    try:
        assert isinstance(get_importer_for_path("file.docx"), DocxImporter)
    except OptionalDependencyError as exc:
        assert exc.package_name == "docx"

    assert isinstance(get_importer_for_path("", format_name="txt"), TxtImporter)
    assert isinstance(get_importer_for_path("", format_name="auto"), TxtImporter)
