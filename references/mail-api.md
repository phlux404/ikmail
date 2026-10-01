# Infomaniak Mail API — endpoint reference

Base: `https://mail.infomaniak.com/api`
Auth: `Authorization: Bearer <personal API token>` (needs `workspace:mail` scope)

This is the backend the kMail app / webmail use. Documented here from
community projects (notably `henrikogaard/infomaniak-mcp`'s `mail-api.ts`,
2026-07); treat as semi-stable and verify against live responses.

## Endpoints used by `bin/ikmail.py`

| Operation | Method & path |
|---|---|
| List mailboxes | `GET /mailbox?with=aliases,permissions,accountId,count_users` |
| List folders | `GET /mail/{mailboxUuid}/folder?with=ik-static` |
| List messages (threads) | `GET /mail/{uuid}/folder/{folderId}/message?offset=&thread=on&severywhere=0&limit=` |
| Read message | `GET /mail/{uuid}/folder/{folderId}/message/{uid}?prefered_format=plain\|html&with=auto_uncrypt,thread_context` |
| Download attachment | `GET /mail/{uuid}/folder/{folderId}/message/{uid}/attachment/{attachmentId}` |

Response envelope: `{ result: "success", data: ... }`. Message list returns
`data.threads[]`; each thread has `uid`, `subject`, `from[]`, `date`,
`seen`, `flagged`, `has_attachments`, `messages_count`, `preview`.

## Write endpoints (not implemented — read-only skill)

Kept for reference if write access is ever requested:

| Operation | Method & path |
|---|---|
| Message action (move/spam/seen/unseen/star/unstar) | `POST /mail/{uuid}/message/{action}` body `{uids[], to?}` |
| Create draft | `POST /mail/{uuid}/draft` |
| Upload draft attachment | `POST /mail/{uuid}/draft/attachment` (headers `x-ws-attachment-*`) |
| Update draft | `PUT /mail/{uuid}/draft/{draftUuid}` |

## Notes
- Folder lookup is by name/role; pass `folder_id:<id>` to address by ID.
  Folder IDs are opaque strings — URL-encode them in paths.
- **Verified live 2026-09-26:** `data` is a flat list for mailbox/folder
  lists (not `data.items`); mailbox `aliases` is a list of plain strings;
  message list returns `data.threads[]`; the thread `uid` is opaque — the
  read endpoint needs the numeric message uid (`<uid>@<folderid>` →
  `<uid>`); the read body arrives as `{value, type, subBody}`.
- Personal API tokens are created at
  `manager.infomaniak.com/v3/ng/accounts/token` with the `workspace:mail` scope.
- A 401/403 usually means the token lacks the scope, not a bad token.
