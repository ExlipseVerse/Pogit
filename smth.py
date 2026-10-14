import sys, hashlib
from typing import Tuple
# Compute git's "blob" SHA-1 over the content of each input line.
# Format: "blob <byte_len>\0<content>" then SHA-1.
store = {}
VALID_TYPES={"blob", "tree", "commit", "tag"}
AUTHOR = "user <user@example.com> 0 +0000"

def hash(otype: str, content: bytes) -> Tuple[str, bytes]:
    """Return the 40-char hex SHA-1 git would assign to this content as a blob."""
    
    header = f"{otype} {len(content)}\0".encode("ascii")
    full_bytes = header + content
    sha = hashlib.sha1(full_bytes).hexdigest()
    return sha, full_bytes

def parse_obj(raw_bytes: bytes):
    sep=b"\x00"

    if not isinstance(raw_bytes, bytes):
        raw_bytes = bytes(raw_bytes)

    if sep not in raw_bytes:
        return "ERR no NUL separator"
    
    nul_index = raw_bytes.index(sep)
    header_bytes = raw_bytes[:nul_index]
    payload_bytes = raw_bytes[nul_index + len(sep):]

    if header_bytes.count(b' ') != 1:
        return "ERR invalid header"

    header_parts = header_bytes.split(b' ')

    try:
        obj_ty = header_parts[0].decode("ascii")
        size = header_parts[1].decode("ascii")
    except (UnicodeDecodeError, IndexError):
        return "ERR header is not valid ASCII"

    if obj_ty not in VALID_TYPES:
        return f"ERR unknown type {obj_ty}"

    try:
        declared_size = int(size)
    except ValueError:
        return "ERR size is not an integer"

    actual_size = len(payload_bytes)
    if declared_size!=actual_size:
        return "ERR size mismatch"

    return f"{obj_ty} {payload_bytes.decode('utf-8', errors='replace')}"


def cat_dispatcher(flag, sha):
    # TODO: handle each flag
            #   -e -> "ok" if exists else "missing"
            #   -t -> object type (or "fatal: not a valid object name <sha>")
            #   -s -> byte length of body (utf-8)
            #   -p -> body, verbatim

    if flag == "-e":
        return "ok" if sha in store else "missing"

    if sha not in store:
        return f"fatal: not a valid object name {sha}"

    otype, body = store[sha]

    if flag == "-t":
        return otype
    elif flag == "-s":
        return str(len(body.encode('utf-8')))
    elif flag == "-p":
        return body

    return "ERR invalid flag"
    

# Parse a packfile's 12-byte header and validate it.
# Header layout (big-endian):
#   bytes 0-3:  magic "PACK"
#   bytes 4-7:  version (uint32) — supported: 2 or 3
#   bytes 8-11: object count (uint32)

def parse_packfile_header(header: bytes):
    if len(header) < 12:
        return "ERR truncated"

    try:
        magic = header[0:4].decode('ascii')
    except UnicodeDecodeError:
        return "ERR bad magic"
    
    if magic != "PACK":
        return "ERR bad magic"
    
    version = int.from_bytes(header[4:8], byteorder='big')
    if version not in (2, 3):
        return f"ERR unsupported version {version}"
    
    count = int.from_bytes(header[8:12], byteorder='big')
    
    return f"PACK v{version} count={count}"

# def find_lcp_mistake():
#     raw = sys.stdin.read()
#     lines = raw.split("\n")
#     if lines and lines[-1] == "":
#         lines.pop()
#     sep_idx = None
#     for i, ln in enumerate(lines):
#         if ln == "---":
#             sep_idx = i
#             break
#     if sep_idx is None:
#         a = lines
#         b = []
#     else:
#         a = lines[:sep_idx]
#         b = lines[sep_idx + 1:]

#     # TODO: build LCS DP table sized (m+1) x (n+1).
#     # TODO: walk the table to produce the edit script:
#     #   ' <line>' for unchanged
#     #   '-<line>' for removed
#     #   '+<line>' for added

#     m=len(a)
#     n=len(b)
#     dp = [[0] * (n+1) for _ in range(m + 1)]
#     for i in range(1, m+1):
#         for j in range(1, n +1):
#             if a[i-1] == b[j-1]:
#                 dp[i][j] = dp[i-1][j-1] +1
#             else:
#                 dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
#     out = []
#     i=m
#     j=n

#     while i>0 or j >0:
#         if i>0 and j>0 and a[i-1] == b[j-1]:
#             out.append(f" {a[i-1]}")
#             i -= 1
#             j -= 1
#         elif j>0 and (i==0 or dp[i][j -1] >= dp[i-1][j]):
#             out.append(f"+{b[j-1]}")
#             j -=1
#         else:
#             out.append(f"-{a[i-1]}")
#             i -= 1
    
#     out.reverse()
#     sys.stdout.write("\n".join(out))


def parse_section(lines, idx, header):
    assert lines[idx] == header
    idx += 1
    cnt = int(lines[idx]); idx += 1
    m = {}
    for _ in range(cnt):
        parts = lines[idx].split(" ", 1)
        m[parts[0]] = parts[1]
        idx += 1
    return m, idx


# def slime_main():
    # work = {}        # name -> content (str)
    # index = {}       # name -> blob_sha
    # head_tree = {}   # name -> blob_sha (last commit's tree)
    # refs = {}        # ref_name -> commit_sha
    # head_branch = "refs/heads/main"
    # commits = {}     # sha -> (tree_sha, parents, message)
    # out = []

    # for raw in sys.stdin:
    #     line = raw.rstrip("\n")
    #     if not line:
    #         continue
    #     if line.startswith("WRITE "):
    #         _, rest = line.split(" ", 1)
    #         name, _, content = rest.partition(" ")
    #         work[name] = content
    #     elif line.startswith("ADD "):
    #         name = line.split(" ", 1)[1]
    #         # TODO: hash the file's content as a blob; update INDEX.
    #         working_file = work[name].encode('utf-8')
    #         f_sha, full_bytes = hash("blob", working_file)

    #         store[f_sha] = full_bytes
    #         index[name] = f_sha

    #     elif line.startswith("COMMIT "):
    #         msg = line.split(" ", 1)[1]
    #         # TODO: build a tree object from INDEX (sorted by name; mode 100644),
    #         # build a commit with the previous HEAD as parent (if any),
    #         # update refs[head_branch] and head_tree, print the new commit sha.
    #         tree_b = b""
    #         for name in sorted(index):
    #             entry_header = f"100644 {name}\x00".encode('ascii')
    #             binary_sha = bytes.fromhex(index[name])
    #             tree_b += entry_header + binary_sha

    #         tree_sha, tree_bytes = hash("tree", tree_b)
    #         store[tree_sha] = tree_bytes

    #         commit_payload = f"tree {tree_sha}\n"

    #         parent_sha = refs.get(head_branch)
    #         if parent_sha:
    #             commit_payload += f"parent {parent_sha}\n"

    #         commit_payload += f"author {AUTHOR}\n"
    #         commit_payload += f"committer {AUTHOR}\n\n{msg}"

    #         new_commit_sha, commit_bytes = hash("commit", commit_payload.encode('utf-8'))
    #         store[new_commit_sha] = commit_bytes
    #         commits[new_commit_sha] = (tree_sha, parent_sha, msg)
    #         refs[head_branch] = new_commit_sha
    #         head_tree = dict(index)

    #         out.append(new_commit_sha)


    #     elif line == "LOG":
    #         # TODO: walk parents from HEAD, printing "<sha> <msg>".
    #         curr = refs.get(head_branch)
    #         while curr:
    #             tree_sha, parent_sha, msg = commits[curr]
    #             out.append(f"{curr} {msg}")
    #             if parent_sha:
    #                 curr = parent_sha
    #             else:
    #                 curr = None

    #     elif line == "STATUS":
    #         # TODO: emit three groups (sorted by name within each):
    #         #   "staged: <name>"     INDEX[n] != HEAD_TREE[n]   (incl. presence)
    #         #   "modified: <name>"   WORK[n]'s blob_sha != INDEX[n]
    #         #   "untracked: <name>"  in WORK, not in INDEX
    #         staged_list = []
    #         modified_list = []
    #         untracked_list = []

    #         all_staged_keys = set(index.keys()) | set(head_tree.keys())
    #         for name in sorted(all_staged_keys):
    #             if index.get(name) != head_tree.get(name):
    #                 if name in index:
    #                     staged_list.append(f"staged: {name}")

    #         for name in sorted(index.keys()):
    #             if name in work:
    #                 disk_sha, _ = hash("blob", work[name].encode('utf-8'))
    #                 if disk_sha != index[name]:
    #                     modified_list.append(f"modified: {name}")

    #         for name in sorted(work.keys()):
    #             if name not in index:
    #                 untracked_list.append(f"untracked: {name}")

    #         if staged_list:
    #             out.extend(staged_list)
    #         if modified_list:
    #             out.extend(modified_list)
    #         if untracked_list:
    #             out.extend(untracked_list)

    # sys.stdout.write("\n".join(out))


def main():
    commits = {}  # sha -> (ts, parents)
    queries = []
    for raw in sys.stdin:
        line = raw.rstrip("\n")
        if not line:
            continue
        if line.startswith("COMMIT "):
            parts = line.split(" ")
            sha = parts[1]
            ts = int(parts[2])
            ps = [p for p in parts[3:] if p != "-"]
            commits[sha] = (ts, ps)
        elif line.startswith("BASE "):
            parts = line.split(" ")
            queries.append((parts[1], parts[2]))

    def ancestors(sha):
        # TODO: BFS/DFS from sha following parents; return set including sha itself.
        seen=set()
        stack=[sha]
        while stack:
            c = stack.pop()
            if c in seen: continue

            seen.add(c)
            stack.extend(commits[c][1])
        return seen

    out = []
    
    for a, b in queries:
        strictly_older_ancestors = set()

        anc_a = ancestors(a)
        anc_b = ancestors(b)
        common = anc_a & anc_b
        
        if not common:
            out.append("NONE")
            continue
        
        
        for d in common:
            d_history = ancestors(d) - {d}
            strictly_older_ancestors.update(d_history)

        best_candidates = [c for c in common if c not in strictly_older_ancestors]

        best_candidates.sort()

        if best_candidates:
            out.append(best_candidates[0])
        else:
            out.append("NONE")
            
    sys.stdout.write("\n".join(out))

if __name__ == "__main__":
    main()