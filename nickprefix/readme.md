# RolePrefix Cog

A simple and reliable Red-DiscordBot cog that automatically applies nickname prefixes based on roles.

This is designed for servers that use structured role tags such as:

```
(Mod) Dev
[ADMIN] John
(PD) Officer Smith
[EMS] Cinna
```

When a member gains or loses a role, their nickname will automatically update to reflect the configured prefix.

---

# Features

- Automatic nickname prefixes based on roles
- Optional prefix stacking
- Rate-limit protection to avoid Discord API spam
- Role hierarchy safety checks
- Permission error reporting
- Automatic cleanup of malformed nicknames
- Mass repair command for existing members

The system also automatically normalizes spacing so nicknames like:

```
(SF)      Dev
```

become:

```
(SF) Dev
```

---

# Commands

## Configuration

### `nickprefix add <role> <prefix>`

Assign a prefix to a role.

Example:

```
[p]nickprefix add Sheriff (SF)
[p]nickprefix add Admin [ADMIN]
```

---

### `nickprefix remove <role>`

Remove a prefix from a role.

```
[p]nickprefix remove Sheriff
```

---

### `nickprefix list`

Shows all configured role prefixes.

---

### `nickprefix stacking <true|false>`

Enable or disable prefix stacking.

If stacking is enabled, members with multiple roles will receive multiple prefixes.

Example:

```
(SF) (PD) Dev
```

If disabled, only the highest role prefix is used.

---

## Maintenance

### `nickprefix force <member>`

Force a nickname update for a specific user.

Useful if a nickname was manually edited or something desynced.

---

### `nickprefix repair`

Re-applies prefixes to every member in the server.

Useful when first installing the cog or after changing prefix rules.

---

# Behavior

The cog automatically updates nicknames when:

- A member joins the server
- A member gains or loses roles
- A nickname is manually edited

Nicknames are cleaned before applying prefixes to prevent duplicates or spacing issues.

Example transformations:

| Input                | Output          |
| -------------------- | --------------- |
| `Dev`           | `(SF) Dev` |
| `(SF)      Dev` | `(SF) Dev` |
| `[ADMIN] Dev`   | `(SF) Dev` |

---

# Safety Features

To prevent Discord rate limits and nickname conflicts the cog includes:

- Per-member update locks
- Basic rate limiting
- Role hierarchy validation
- Permission checks

If the bot cannot edit a nickname, an error message will be returned when using commands like `force`.

---

# Requirements

- Red-DiscordBot 3.x
- Bot must have **Manage Nicknames** permission
- Bot role must be **above members it edits**

---

# Installation

Example repository installation:

```
[p]repo add myrepo https://github.com/ItzDabbzz/dabz-cogs
[p]cog install dabz-cogs roleprefix
[p]load roleprefix
```

---

# License

MIT
