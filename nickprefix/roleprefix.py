import asyncio
import re
import time

import discord
from redbot.core import commands, Config


class RolePrefix(commands.Cog):
    """Automatically apply nickname prefixes based on roles."""

    def __init__(self, bot):
        self.bot = bot

        self.config = Config.get_conf(self, identifier=902341233)
        default_guild = {
            "prefixes": {},   # role_id -> prefix
            "stacking": False
        }
        self.config.register_guild(**default_guild)
        self._prefix_cache = {}
        self._member_locks = {}
        self._edit_timestamps = {}

    # ------------------------------------------------
    # Utility
    # ------------------------------------------------
    def _has_correct_prefix(self, name: str, prefix: str):
        if not prefix:
            return False
        return name.startswith(prefix + " ") or name == prefix

    def _clean_prefix(self, name: str):
        # remove [TAG] or (TAG) prefixes
        name = re.sub(r"^((\[[^\]]+\])|(\([^)]+\)))+\s*", "", name)

        # normalize whitespace
        return re.sub(r"\s+", " ", name).strip()

    def _get_lock(self, member_id: int):
        if member_id not in self._member_locks:
            self._member_locks[member_id] = asyncio.Lock()
        return self._member_locks[member_id]

    async def _rate_limited(self, member: discord.Member):
        now = time.time()
        last = self._edit_timestamps.get(member.id, 0)

        if now - last < 8:
            return True

        self._edit_timestamps[member.id] = now
        return False

    async def _get_prefix(self, member: discord.Member):

        data = await self.config.guild(member.guild).prefixes()
        stacking = await self.config.guild(member.guild).stacking()

        roles = sorted(member.roles, key=lambda r: r.position, reverse=True)

        matches = []
        for role in roles:
            p = data.get(str(role.id))
            if p:
                matches.append(p)

        if not matches:
            return ""

        if stacking:
            return " ".join(matches)

        return matches[0]

    async def _update_member(self, member: discord.Member):
        lock = self._get_lock(member.id)

        async with lock:
            guild = member.guild
            me = guild.me

            # Check permissions
            if not me.guild_permissions.manage_nicknames:
                return "missing_perm"

            # Check role hierarchy
            if member.top_role >= me.top_role:
                return "role_hierarchy"

            # Check rate limit
            if await self._rate_limited(member):
                return "rate_limited"

            # Get the appropriate prefix
            prefix = await self._get_prefix(member)
            cached = self._prefix_cache.get(member.id)
            if cached == prefix:
                return "no_change"
            # Determine current nickname (or fallback to username)
            current = member.nick or member.name
            # If the current nickname already has the correct prefix, no update is needed
            if prefix and self._has_correct_prefix(current, prefix):
                return "no_change"
            # Remove existing prefixes to get the base name
            base = self._clean_prefix(current)
            # Construct the new nickname with the prefix
            new_name = f"{prefix} {base}".strip() if prefix else base
            new_name = re.sub(r"\s+", " ", new_name)
            # If the new nickname is the same as the current, no update is needed
            if new_name == current:
                return "no_change"
            # Discord nickname limit is 32 characters
            if len(new_name) > 32:
                new_name = new_name[:32]
            # Attempt to update the member's nickname
            try:
                await member.edit(nick=new_name, reason="Role prefix update")
                self._prefix_cache[member.id] = prefix
                return "success"
            except discord.Forbidden:
                return "role_hierarchy"
            except discord.HTTPException:
                return "http_error"

    # ------------------------------------------------
    # Events
    # ------------------------------------------------

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self._update_member(member)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # role change
        if before.roles != after.roles:
            await self._update_member(after)
            return

        # nickname manually changed
        if before.nick != after.nick:
            await self._update_member(after)

    # ------------------------------------------------
    # Commands
    # ------------------------------------------------

    @commands.group()
    @commands.admin_or_permissions(manage_roles=True)
    async def nickprefix(self, ctx):
        """Configure role nickname prefixes."""
        pass

    @nickprefix.command()
    async def add(self, ctx, role: discord.Role, *, prefix: str):
        """Assign a prefix to a role."""

        data = await self.config.guild(ctx.guild).prefixes()

        data[str(role.id)] = prefix
        await self.config.guild(ctx.guild).prefixes.set(data)

        await ctx.send(f"Prefix `{prefix}` set for **{role.name}**.")

    @nickprefix.command()
    async def remove(self, ctx, role: discord.Role):
        """Remove a role prefix."""

        data = await self.config.guild(ctx.guild).prefixes()

        if str(role.id) not in data:
            await ctx.send("That role has no prefix configured.")
            return

        del data[str(role.id)]
        await self.config.guild(ctx.guild).prefixes.set(data)

        await ctx.send(f"Removed prefix from **{role.name}**.")

    @nickprefix.command()
    async def list(self, ctx):
        """List configured role prefixes."""

        data = await self.config.guild(ctx.guild).prefixes()

        if not data:
            await ctx.send("No prefixes configured.")
            return

        lines = []

        for rid, prefix in data.items():
            role = ctx.guild.get_role(int(rid))
            if role:
                lines.append(f" <@&{role.id}> [ {role.name} ] → `{prefix}`")

        await ctx.send("\n".join(lines))

    @nickprefix.command()
    async def stacking(self, ctx, value: bool):
        """Enable or disable prefix stacking."""

        await self.config.guild(ctx.guild).stacking.set(value)

        state = "enabled" if value else "disabled"
        await ctx.send(f"Prefix stacking **{state}**.")

    @nickprefix.command()
    async def force(self, ctx, member: discord.Member):
        """Force update a member nickname."""

        result = await self._update_member(member)

        messages = {
            "success": "✅ Nickname updated.",
            "missing_perm": "❌ Bot is missing **Manage Nicknames** permission.",
            "role_hierarchy": "❌ Cannot edit nickname — bot role is below this member.",
            "rate_limited": "⚠️ Nickname update skipped due to rate limit protection.",
            "http_error": "❌ Discord rejected the nickname update.",
            "no_change": "ℹ️ Nickname already correct."
        }

        await ctx.send(messages.get(result, "Unknown result."))

    @nickprefix.command()
    async def repair(self, ctx):
        """Repair nicknames for all members."""

        await ctx.send("Repairing nicknames...")

        results = {
            "success": 0,
            "role_hierarchy": 0,
            "missing_perm": 0,
            "http_error": 0
        }

        for member in ctx.guild.members:
            result = await self._update_member(member)

            if result in results:
                results[result] += 1

            await asyncio.sleep(1)

        await ctx.send(
            f"Repair complete.\n"
            f"Updated: {results['success']}\n"
            f"Hierarchy blocked: {results['role_hierarchy']}\n"
            f"Permission errors: {results['missing_perm']}\n"
            f"HTTP errors: {results['http_error']}"
        )