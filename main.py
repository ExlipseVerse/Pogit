import sys, hashlib

# Compute git's "blob" SHA-1 over the content of each input line.
# Format: "blob <byte_len>\0<content>" then SHA-1.


def hash_blob(content: bytes) -> str:
    """Return the 40-char hex SHA-1 git would assign to this content as a blob."""
    header = f"blob {len(content)}\0".encode("ascii")
    # TODO: SHA-1 the concatenation of header + content; return hexdigest().
    return ""


def main():
    # Each input line is one "file's" content (no trailing newline included).
    # Note: the grader expects no trailing newline; use "\n".join(...).
    out = []
    for raw in sys.stdin:
        line = raw.rstrip("\n").encode("utf-8")
        out.append(hash_blob(line))
    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
