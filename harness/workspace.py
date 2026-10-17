from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil


def safe_path(base, relative):
    name = str(relative).replace("\\", "/")
    posix, windows = PurePosixPath(name), PureWindowsPath(name)
    if posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts:
        raise ValueError(f"unsafe overlay path: {relative}")
    result = (Path(base) / name).resolve()
    if not result.is_relative_to(Path(base).resolve()) or result == Path(base).resolve():
        raise ValueError(f"path escapes workspace: {relative}")
    return result


def copy_tree(source, dest):
    for p in sorted(Path(source).rglob("*")):
        if p.is_symlink():
            raise ValueError(f"symlinks forbidden: {p}")
        target = safe_path(dest, p.relative_to(source))
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif p.name != "__delete__.txt" and "__pycache__" not in p.parts:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, target)


def materialize(starter, overlay, dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=False)
    copy_tree(Path(starter), dest)
    if overlay is not None:
        overlay = Path(overlay)
        deletes = overlay / "__delete__.txt"
        if deletes.exists():
            for relative in deletes.read_text(encoding="utf-8").splitlines():
                if relative.strip():
                    target = safe_path(dest, relative.strip())
                    if Path(relative).parts[0] == "tests":
                        raise ValueError("visible tests must remain")
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink(missing_ok=True)
        for p in overlay.rglob("*"):
            if p.relative_to(overlay).parts[0] == "tests":
                raise ValueError("overlay must not change visible tests")
        copy_tree(overlay, dest)
    return dest
