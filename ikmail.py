#!/usr/bin/env python3
"""ikmail - read Infomaniak mail via the Mail API (mail.infomaniak.com/api).

Read-only: mailboxes, folders, message lists, message bodies, search.
Python 3, standard library only - no dependencies, no API keys services.

Auth: a personal Infomaniak API token (scope `workspace:mail`), supplied via
the INFOMANIAK_TOKEN environment variable or ~/.config/ikmail/token.
The token is only ever sent to mail.infomaniak.com, never printed or logged.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = "https://mail.infomaniak.com/api"
TOKEN_ENV = "INFOMANIAK_TOKEN"
TOKEN_FILE = os.path.expanduser("~/.config/ikmail/token")


def get_token():
    tok = os.environ.get(TOKEN_ENV, "").strip()
    if tok:
        return tok
    try:
        with open(TOKEN_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        pass
    sys.stderr.write(
        "error: no Infomaniak API token found.\n"
        f"Create a token (scope: workspace:mail) at\n"
        "  https://manager.infomaniak.com/v3/ng/accounts/token\n"
        f"then either:\n"
        f"  export {TOKEN_ENV}=<your token>\n"
        f"or save it (chmod 600) in {TOKEN_FILE}\n")
    sys.exit(2)


def api(path, timeout=60):
    req = urllib.request.Request(
        BASE + path,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {get_token()}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:2000]
        sys.stderr.write(f"error: Mail API {e.code} {e.reason}\n{body}\n")
        sys.exit(1)
    except urllib.error.URLError as e:
        sys.stderr.write(f"error: network: {e.reason}\n")
        sys.exit(1)
    if not isinstance(payload, dict) or payload.get("result") == "error":
        err = payload.get("error", {}) if isinstance(payload, dict) else {}
        sys.stderr.write(f"error: Mail API error: {err.get('description', payload)}\n")
        sys.exit(1)
    return payload


def q(s):
    return urllib.parse.quote(str(s), safe="")


def get_mailboxes():
    return api("/mailbox?with=aliases,permissions,accountId,count_users").get("data") or []


def find_mailbox(ref):
    """ref: email address, mailbox name, or uuid."""
    ref = (ref or "").strip().lower()
    boxes = get_mailboxes()
    if not boxes:
        sys.stderr.write("error: no mailboxes found\n")
        sys.exit(1)
    if not ref:
        prim = [b for b in boxes if b.get("is_primary")]
        return (prim or boxes)[0]
    for b in boxes:
        if (b.get("email") or "").lower() == ref or (b.get("mailbox") or "").lower() == ref \
                or (b.get("uuid") or "").lower() == ref:
            return b
    sys.stderr.write(f"error: no mailbox matching '{ref}'\n")
    sys.exit(1)


def get_folders(uuid):
    return api(f"/mail/{q(uuid)}/folder").get("data") or []


def resolve_folder_id(uuid, folder):
    """folder: name/role (e.g. inbox), or folder_id:<id>."""
    folder = (folder or "inbox").strip()
    if folder.lower().startswith("folder_id:"):
        return folder.split(":", 1)[1]
    folders = get_folders(uuid)
    want = folder.lower()
    for f in folders:
        if (f.get("name") or "").lower() == want or (f.get("role") or "").lower() == want \
                or (f.get("path") or "").lower() == want:
            return f["id"]
    sys.stderr.write(f"error: no folder matching '{folder}'\n")
    sys.exit(1)


def get_messages(uuid, folder_id, limit=20, offset=0, query=None):
    params = {
        "limit": str(limit),
        "offset": str(offset),
        "thread": "on",
        "severywhere": "0",
    }
    if query:
        params["search"] = query
    return api(
        f"/mail/{q(uuid)}/folder/{q(folder_id)}/message?{urllib.parse.urlencode(params)}"
    ).get("data", {})


def fmt_addrs(addrs):
    out = []
    for a in addrs or []:
        name, email = a.get("name") or "", a.get("email") or ""
        out.append(f"{name} <{email}>" if name else email)
    return "; ".join(out)


def cmd_mailboxes(args):
    for b in get_mailboxes():
        row = {
            "uuid": b.get("uuid"),
            "email": b.get("email"),
            "mailbox": b.get("mailbox"),
            "is_primary": b.get("is_primary"),
            "aliases": b.get("aliases") or [],
            "unseen": None,
        }
        print(json.dumps(row) if args.json else f"{b.get('email')}  (uuid {b.get('uuid')})")


def cmd_folders(args):
    b = find_mailbox(args.mailbox)
    folders = get_folders(b["uuid"])
    if args.json:
        print(json.dumps(folders))
        return
    for f in folders:
        print(f"{f.get('name'):<12} role={f.get('role') or '-':<8} "
              f"total={f.get('total_count')} unread={f.get('unread_count')}")


def cmd_messages(args):
    b = find_mailbox(args.mailbox)
    fid = resolve_folder_id(b["uuid"], args.folder)
    data = get_messages(b["uuid"], fid, limit=args.limit, offset=args.offset, query=args.query)
    threads = data.get("threads", [])
    if args.json:
        print(json.dumps(threads))
        return
    for t in threads:
        flags = []
        if t.get("unseen_messages"):
            flags.append("UNSEEN")
        if t.get("has_attachments"):
            flags.append("ATTACH")
        flag = (" [" + ",".join(flags) + "]") if flags else ""
        inner = t.get("messages") or []
        ruid = (inner[0].get("uid", "").split("@", 1)[0]) if inner else ""
        print(f"{t.get('date', '')[:16]}  {fmt_addrs(t.get('from'))}")
        print(f"  {t.get('subject')}{flag}")
        print(f"  uid={ruid}")
        print()


def cmd_read(args):
    b = find_mailbox(args.mailbox)
    fid = resolve_folder_id(b["uuid"], args.folder)
    # Accept a thread/message uid ("847@folderid") or the plain numeric uid.
    uid = args.uid.split("@", 1)[0]
    m = api(f"/mail/{q(b['uuid'])}/folder/{q(fid)}/message/{q(uid)}"
            f"?prefered_format={args.format}&with=auto_uncrypt,thread_context").get("data", {})
    if args.json:
        print(json.dumps(m))
        return
    print(f"From: {fmt_addrs(m.get('from'))}")
    print(f"To: {fmt_addrs(m.get('to'))}")
    if m.get("cc"):
        print(f"Cc: {fmt_addrs(m.get('cc'))}")
    print(f"Date: {m.get('date')}")
    print(f"Subject: {m.get('subject')}")
    atts = m.get("attachments") or []
    if atts:
        print(f"Attachments: {', '.join(a.get('name', '?') for a in atts)}")
    print("-" * 60)
    body = m.get("body")
    text = body.get("value") if isinstance(body, dict) else body
    print(text or "(no body in this format)")


def main():
    p = argparse.ArgumentParser(description="Read Infomaniak mail (read-only)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output")
    common.add_argument("--mailbox", default="", help="email, name, or uuid (default: primary)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("mailboxes", parents=[common], help="list mailboxes")
    sub.add_parser("folders", parents=[common], help="list folders of a mailbox")

    pm = sub.add_parser("messages", parents=[common], help="list message threads in a folder")
    pm.add_argument("--folder", default="inbox")
    pm.add_argument("--limit", type=int, default=20)
    pm.add_argument("--offset", type=int, default=0)
    pm.add_argument("--query", default="", help="search string (same as search)")

    pr = sub.add_parser("read", parents=[common], help="read one message body")
    pr.add_argument("uid", help="message uid (from messages output)")
    pr.add_argument("--folder", default="inbox")
    pr.add_argument("--format", choices=["plain", "html"], default="plain",
                    help="body format (default: plain)")

    ps = sub.add_parser("search", parents=[common], help="search messages in a folder")
    ps.add_argument("query")
    ps.add_argument("--folder", default="inbox")
    ps.add_argument("--limit", type=int, default=20)

    args = p.parse_args()
    {"mailboxes": cmd_mailboxes, "folders": cmd_folders, "messages": cmd_messages,
     "read": cmd_read, "search": lambda a: cmd_messages(
         argparse.Namespace(**{**vars(a), "query": a.query, "offset": 0}))}[args.cmd](args)


if __name__ == "__main__":
    main()
