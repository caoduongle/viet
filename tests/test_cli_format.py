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


def test_cli_write_docx_file(tmp_path, tiny_bank_path, capsys):
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
