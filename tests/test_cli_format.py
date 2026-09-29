"""Kiểm thử tính năng tự động nhận dạng định dạng --format {auto,txt,md,docx} trong CLI."""
import pytest
from chuviettay.cli import build_parser, main


def test_cli_parser_format_argument():
    parser = build_parser()
    args = parser.parse_args(["write", "-f", "test.md", "--format", "auto"])
    assert args.format == "auto"

    args_md = parser.parse_args(["write", "-f", "test.txt", "--format", "md"])
    assert args_md.format == "md"

    args_docx = parser.parse_args(["write", "-f", "test.docx", "--format", "docx"])
    assert args_docx.format == "docx"


def test_cli_write_markdown_file(tmp_path, tiny_bank_path, capsys):
    pytest.importorskip("markdown_it", reason="Cần cài đặt markdown-it-py để chạy kiểm thử định dạng Markdown")
    md_file = tmp_path / "sample.md"
    md_file.write_text("# Tiêu đề\n\nNội dung văn bản", encoding="utf-8")
    out_xopp = tmp_path / "sample.xopp"

    ret = main([
        "--bank", str(tiny_bank_path),
        "write",
        "-f", str(md_file),
        "-o", str(out_xopp),
        "--format", "auto",
        "--seed", "42",
    ])
    assert ret == 0
    assert out_xopp.exists()

    captured = capsys.readouterr()
    assert "Đã tạo" in captured.out or "dòng" in captured.out


def test_cli_write_markdown_split_list(tmp_path, tiny_bank_path, capsys):
    """Kiểm thử CLI chuyển đổi file Markdown chứa danh sách bị ngắt bởi bảng ra file .xopp."""
    import gzip
    pytest.importorskip("markdown_it", reason="Cần cài đặt markdown-it-py để chạy kiểm thử định dạng Markdown")
    md_file = tmp_path / "split_list.md"
    md_file.write_text("""1. Mục một
2. Mục hai
3. Mục ba

| Cột A | Cột B |
|---|---|
| A | B |

4. Mục bốn
5. Mục năm
""", encoding="utf-8")
    out_xopp = tmp_path / "split_list.xopp"

    ret = main([
        "--bank", str(tiny_bank_path),
        "write",
        "-f", str(md_file),
        "-o", str(out_xopp),
        "--format", "auto",
        "--seed", "42",
    ])
    assert ret == 0
    assert out_xopp.exists()

    with gzip.open(out_xopp, "rt", encoding="utf-8") as gz:
        content = gz.read()
        assert "<xournal" in content
        assert "<stroke" in content


def test_cli_write_docx_file(tmp_path, tiny_bank_path, capsys):
    pytest.importorskip("docx", reason="Cần cài đặt python-docx để chạy kiểm thử định dạng Word")
    import docx
    docx_file = tmp_path / "sample.docx"

    doc = docx.Document()
    doc.add_paragraph("Đoạn văn trong Word")
    doc.save(str(docx_file))

    out_xopp = tmp_path / "docx_out.xopp"

    ret = main([
        "--bank", str(tiny_bank_path),
        "write",
        "-f", str(docx_file),
        "-o", str(out_xopp),
        "--format", "auto",
        "--seed", "42",
    ])
    assert ret == 0
    assert out_xopp.exists()


def test_cli_write_txt_backward_compatible(tmp_path, tiny_bank_path, capsys):
    txt_file = tmp_path / "sample.txt"
    txt_file.write_text("xin chào", encoding="utf-8")
    out_xopp = tmp_path / "txt_out.xopp"

    ret = main([
        "--bank", str(tiny_bank_path),
        "write",
        "-f", str(txt_file),
        "-o", str(out_xopp),
        "--seed", "42",
    ])
    assert ret == 0
    assert out_xopp.exists()


def test_cli_write_sample_fixtures_e2e(tmp_path, tiny_bank_path):
    """Kiểm thử chuyển đổi bộ tài liệu mẫu thực tế fixtures/sample.{txt,md,docx} sang .xopp."""
    import gzip
    import os

    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    sample_txt = os.path.join(fixtures_dir, "sample.txt")
    sample_md = os.path.join(fixtures_dir, "sample.md")
    sample_docx = os.path.join(fixtures_dir, "sample.docx")

    # 1. Chuyển đổi sample.txt
    if os.path.exists(sample_txt):
        out_txt = tmp_path / "sample_txt.xopp"
        ret = main([
            "--bank", str(tiny_bank_path),
            "write",
            "-f", sample_txt,
            "-o", str(out_txt),
            "--format", "auto",
        ])
        assert ret == 0
        assert out_txt.exists()
        with gzip.open(out_txt, "rt", encoding="utf-8") as gz:
            content = gz.read()
            assert "<xournal" in content
            assert "<page" in content
            assert "<stroke" in content

    # 2. Chuyển đổi sample.md
    if os.path.exists(sample_md):
        try:
            import markdown_it  # noqa: F401
            out_md = tmp_path / "sample_md.xopp"
            ret = main([
                "--bank", str(tiny_bank_path),
                "write",
                "-f", sample_md,
                "-o", str(out_md),
                "--format", "auto",
            ])
            assert ret == 0
            assert out_md.exists()
            with gzip.open(out_md, "rt", encoding="utf-8") as gz:
                content = gz.read()
                assert "<xournal" in content
                assert "<stroke" in content
        except ImportError:
            pass

    # 3. Chuyển đổi sample.docx
    if os.path.exists(sample_docx):
        try:
            import docx  # noqa: F401
            out_docx = tmp_path / "sample_docx.xopp"
            ret = main([
                "--bank", str(tiny_bank_path),
                "write",
                "-f", sample_docx,
                "-o", str(out_docx),
                "--format", "auto",
            ])
            assert ret == 0
            assert out_docx.exists()
            with gzip.open(out_docx, "rt", encoding="utf-8") as gz:
                content = gz.read()
                assert "<xournal" in content
        except ImportError:
            pass

