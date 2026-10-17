# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Heaven Ticket Shop Bot — a Discord shop/support-ticket bot written with discord.py 2.7 (Python 3.14, Windows). The code lives in `main.py`. Owner-editable IDs, texts, images and colors live in `shop_settings.py`. All user-facing strings are Thai.

`คู่มือ_Heaven_Ticket.md` is the owner's Thai manual. It covers where each setting lives, adding products, the rental/new-server checklist, troubleshooting, and known limitations (section 10). Keep it in sync when settings, behavior, or known issues change. `main.py` has a numbered Thai table of contents at the top and matching `# ===== N. ...` section headers, so update both when adding a section.

## Commands

```powershell
.\.venv\Scripts\Activate.ps1      # activate venv
python main.py                     # run the bot (needs DISCORD_TOKEN in .env)
```

- Install dependencies: `pip install -r requirements.txt`. There is no test suite or linter.
- Testing is manual in a Discord server: restart the bot after every edit, then walk the full lifecycle (open → Claim → Close → summary → reopen → Close again).
- Slash commands (`/ping`, `/panel`) are globally synced in `setup_hook` on every start.

## Architecture

**Settings file:** `shop_settings.py` is imported as `settings`. It holds the guild IDs (`TICKET_CATEGORY_ID`, `CLOSED_CATEGORY_ID`, `SUPPORT_ROLE_ID`, `LOG_CHANNEL_ID`), the `PRODUCTS` list, and every customer-facing text, image URL and color: panel, support button, review, welcome, notice, order details, and summary/DM. The owner edits this file by hand and restarts the bot. Configuration through Discord commands was tried and rejected.
- Adding a setting means adding it to `shop_settings.py` (with a Thai comment) and to the matching list in `main.py` (`SETTING_TEXT_LIMITS` / `_IDS` / `_IMAGE_URLS` / `_COLORS` / `_EMOJIS`).
- `check_shop_settings()` runs at import. It strips `"""` padding, checks Discord length limits, URLs, colors and IDs, and raises one `RuntimeError` listing every problem.
- Empty optional texts and URLs mean "omit". Use `value or None` for embed titles and descriptions, and `if value:` before `set_image` / `set_footer`.
- `ORDER_DETAILS_TITLE` stays in `main.py` on purpose. The summary step finds the order embed by that exact title, so it must not be made editable.
- Ticket-button permission checks are "member has the support role", duplicated inline in each callback. `/panel` requires Manage Server.

**Products:** `settings.PRODUCTS` is a list of dicts. `check_products()` validates each one, rejecting unknown keys (typos), bad ids, more than 5 questions, and duplicate `field_name`s. It stores stripped copies in `PRODUCTS_BY_ID`, keeping file order. Runtime code reads products only from `PRODUCTS_BY_ID`, never from `settings.PRODUCTS`.
- Each product becomes a `ProductButton` on the panel. This is a `DynamicItem` with template `heaven:buy_<id>`, so the legacy ids `heaven:buy_nitro` and `heaven:buy_premium` keep working on already-posted panels. A button for a product that was removed from the file replies "no longer available".
- Clicking a product button opens `ProductOrderModal(product)`, whose questions come from the product. That leads to `OrderConfirmView(answers, owner_id, product)`. The welcome embed uses the product's `welcome_text` and per-product images, falling back to the global `WELCOME_*_URL`.
- No prices are shown, by the owner's decision.

**Support/inquiry:** `SupportButton` (`heaven:support`, always the last button on the panel) checks `find_open_ticket()`, then opens `SupportRequestModal`. The modal is one form with two `discord.ui.Label` rows: a required `Select` over `settings.SUPPORT_TOPICS`, and an optional paragraph `TextInput`. The select stores option indexes, and `check_support_topics()` validates and strips the topic list.
- On submit, the answers `{SUPPORT_FIELD_TOPIC, SUPPORT_FIELD_DETAILS}` go into the same `OrderConfirmView`, with the `SUPPORT_TICKET` pseudo-product, which carries the welcome text and images. Support tickets therefore share the confirm step, double-click guard, one-ticket rule, and ticket lifecycle with product orders.
- Support tickets still show the fixed `🧾 รายละเอียดคำสั่งซื้อ` order-details title, because the summary lookup depends on it.
- New modals should use `discord.ui.Label` (the `TextInput(label=...)` form is deprecated). `ProductOrderModal` still uses the old form, and it works.

**Ticket state has no database.** Open/closed status is the channel's category: `is_ticket_closed(channel)` checks `category_id == CLOSED_CATEGORY_ID`. The owner, the button that opened the ticket, and the claimer live in the channel topic, which also shows to admins in Discord:

```
👤 <@owner> · 📦 <product id>        (product ticket)
👤 <@owner> · 💬 <support topic name> (support ticket)
… · 🙋 <@admin>                       (appended on Claim)
```

- Always go through the helpers: `build_ticket_topic`, `build_claimed_topic`, `get_ticket_owner_id`, `is_ticket_claimed`, `get_ticket_open_category_id`. Don't parse the topic inline.
- The helpers also accept the legacy format `Ticket owner ID: <id> | Claimed by ID: <id>`, including a stale `| Status: …` segment, so tickets created before the change keep working. Legacy tickets reopen into `TICKET_CATEGORY_ID`.
- The topic is set at creation and edited only once, on Claim. Do not add topic or name edits to close/reopen (see rate limits below).

**Per-button categories and channel names:** each product has `"category_id"` and `SUPPORT_CATEGORY_ID` covers all support topics. `0` means `TICKET_CATEGORY_ID`. `CLOSED_CATEGORY_ID` is shared by every button.
- Reopen moves the ticket back to the category returned by `get_ticket_open_category_id()`, using the 📦 product id or 💬 tag in the topic. A removed product falls back to the main category.
- `find_open_ticket()` scans every category in `get_open_category_ids()`.
- Channel names come from `make_channel_name()`: `<channel_name>-<username up to 12 chars>`, with `channel_name` taken from the product or from the chosen support topic. Thai text is allowed.
- `OrderConfirmView` receives the ticket info as `product`, which must carry `category_id`, `channel_name` and `topic_tag`. `check_products()` adds these to products. For support tickets, `SupportRequestModal.on_submit` builds them from `SUPPORT_TICKET` plus the chosen topic.
- After validation, `settings.SUPPORT_TOPICS` is a list of `{"name", "channel_name"}`. Plain strings are still accepted in the file.

**Lifecycle / view flow:**

1. `/panel` (Manage Server only) posts `ShopPanelView`. One open ticket per customer: `find_open_ticket()` (scans the open-ticket category by topic owner ID) is checked on every product button and again in `OrderConfirmView.confirm`. Product button → `ProductOrderModal` → ephemeral `OrderConfirmView` → creates a `<channel_name>-<user>` channel in that button's category, posts `TicketControlView` (Close + Claim) and an order embed titled `🧾 รายละเอียดคำสั่งซื้อ` (the summary step later finds this embed by exact title in channel history).
2. Claim → appends `· 🙋 <@admin>` to the topic via `build_claimed_topic()`.
3. Close → `CloseConfirmView.confirm_close`: locks owner's send permission, moves to closed category (no rename/topic change), strips old control buttons (by `custom_id` `heaven:close_ticket` / `heaven:claim_ticket`), posts `ClosedTicketView`.
4. Summary → `TicketSummaryModal`: posts summary in ticket, sends combined embed to the log channel and DM to customer, then posts `DeleteTicketView` (Reopen + Delete).
5. Reopen → moves back to the ticket's own open category (`get_ticket_open_category_id`) with `sync_permissions=True`, restores owner perms, posts `ReopenedTicketView` (Close only — no Claim on reopen, by design).
6. Delete → `DeleteTicketConfirmView` → 10s countdown with `CancelDeleteView` → `channel.delete()`.

## Known pitfalls

- **Persistent views:** `ShopPanelView`, `TicketControlView`, `ClosedTicketView`, `DeleteTicketView`, and `ReopenedTicketView` are registered via `add_view` in `ShopBot.setup_hook` so their buttons survive restarts. They must keep no-arg constructors and derive channel/owner from `interaction.channel` and `get_ticket_owner_id()`. Ephemeral confirm views (`CloseConfirmView`, `DeleteTicketConfirmView`, `CancelDeleteView`, `OrderConfirmView`) are intentionally non-persistent.
- **Rate limits on `channel.edit`:** Discord allows only ~2 name/topic changes per channel per 10 minutes. Previously close/reopen also renamed and rewrote the topic, causing ~400–560s 429 waits and expired interactions. Keep close/reopen to category moves only, and `defer()` before any `channel.edit` so the 3-second interaction deadline can't expire.
- **Concurrency guard:** state-changing ticket actions (Claim, confirm close, reopen, summary submit, confirm delete) are wrapped in `run_ticket_action()`, a per-channel busy set that rejects a second admin while one is in progress. The decorated callback is a thin wrapper and the body lives in a `do_*` method. New state-changing buttons should follow the same pattern. The in-memory set resets on restart.
- **Discord embed limits:** a field value holds at most 1024 characters, a description at most 4096, and a whole embed at most 6000. Put customer answers into embeds only through `add_answer_fields()`, which shares the remaining budget across fields and truncates with a marker only when needed. Clip other free text with `shorten()`. The summary embed sets its description last, sized to what remains. The admin summary input is capped at 1000 characters.
- **Summary DM de-dup:** `dm_sent_rounds` (in memory, keyed by the "สรุปข้อมูล" message id) prevents a second DM when an admin re-submits a summary after the log send failed.
- **Never call a `@discord.ui.button`-decorated method directly** (e.g. `TicketControlView().close_ticket(...)`) — it raises `TypeError: 'Button' object is not callable`. `ReopenedTicketView` duplicates the close logic and opens `CloseConfirmView` directly for this reason.

## Working with the user

The owner is a beginner and communicates in Thai. Ask before making any system/design decision you are unsure about. Make targeted edits to existing code rather than rewriting the file, state the exact class/method being changed, verify against the actual code before diagnosing, and fix one issue at a time so each change can be tested before the next.
