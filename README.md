# ikmail

Read your Infomaniak mail from the command line. One Python file, standard library only — no dependencies, no package installs, nothing phoning home except Infomaniak's own API.

`ikmail` talks to the same backend the kMail app and webmail use (`https://mail.infomaniak.com/api`). It is **read-only**: list mailboxes and folders, browse message threads, read message bodies, and search. It never sends, moves, deletes, or flags anything.

## Install

```sh
curl -o ikmail.py https://raw.githubusercontent.com/phlux404/ikmail/main/ikmail.py
chmod +x ikmail.py
```

Or just clone the repo. Python 3.8+ is all you need.

## Setup

You need a personal Infomaniak API token with the `workspace:mail` scope:

1. Create one at https://manager.infomaniak.com/v3/ng/accounts/token
2. Give `ikmail` the token in **one** of these ways:

```sh
# Option A: environment variable
export INFOMANIAK_TOKEN=<your token>

# Option B: config file (keep it private)
mkdir -p ~/.config/ikmail
printf '%s' '<your token>' > ~/.config/ikmail/token
chmod 600 ~/.config/ikmail/token
```

The token is only ever sent to `mail.infomaniak.com` as an `Authorization: Bearer` header. It is never printed, logged, or written anywhere by this tool.

## Usage

```
ikmail.py [--json] [--mailbox <email|name|uuid>] <command>
```

`--mailbox` defaults to your primary mailbox. `--json` switches any command to machine-readable output (handy for piping into `jq` or a script).

```sh
# List your mailboxes
ikmail.py mailboxes

# List folders in a mailbox
ikmail.py folders
ikmail.py --mailbox you@example.com folders

# Browse the inbox (threads, newest first)
ikmail.py messages
ikmail.py messages --folder Sent --limit 5

# Read one message (uid comes from the messages output)
ikmail.py read 847
ikmail.py read 847 --format html

# Search a folder
ikmail.py search "invoice"
ikmail.py --json search "invoice" > results.json
```

`--folder` accepts a folder name, path, or role (`INBOX`, `Sent`, …), or `folder_id:<id>` if you already know the internal ID.

## Notes

- The Mail API is thread-based: `messages` returns threads; `read` takes the numeric message uid shown in the listing (a full `uid@folderid` string also works — the part after `@` is stripped).
- A `401`/`403` almost always means the token lacks the `workspace:mail` scope, not that the token is wrong.
- Endpoint details, verified response shapes, and the (unimplemented) write endpoints are documented in [references/mail-api.md](references/mail-api.md). The API is community-documented rather than officially published, so treat it as semi-stable.

## License

MIT — see [LICENSE](LICENSE).
