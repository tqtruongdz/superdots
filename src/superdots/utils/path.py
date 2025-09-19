from pathlib import Path

def normalize_path(path: Path, home: Path, expanduser: bool=True) -> Path:
    if path.is_absolute():  # Bắt đầu bằng '/'
        try:
            # Chuyển sang đường dẫn tương đối với home
            path = path.relative_to(home)
        except ValueError:
            # Nếu không thể relative, giữ nguyên đường dẫn tuyệt đối
            return path
    
    norm_path = (Path('~') / path)
    if expanduser:
        norm_path = norm_path.expanduser()
    return norm_path