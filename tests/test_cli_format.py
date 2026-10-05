"""Kiểm thử CLI cho các cờ định dạng trang: --paper, --orientation, --background, --background-spacing."""
import gzip
import io
import os
import xml.etree.ElementTree as ET
import pytest

from chuviettay import cli


def run_cli(capsys, bank_path, *args):
    """Chạy cli.main với danh sách tham số và trả về (exit_code, capsys.readouterr())."""
    try:
        cli.main(["--bank", bank_path] + list(args))
        rc = 0
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    return rc, capsys.readouterr()


def test_cli_write_paper_and_orientation(capsys, tiny_bank_path, tmp_path):
    out = str(tmp_path / "cli_a3_land.xopp")
    rc, cap = run_cli(
        capsys,
        tiny_bank_path,
        "write",
        "-t",
        "Chào buổi sáng",
        "-o",
        out,
        "--paper",
        "a3",
        "--orientation",
        "landscape",
        "--seed",
        "1",
    )
    assert rc == 0
    assert os.path.exists(out)

    raw = gzip.decompress(open(out, "rb").read()).decode("utf-8")
    assert '<page width="1190.55" height="841.89">' in raw


def test_cli_write_background_graph_spacing(capsys, tiny_bank_path, tmp_path):
    out = str(tmp_path / "cli_graph.xopp")
    rc, cap = run_cli(
        capsys,
        tiny_bank_path,
        "write",
        "-t",
        "Viết chữ trên ô li",
        "-o",
        out,
        "--paper",
        "a4",
        "--background",
        "graph",
        "--background-spacing",
        "5mm",
        "--seed",
        "1",
    )
    assert rc == 0
    assert os.path.exists(out)

    raw = gzip.decompress(open(out, "rb").read()).decode("utf-8")
    assert '<page width="595.28" height="841.89">' in raw
    assert 'style="graph"' in raw
    assert 'config="r1=14.17"' in raw


def test_cli_write_custom_paper_with_units(capsys, tiny_bank_path, tmp_path):
    out = str(tmp_path / "cli_custom.xopp")
    rc, cap = run_cli(
        capsys,
        tiny_bank_path,
        "write",
        "-t",
        "Khổ giấy tùy chỉnh",
        "-o",
        out,
        "--paper",
        "custom",
        "--paper-width",
        "15cm",
        "--paper-height",
        "20cm",
        "--seed",
        "1",
    )
    assert rc == 0
    assert os.path.exists(out)

    raw = gzip.decompress(open(out, "rb").read()).decode("utf-8")
    # 15 cm ~ 425.20 pt, 20 cm ~ 566.93 pt
    assert '<page width="425.2" height="566.93">' in raw or '<page width="425.20" height="566.93">' in raw


def test_cli_write_mode_fidelity_and_semantic(capsys, tiny_bank_path, tmp_path, monkeypatch):
    from chuviettay.fidelity.converter import FidelityConverter

    if not FidelityConverter.is_word_available():
        import json
        import shutil
        fix_json = "tests/fixtures/fidelity/sample_fidelity_data.json"
        fix_pdf = "tests/fixtures/fidelity/sample_background.pdf"
        with open(fix_json, "r", encoding="utf-8") as f:
            mock_data = json.load(f)
        monkeypatch.setattr(FidelityConverter, "extract_spatial_data", lambda docx, out_json=None: mock_data)
        monkeypatch.setattr(FidelityConverter, "convert_to_pdf", lambda docx, out_pdf: shutil.copyfile(fix_pdf, out_pdf))

    sample_docx = "tests/fixtures/sample.docx"
    out_fid = str(tmp_path / "cli_fid.xopp")

    rc, cap = run_cli(
        capsys,
        tiny_bank_path,
        "write",
        sample_docx,
        "-o",
        out_fid,
        "--mode",
        "fidelity",
    )
    assert rc == 0
    assert os.path.exists(out_fid)
    assert "Fidelity mode:" in cap.out

    raw_fid = gzip.decompress(open(out_fid, "rb").read()).decode("utf-8")
    assert '<background type="pdf"' in raw_fid


def test_cli_fidelity_mode_rejects_non_docx(tiny_bank_path, tmp_path):
    out = str(tmp_path / "cli_invalid.xopp")
    with pytest.raises(SystemExit) as excinfo:
        cli.main([
            "--bank",
            tiny_bank_path,
            "write",
            "-t",
            "Văn bản thuần",
            "-o",
            out,
            "--mode",
            "fidelity",
        ])
    assert "chỉ áp dụng cho tệp .docx" in str(excinfo.value)
