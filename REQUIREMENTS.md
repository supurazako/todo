# TODO Web — 初版要件

## Updated access policy
- Owner explicitly approved public, login-free access to all TODOs and finance entries/summaries.
- Writes remain owner-authenticated; no anonymous create/edit/complete/delete.
- Owner login is optional, reached from sidebar; logout restores public viewing.
- Send noindex/nofollow/noarchive directives without claiming privacy or access control.
- These updates supersede prior requirements for viewer keys and anonymous read denial below.

## 合意済み
- URL: https://task.supurazako.com
- Repository: supurazako/todo (private)
- Host: the PC running Chronos; no high-availability requirement.
- Owner: create, edit, complete, delete TODOs on the web.
- Viewers: one shared viewer key, read all open and completed TODOs; no writes.
- Separate owner and viewer keys; keys never in URLs; revocable sessions after key rotation.
- Persistent storage shared with the existing 08:00 Asia/Tokyo Discord reminder.
- Responsive UI, white background, lime accents, rounded inset sidebar and finance summary cards adapted from tokuzou0829/my-todo-app (see DESIGN_SOURCE.md). This supersedes the initial blue Apple-inspired visual direction.
- Household finance: JPY income/expense entries (date, description, positive integer amount), create/edit/delete, monthly income/expense/net totals.
- Existing viewer key reads all TODOs and all finance records; only the owner can edit. No separate finance authentication.
- Keyboard access, visible focus, readable contrast; minimal motion.
- Out of scope: due dates, priority, recurrence, categories, per-item visibility, individual viewer accounts.

## Integration discovered
Existing Chronos TODO storage uses SQLite table `todo_items`:
`todo_id`, `task`, `status` (`open` or `completed`), `created_at`, `completed_at`.
The reminder reads open rows ordered by `todo_id` from the calendar-owner database.
Use this store directly rather than maintaining a second copy. Never commit database contents or credentials.
The owner permits breaking changes to existing TODO processing; backward compatibility is not an acceptance requirement. Preserve existing TODO data unless deletion is explicitly approved, and retain the agreed daily reminder behavior. A different storage design may be selected if it simplifies the implementation; any required migration must be verified. Changes to the bot repository still require its owner-approval proposal workflow.

## Deployment candidate (not configured)
Loopback-only application behind Cloudflare Tunnel. cloudflared is installed;
existing tunnel routing, authorization and service configuration still require inspection.
Do not replace existing routes or expose the database over HTTP.

## Acceptance checks
- Anonymous requests cannot read TODOs or mutate data.
- Viewer sessions cannot mutate data, including direct API requests.
- Owner CRUD persists across application restarts and appears in reminder queries.
- User input renders as text, not executable markup.
- Cross-origin mutation attempts are rejected; login sessions use secure cookie settings for production.
- No key or TODO data is committed to Git.
- Verify application locally before enabling external routing, then verify HTTPS at the exact hostname.
