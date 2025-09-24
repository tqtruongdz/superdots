from pathlib import Path
from typing import Optional

def normalize_path(path: Path, home: Optional[Path] = None, expanduser: bool=True) -> Path:
    if not home:
        home = Path.home()
    if path.is_absolute():  # Bắt đầu bằng '/'
        try:
            # Chuyển sang đường dẫn tương đối với home
            path = path.relative_to(home)
        except ValueError:
            # Nếu không thể relative, giữ nguyên đường dẫn tuyệt đối
            return path
    path = (Path('~') / path)
    if expanduser:
        path = path.expanduser()
    return path 