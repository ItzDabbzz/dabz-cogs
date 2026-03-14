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

        self._edit_timestamps = {}

    # ------------------------------------------------
    # Utility
    # ------------------------------------------------

    def _clean_prefix(self, name: str):
        return re.sub(r"^(\[[^\]]+\])+\s*", "", name).strip()

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
            return "".join(matches)

        return matches[0]

    async def _update_member(self, member: discord.Member):

        guild = member.guild
        me = guild.me

        if not me.guild_permissions.manage_nicknames:
            return

        if member.top_role >= me.top_role:
            return

        if await self._rate_limited(member):
            return

        prefix = await self._get_prefix(member)

        current = member.nick or member.name
        base = self._clean_prefix(current)

        new_name = f"{prefix} {base}".strip() if prefix else base

        if new_name == current:
            return

        if len(new_name) > 32:
            new_name = new_name[:32]

        try:
            await member.edit(nick=new_name, reason="Role prefix update")
        except discord.HTTPException:
            pass

    # ------------------------------------------------
    # Events
    # ------------------------------------------------

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self._update_member(member)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
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
                lines.append(f"{role.name} → `{prefix}`")

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

        await self._update_member(member)
        await ctx.send("Nickname updated.")

    @nickprefix.command()
    async def repair(self, ctx):
        """Repair nicknames for all members."""

        await ctx.send("Repairing nicknames...")

        for member in ctx.guild.members:
            await self._update_member(member)
            await asyncio.sleep(1)

        await ctx.send("Repair complete.")