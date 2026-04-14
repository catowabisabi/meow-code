"""
REST API routes for file operations (used by code editor).
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/files", tags=["files"])

# --- Pydantic Models ---


class FileEntry(BaseModel):
    name: str
    path: str
    isDirectory: bool
    isFile: bool


class ListFilesResponse(BaseModel):
    path: str
    files: list[FileEntry]


class ReadFileResponse(BaseModel):
    path: str
    content: str
    language: str
    size: int


class WriteFileRequest(BaseModel):
    path: str
    content: str


class WriteFileResponse(BaseModel):
    ok: bool
    path: str


class DirectoryEntry(BaseModel):
    path: str
    label: str


class DirectoriesResponse(BaseModel):
    directories: list[DirectoryEntry]


class ErrorResponse(BaseModel):
    error: str


# --- Helpers ---


def ext_to_language(ext: str) -> str:
    """Map file extension to language identifier."""
    ext_map: dict[str, str] = {
        "ts": "typescript",
        "tsx": "typescript",
        "js": "javascript",
        "jsx": "javascript",
        "py": "python",
        "rb": "ruby",
        "go": "go",
        "rs": "rust",
        "java": "java",
        "c": "c",
        "cpp": "cpp",
        "h": "c",
        "hpp": "cpp",
        "cs": "csharp",
        "json": "json",
        "yaml": "yaml",
        "yml": "yaml",
        "toml": "toml",
        "md": "markdown",
        "html": "html",
        "css": "css",
        "scss": "scss",
        "sh": "shell",
        "bash": "shell",
        "zsh": "shell",
        "ps1": "powershell",
        "sql": "sql",
        "xml": "xml",
        "svg": "xml",
        "vue": "vue",
        "dart": "dart",
        "kt": "kotlin",
        "swift": "swift",
        "r": "r",
        "lua": "lua",
        "php": "php",
        "pl": "perl",
    }
    return ext_map.get(ext, "plaintext")


def _get_subdirs(dir_path: str, max_depth: int = 1) -> list[str]:
    """Get subdirectories of a directory, up to max_depth."""
    try:
        entries = os.listdir(dir_path)
        result = []
        for name in entries:
            if name.startswith(".") or name.startswith("node_modules"):
                continue
            full_path = os.path.join(dir_path, name)
            if os.path.isdir(full_path):
                result.append(full_path)
                if len(result) >= 20:
                    break
        return result[:20]
    except (OSError, PermissionError):
        return []


# --- Routes ---


@router.get("/directories", response_model=DirectoriesResponse)
async def list_directories() -> DirectoriesResponse:
    """Return a list of common project directories."""
    home_dir = os.path.expanduser("~")
    cwd = os.getcwd()

    directories = [
        DirectoryEntry(path=cwd, label=f"專案 ({os.path.basename(cwd)})"),
        DirectoryEntry(path=home_dir, label="主目錄"),
    ]

    # Add subdirectories from cwd and home
    for base_dir in [cwd, home_dir]:
        for subdir in _get_subdirs(base_dir):
            directories.append(
                DirectoryEntry(path=subdir, label=os.path.basename(subdir))
            )

    return DirectoriesResponse(directories=directories)


@router.post("/browse")
async def browse_folder():
    """Open native OS folder picker dialog and return selected path."""
    try:
        if sys.platform == "win32":
            ps_script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
                "$d.Description = 'Select a project folder'; "
                "if ($d.ShowDialog() -eq 'OK') { $d.SelectedPath } else { '' }"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, text=True, timeout=120,
            )
            selected = result.stdout.strip()
        elif sys.platform == "darwin":
            # macOS: use osascript to open Finder folder dialog
            apple_script = (
                'set theFolder to POSIX path of '
                '(choose folder with prompt "Select a project folder")'
            )
            result = subprocess.run(
                ["osascript", "-e", apple_script],
                capture_output=True, text=True, timeout=120,
            )
            selected = result.stdout.strip().rstrip("/")
        else:
            # Linux: try zenity (GTK), then kdialog (KDE)
            selected = ""
            for cmd in [
                ["zenity", "--file-selection", "--directory", "--title=Select a project folder"],
                ["kdialog", "--getexistingdirectory", os.path.expanduser("~"), "--title", "Select a project folder"],
            ]:
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=120,
                    )
                    if result.returncode == 0:
                        selected = result.stdout.strip()
                        break
                except FileNotFoundError:
                    continue

        if not selected:
            return {"cancelled": True}
        return {"path": selected}
    except subprocess.TimeoutExpired:
        return {"cancelled": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=ListFilesResponse)
async def list_files(
    path: Annotated[str | None, Query(description="Directory path to list")] = None,
) -> ListFilesResponse:
    """List files and directories in a given path."""
    dir_path = path if path else os.getcwd()

    try:
        entries = os.scandir(dir_path)
        files: list[FileEntry] = []

        for entry in entries:
            files.append(
                FileEntry(
                    name=entry.name,
                    path=entry.path,
                    isDirectory=entry.is_dir(),
                    isFile=entry.is_file(),
                )
            )

        # Sort: directories first, then files alphabetically
        files.sort(key=lambda f: (not f.isDirectory, f.name))

        return ListFilesResponse(path=dir_path, files=files)

    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/read", response_model=ReadFileResponse)
async def read_file(
    path: Annotated[str, Query(description="File path to read")],
) -> ReadFileResponse:
    """Read file contents with size limit (5MB)."""
    file_path = Path(path)

    if not file_path.exists():
        raise HTTPException(status_code=400, detail="File not found")

    try:
        stat = file_path.stat()
        if stat.st_size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")

        content = file_path.read_text(encoding="utf-8")
        ext = file_path.suffix.lstrip(".").lower()

        return ReadFileResponse(
            path=str(file_path),
            content=content,
            language=ext_to_language(ext),
            size=stat.st_size,
        )

    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/write", response_model=WriteFileResponse)
async def write_file(request: WriteFileRequest) -> WriteFileResponse:
    """Write content to a file, creating directories as needed."""
    if not request.path or request.content is None:
        raise HTTPException(status_code=400, detail="Missing path or content")

    try:
        file_path = Path(request.path)
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(request.content, encoding="utf-8")

        return WriteFileResponse(ok=True, path=request.path)

    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))
