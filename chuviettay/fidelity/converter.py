"""Bộ chuyển đổi và trích xuất bố cục cố định (Fidelity Converter).

Hỗ trợ Microsoft Word COM (trên Windows) và LibreOffice (trên Linux/macOS), kèm cơ chế UTF-8 JSON bridge.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any

_log = logging.getLogger(__name__)


class FidelityConverter:
    """Điều phối trích xuất tọa độ không gian và kết xuất PDF nền cho DOCX."""

    _word_available_cache: bool | None = None
    _libreoffice_available_cache: bool | None = None

    @classmethod
    def reset_cache(cls) -> None:
        """Đặt lại bộ nhớ đệm trạng thái khả dụng của công cụ (phục vụ kiểm thử)."""
        cls._word_available_cache = None
        cls._libreoffice_available_cache = None

    @classmethod
    def _run_powershell_script(cls, script_content: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
        """Thực thi an toàn một khối lệnh PowerShell bằng tệp tạm thời với ExecutionPolicy Bypass."""
        fd, script_path = tempfile.mkstemp(prefix="ps_", suffix=".ps1")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(script_content)

        try:
            ps_exe = shutil.which("powershell") or "powershell"
            return subprocess.run(
                [ps_exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script_path],
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        finally:
            if os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except OSError:
                    pass

    @classmethod
    def is_word_available(cls) -> bool:
        """Kiểm tra Microsoft Word COM có khả dụng trên hệ thống Windows hay không (R6)."""
        if cls._word_available_cache is not None:
            return cls._word_available_cache
        if sys.platform != "win32":
            cls._word_available_cache = False
            return False

        ps_cmd = """
try {
    $ErrorActionPreference = 'Stop'
    $w = New-Object -ComObject Word.Application
    if ($w -ne $null) {
        $v = $w.Version
        $w.Quit(0)
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($w) | Out-Null
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
        Write-Host $v
    } else {
        exit 1
    }
} catch {
    exit 1
}
"""
        try:
            res = cls._run_powershell_script(ps_cmd, timeout=10)
            avail = res.returncode == 0 and bool(res.stdout.strip())
            cls._word_available_cache = avail
            return avail
        except Exception as e:
            _log.debug("Kiểm tra Word COM thất bại: %s", e)
            cls._word_available_cache = False
            return False

    @classmethod
    def is_libreoffice_available(cls) -> bool:
        """Kiểm tra LibreOffice soffice có khả dụng hay không (R6)."""
        if cls._libreoffice_available_cache is not None:
            return cls._libreoffice_available_cache
        avail = shutil.which("soffice") is not None or shutil.which("libreoffice") is not None
        cls._libreoffice_available_cache = avail
        return avail

    @classmethod
    def is_available(cls) -> bool:
        """Hệ thống có ít nhất một công cụ dựng layout cố định hay không."""
        return cls.is_word_available() or cls.is_libreoffice_available()

    @classmethod
    def extract_spatial_data(cls, docx_path: str, output_json_path: str | None = None) -> dict[str, Any]:
        """Trích xuất danh sách các trang và tọa độ các TextBox/ImageBox từ DOCX qua UTF-8 JSON bridge."""
        docx_abs = os.path.abspath(docx_path)
        if not os.path.exists(docx_abs):
            raise FileNotFoundError(f"Không tìm thấy tệp DOCX: {docx_path}")

        cleanup_temp = False
        if output_json_path is None:
            fd, json_abs = tempfile.mkstemp(prefix="spatial_", suffix=".json")
            os.close(fd)
            cleanup_temp = True
        else:
            json_abs = os.path.abspath(output_json_path)

        try:
            if cls.is_word_available():
                cls._extract_with_word_com(docx_abs, json_abs)
            elif cls.is_libreoffice_available():
                raise RuntimeError(
                    "Fidelity Mode yêu cầu Microsoft Word COM trên Windows để trích xuất tọa độ không gian chính xác. "
                    "LibreOffice chỉ hỗ trợ tạo PDF nền; vui lòng chuyển sang môi trường Windows có Word hoặc chọn chế độ Semantic Mode (--mode semantic)."
                )
            else:
                raise RuntimeError(
                    "Fidelity Mode yêu cầu Microsoft Word (Windows) để trích xuất tọa độ văn bản và xử lý bố cục cố định. "
                    "Vui lòng cài đặt Microsoft Word hoặc sử dụng chế độ Semantic Mode (--mode semantic)."
                )

            with open(json_abs, "r", encoding="utf-8") as f:
                return json.load(f)
        finally:
            if cleanup_temp and os.path.exists(json_abs):
                try:
                    os.remove(json_abs)
                except OSError:
                    pass

    @staticmethod
    def _ps_quote(path: str) -> str:
        """Thoát chuỗi an toàn cho PowerShell để tránh lỗi dấu nháy và ký tự đặc biệt ($)."""
        return "'" + path.replace("'", "''") + "'"

    @classmethod
    def _extract_with_word_com(cls, docx_abs: str, json_abs: str) -> None:
        """Thực thi script PowerShell Word COM trích xuất tọa độ sang tệp UTF-8 JSON."""
        docx_q = cls._ps_quote(docx_abs)
        json_q = cls._ps_quote(json_abs)
        ps_script = f"""
$ErrorActionPreference = 'Stop'
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {{
    $doc = $w.Documents.Open({docx_q})
    $pagesDict = @{{}}
    $totalPages = $doc.ComputeStatistics(2) # wdStatisticPages

    for ($i = 1; $i -le $totalPages; $i++) {{
        $pagesDict[$i] = [System.Collections.Generic.List[hashtable]]::new()
    }}

    $sec = $doc.Sections.Item(1)
    $pageWidth = $sec.PageSetup.PageWidth
    $pageHeight = $sec.PageSetup.PageHeight

    foreach ($p in $doc.Paragraphs) {{
        $cleanTxt = $p.Range.Text.Replace([char]1, "").Trim()
        if ($cleanTxt) {{
            $pg = $p.Range.Information(3) # wdActiveEndPageNumber
            if (-not $pagesDict.ContainsKey($pg)) {{
                $pagesDict[$pg] = [System.Collections.Generic.List[hashtable]]::new()
            }}
            $y = [double]$p.Range.Information(5) # wdVerticalPositionRelativeToPage
            $x = [double]$p.Range.Information(6) # wdHorizontalPositionRelativeToPage
            $fontSize = [double]$p.Range.Font.Size
            if ($fontSize -le 0) {{ $fontSize = 12.0 }}
            $lineSpacing = [double]$p.Format.LineSpacing
            if ($lineSpacing -le 0) {{ $lineSpacing = $fontSize * 1.2 }}

            $align = "left"
            if ($p.Alignment -eq 1) {{ $align = "center" }}
            elseif ($p.Alignment -eq 2) {{ $align = "right" }}

            if ($p.InlineShapes.Count -gt 0) {{
                foreach ($ishape in $p.InlineShapes) {{
                    $sStart = $ishape.Range.Start
                    $sEnd = $ishape.Range.End
                    if ($sStart -gt $p.Range.Start) {{
                        $preTxt = $doc.Range($p.Range.Start, $sStart).Text.Replace([char]1, "").Trim()
                        if ($preTxt) {{
                            $pagesDict[$pg].Add(@{{
                                type = "text"
                                x = $x
                                y = $y
                                width = [double]($ishape.Range.Information(6) - $x)
                                height = [double]$lineSpacing
                                text = $preTxt
                                font_size = $fontSize
                                line_spacing = $lineSpacing
                                align = $align
                            }})
                        }}
                    }}
                    if ($sEnd -lt $p.Range.End) {{
                        $postTxt = $doc.Range($sEnd, $p.Range.End).Text.Replace([char]1, "").Trim()
                        if ($postTxt) {{
                            $postX = [double]($ishape.Range.Information(6) + $ishape.Width)
                            $pagesDict[$pg].Add(@{{
                                type = "text"
                                x = $postX
                                y = [double]$ishape.Range.Information(5)
                                width = [double]($pageWidth - $postX - $sec.PageSetup.RightMargin)
                                height = [double]$lineSpacing
                                text = $postTxt
                                font_size = $fontSize
                                line_spacing = $lineSpacing
                                align = $align
                            }})
                        }}
                    }}
                }}
            }} else {{
                $box = @{{
                    type = "text"
                    x = $x
                    y = $y
                    width = [double]($pageWidth - $x - $sec.PageSetup.RightMargin)
                    height = [double]($lineSpacing)
                    text = $cleanTxt
                    font_size = $fontSize
                    line_spacing = $lineSpacing
                    align = $align
                }}
                $pagesDict[$pg].Add($box)
            }}
        }}
    }}

    foreach ($shape in $doc.InlineShapes) {{
        $pg = $shape.Range.Information(3)
        if (-not $pagesDict.ContainsKey($pg)) {{
            $pagesDict[$pg] = [System.Collections.Generic.List[hashtable]]::new()
        }}
        $y = [double]$shape.Range.Information(5)
        $x = [double]$shape.Range.Information(6)
        $imgBox = @{{
            type = "image"
            x = $x
            y = $y
            width = [double]$shape.Width
            height = [double]$shape.Height
        }}
        $pagesDict[$pg].Add($imgBox)
    }}

    try {{
        foreach ($shape in $doc.Shapes) {{
            $pg = $shape.Anchor.Information(3)
            if (-not $pagesDict.ContainsKey($pg)) {{
                $pagesDict[$pg] = [System.Collections.Generic.List[hashtable]]::new()
            }}
            $y = [double]$shape.Top
            $x = [double]$shape.Left
            $imgBox = @{{
                type = "image"
                x = $x
                y = $y
                width = [double]$shape.Width
                height = [double]$shape.Height
            }}
            $pagesDict[$pg].Add($imgBox)
        }}
    }} catch {{}}

    $outPages = @()
    $sortedKeys = $pagesDict.Keys | Sort-Object
    foreach ($k in $sortedKeys) {{
        $outPages += @{{
            page_index = ($k - 1)
            width = $pageWidth
            height = $pageHeight
            boxes = $pagesDict[$k]
        }}
    }}

    $root = @{{
        source_file = {docx_q}
        total_pages = $totalPages
        pages = $outPages
    }}

    $jsonStr = $root | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText({json_q}, $jsonStr, [System.Text.Encoding]::UTF8)
    $doc.Close(0)
}} finally {{
    if ($doc) {{ try {{ $doc.Close(0) }} catch {{}} }}
    $w.Quit(0)
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($w) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}}
"""
        res = cls._run_powershell_script(ps_script, timeout=60)
        if res.returncode != 0:
            raise RuntimeError(f"Lỗi khi trích xuất Word COM: {res.stderr.strip() or res.stdout.strip()}")

    @classmethod
    def convert_to_pdf(cls, docx_path: str, output_pdf_path: str) -> str:
        """Chuyển đổi DOCX thành tệp PDF nền cố định."""
        docx_abs = os.path.abspath(docx_path)
        pdf_abs = os.path.abspath(output_pdf_path)

        if cls.is_word_available():
            docx_q = cls._ps_quote(docx_abs)
            pdf_q = cls._ps_quote(pdf_abs)
            ps_script = f"""
$ErrorActionPreference = 'Stop'
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {{
    $doc = $w.Documents.Open({docx_q})
    $doc.SaveAs2({pdf_q}, 17) # 17 = wdFormatPDF
    $doc.Close(0)
}} finally {{
    if ($doc) {{ try {{ $doc.Close(0) }} catch {{}} }}
    $w.Quit(0)
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($w) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}}
"""
            try:
                res = cls._run_powershell_script(ps_script, timeout=60)
                if res.returncode == 0 and os.path.exists(pdf_abs):
                    return pdf_abs
            except Exception as e:
                _log.warning("Chuyển đổi Word COM thất bại: %s. Thử fallback.", e)

        if cls.is_libreoffice_available():
            out_dir = os.path.dirname(pdf_abs)
            cmd = ["soffice", "--headless", "--convert-to", "pdf", docx_abs, "--outdir", out_dir]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                produced_pdf = os.path.join(out_dir, f"{os.path.splitext(os.path.basename(docx_abs))[0]}.pdf")
                if os.path.exists(produced_pdf) and os.path.abspath(produced_pdf) != pdf_abs:
                    shutil.move(produced_pdf, pdf_abs)
                if os.path.exists(pdf_abs):
                    return pdf_abs

        raise RuntimeError(
            "Fidelity Mode yêu cầu Microsoft Word (Windows) hoặc LibreOffice (Linux/macOS) để kết xuất PDF nền. "
            "Vui lòng cài đặt Microsoft Word hoặc sử dụng chế độ Semantic Mode (--mode semantic)."
        )
