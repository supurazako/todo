# Design provenance

Visual source: https://github.com/tokuzou0829/my-todo-app
Reference commit: `45fa18614334bac119165d8fc28d98a20cc108c3`

The owner reports direct permission from author tokuzou0829 to use the app and its design.
This records that reported permission, not a new license grant for third parties.
Do not infer unrestricted redistribution rights from this document.

Adapted into plain HTML/CSS/JavaScript:
- `app/globals.css`: lime primary #84cc16, pale-lime accent #ecfccb, zinc text/borders.
- `components/site-header.tsx`: inset rounded sidebar, active navigation and account panel.
- `components/todo-app.tsx`: bordered task rows, lime hover/checked state and rounded controls.
- `components/finance-app.tsx`: month navigation, income/expense/net metrics, entry list and modal input.

The lightweight version does not bundle Next.js, React, Tailwind, PostgreSQL,
Recharts, R2, Better Auth or Web Push. It is not a pixel-identical copy and does
not include the upstream app's complete feature set, fonts, icons or branding assets.

The later design request supersedes the original blue Apple-inspired direction.
Both TODO and finance are visible to holders of the existing viewer key; writes
remain owner-only. Finance amounts are positive whole JPY, with income/expense
stored separately. Net is monthly income minus expense, not bank balance.
