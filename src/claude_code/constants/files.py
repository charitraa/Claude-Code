"""
Binary file extensions and detection
"""

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".tiff", ".tif",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".flv", ".m4v", ".mpeg", ".mpg",
    ".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a", ".wma", ".aiff", ".opus",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz", ".z", ".tgz", ".iso",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a", ".obj", ".lib", ".app", ".msi", ".deb", ".rpm",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".pyc", ".pyo", ".class", ".jar", ".war", ".ear", ".node", ".wasm", ".rlib",
    ".sqlite", ".sqlite3", ".db", ".mdb", ".idx",
    ".psd", ".ai", ".eps", ".sketch", ".fig", ".xd", ".blend", ".3ds", ".max",
    ".swf", ".fla",
    ".lockb", ".dat", ".data",
}

BINARY_CHECK_SIZE = 8192


def has_binary_extension(file_path: str) -> bool:
    """Check if a file path has a binary extension."""
    ext = file_path[file_path.rfind("."):].lower() if "." in file_path else ""
    return ext in BINARY_EXTENSIONS


def is_binary_content(buffer: bytes) -> bool:
    """Check if a buffer contains binary content."""
    check_size = min(len(buffer), BINARY_CHECK_SIZE)
    
    non_printable = 0
    for i in range(check_size):
        byte = buffer[i]
        if byte == 0:
            return True
        if byte < 32 and byte not in (9, 10, 13):
            non_printable += 1
    
    return non_printable / check_size > 0.1 if check_size > 0 else False
