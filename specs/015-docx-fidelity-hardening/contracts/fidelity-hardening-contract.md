# Interface Contract: DOCX Fidelity Hardening & Surgical Whiteout

**Feature**: `015-docx-fidelity-hardening`  
**Date**: 2026-09-30  
**Status**: Completed  

---

## 1. Converter Availability & Caching API Contract

### `chuviettay.fidelity.converter.FidelityConverter`

```python
class FidelityConverter:
    _word_available_cache: bool | None = None
    _libreoffice_available_cache: bool | None = None

    @classmethod
    def reset_cache(cls) -> None:
        """Reset all availability cache flags to None."""
        ...

    @classmethod
    def is_word_available(cls) -> bool:
        """Check if Microsoft Word COM is available.
        
        Guarantees:
        - Non-Windows: sets cls._word_available_cache = False, returns False.
        - Windows: queries COM via PowerShell once, caches boolean result, returns boolean.
        - Subsequent calls: returns cached boolean value immediately without probing.
        """
        ...

    @classmethod
    def is_libreoffice_available(cls) -> bool:
        """Check if LibreOffice CLI is available.
        
        Guarantees:
        - Probes system PATH once, caches boolean result, returns boolean.
        - Subsequent calls: returns cached boolean value immediately.
        """
        ...

    @classmethod
    def _run_powershell_script(
        cls, script_content: str, timeout: int = 60
    ) -> subprocess.CompletedProcess[str]:
        """Execute a PowerShell script using a temporary .ps1 file.
        
        Guarantees:
        - Must invoke with shell=False (avoiding cmd.exe shell intermediary).
        - Pass arguments as list: ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script_path]
        - Clean up temporary .ps1 file in finally block.
        """
        ...
```

---

## 2. Whiteout Generator Contract

### `chuviettay.fidelity.background.WhiteoutBackgroundGenerator`

```python
class WhiteoutBackgroundGenerator:
    @classmethod
    def create_whiteout_docx(
        cls, docx_path: str, output_path: str | None = None
    ) -> str:
        """Produce a whiteout DOCX where text runs are whitened and non-text parts are preserved verbatim.
        
        Parameters:
            docx_path: Absolute or relative path to the existing input DOCX file.
            output_path: Optional destination path. If None, creates a temporary file.
            
        Returns:
            str: Path to the generated whiteout DOCX file.
            
        Preconditions:
            - docx_path must exist and be a valid ZIP archive.
            
        Postconditions:
            - Returns path to valid DOCX ZIP package.
            - All non-XML files (images, media, embeddings, fonts) in the output ZIP have identical SHA256 checksums to the input.
            - All text runs (<w:r> and <a:r>) in target XML parts have color set to #FFFFFF.
            - On error, raises RuntimeError and cleans up partially written temporary files.
        """
        ...
```

---

## 3. GUI Mode Controller Contract

### `chuviettay.view.write_tab.WriteTab`

```python
class WriteTab:
    cb_mode: ttk.Combobox
    cb_paper: ttk.Combobox
    btn_paper_custom: ttk.Button
    cb_ori: ttk.Combobox
    cb_bg: ttk.Combobox
    entry_spacing: ttk.Entry

    def _on_mode_changed(self, event=None) -> None:
        """Handle DOCX mode changes between Semantic and Fidelity.
        
        Behavior:
        - If v_mode is "Khóa bố cục & ảnh (Fidelity)":
            - cb_paper.configure(state="disabled")
            - btn_paper_custom.configure(state="disabled")
            - cb_ori.configure(state="disabled")
            - cb_bg.configure(state="disabled")
            - entry_spacing.configure(state="disabled")
        - If v_mode is "Tự do (Semantic)":
            - cb_paper.configure(state="readonly")
            - btn_paper_custom.configure(state="normal")
            - cb_ori.configure(state="readonly")
            - cb_bg.configure(state="readonly")
            - entry_spacing.configure(state="normal")
        """
        ...
```
