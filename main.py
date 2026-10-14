import sys
import zlib
import hashlib
from pathlib import Path


def init():
    # get the current working directory
    base_dir = Path.cwd() / ".git"

    subfolders = [
        base_dir / "objects",
        base_dir / "refs",
        base_dir / "refs" / "heads",
        base_dir / "refs" / "tags"
    ]

    for folder in subfolders:
        folder.mkdir(parents=True, exist_ok=True)

    head_file = base_dir / "HEAD"
    head_file.write_text("ref: refs/heads/main\n")

    print("Initialized git directory")

def create_blob(data: bytes):
    header = f"blob {len(data)}\x00".encode('ascii')
    full_bytes = header + data
    return full_bytes

def obj_hash(obj_data: bytes):
    sha = hashlib.sha1(obj_data).hexdigest()
    return sha

def write_obj(obj_data: bytes, obj_hash: str):
    fol_name, rest = obj_hash[:2], obj_hash[2:]
    obj_path = Path.cwd() / ".git" / "objects" / fol_name / rest
    try:
        compressed_data = zlib.compress(obj_data)
    except zlib.error:
        print("failed to compress data")
        return
    
    obj_path.parent.mkdir(parents=True, exist_ok=True)
    obj_path.write_bytes(compressed_data)

def dissect_any_obj(obj_data: bytes):
    if obj_data is None:
        return None

    parts = obj_data.split(b"\x00", 1)
    if len(parts) < 2:
        return None
    
    header_bytes, payload_bytes = parts[0], parts[1]

    try:
        header_str = header_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return None

    header_parts = header_str.split(" ", 1)
    if len(header_parts) < 2:
        return None

    obj_type, size_str = header_parts[0], header_parts[1]

    try:
        expected_size = int(size_str)
    except ValueError:
        return None

    if len(payload_bytes) != expected_size:
        return None

    return obj_type, expected_size, payload_bytes

def dissect_obj(obj_data: bytes):
    res = dissect_any_obj(obj_data)
    if res and res[0] == "blob":
        return res[2]
    return None

def read_obj(obj_hash):
    fl = obj_hash[:2]
    rl = obj_hash[2:]

    obj_path = Path.cwd() / ".git" / "objects" / fl / rl

    if obj_path.exists():
        try:
            compressed_data = obj_path.read_bytes()
            return zlib.decompress(compressed_data)
        except Exception:
            return None
    else:
        return None

def parse_tree_entry(data: bytes):
    parts = data.split(b"\x00", 1)
    if len(parts) < 2: return None

    left_part, right_part = parts[0], parts[1]

    mode_name = left_part.split(b" ", 1)
    if len(mode_name) < 2: return None

    if len(right_part) < 20:
        return None

    mode = mode_name[0].decode("utf-8")
    name = mode_name[1].decode("utf-8")
    object_id = right_part[:20]
    rest = right_part[20:]

    return mode, name, object_id, rest

def parse_git_tree(payload: bytes):
    entries = []
    rest = payload
    while rest:
        result = parse_tree_entry(rest)
        if result is None:
            raise ValueError("Malformed tree data: failed to parse tree entry.")

        mode, name, obj_id, rest = result

        entries.append((mode,name,obj_id))

    return entries

def main():
    args = sys.argv[1:]

    if not args:
        return

    if args[0] == "init":
        init()
        return
    
    if args[0] == "cat-file" or args[0] == "read":
        if len(args) < 2:
            return
        
        obj_bytes = read_obj(args[1])
        dissected = dissect_obj(obj_bytes)
        if dissected is not None:
            print(dissected)
    
    if args[0] == "hash-object":
        if len(args) < 3:
            return
        mode = args[1]
        if not mode == "-w": return

        p = args[2]
        try:
            with open(p, "rb") as file:
                content = file.read()
                blob = create_blob(content)
                hashed = obj_hash(blob)
                write_obj(blob, hashed)
                print(hashed)
        except FileNotFoundError:
            print(f"Error: The file '{p}' does not exist.")

    if args[0] == "ls-tree":
        if len(args) < 2:
            return
        t_hash = args[1]
        raw_obj = read_obj(t_hash)
        dissected_res = dissect_any_obj(raw_obj)
        if not dissected_res:
            return
            
        obj_type, _, payload = dissected_res
        if obj_type != "tree":
            return
            
        parsed_entries = parse_git_tree(payload)

        for mode, name, obj_id in parsed_entries:
            hex_hash = obj_id.hex()
            resolved_type = "tree" if mode in ("40000", "040000") else "blob"
            print(f"{mode.zfill(6)} {resolved_type} {hex_hash}\t{name}")


if __name__ == "__main__":
    main()