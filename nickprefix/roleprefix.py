import discord
import re
from redbot.core import commands, Config


class RolePrefix(commands.Cog):
    """Automatically apply nickname prefixes based on roles."""

    PREFIX_CLEAN = r"^\[[^\]]+\]\s*"

    def __init__(self, bot):
        self.bot = bot

        self.config = Config.get_conf(self, identifier=8293749823)

        default_guild = {
            "role_prefixes": {},
            "stacking": False
        }

        self.config.register_guild(**default_guild)

    # ---------------- UTIL ---------------- #

    async def get_prefixes(self, member: discord.Member):
        data = await self.config.guild(member.guild).role_prefixes()
        stacking = await self.config.guild(member.guild).stacking()

        roles = sorted(member.roles, key=lambda r: r.position, reverse=True)

        matches = []

        for role in roles:
            if str(role.id) in data:
                matches.append(data[str(role.id)])

        if not matches:
            return None

        if stacking:
            return "".join(matches)

        return matches[0]

    async def clean_name(self, name: str):
        return re.sub(self.PREFIX_CLEAN, "", name).strip()

    async def update_member(self, member: discord.Member):
        if not member.guild.me.guild_permissions.manage_nicknames:
            return

        if member.top_role >= member.guild.me.top_role:
            return

        prefix = await self.get_prefixes(member)

        current = member.nick if member.nick else member.name
        base = await self.clean_name(current)

        if prefix:
            new_name = f"{prefix} {base}"
        else:
            new_name = base

        if new_name == current:
            return

        if len(new_name) > 32:
            new_name = new_name[:32]

        try:
            await member.edit(nick=new_name, reason="Role prefix update")
        except discord.HTTPException:
            pass

    # ---------------- EVENTS ---------------- #

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.update_member(member)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            await self.update_member(after)

    # ---------------- COMMANDS ---------------- #

    @commands.group()
    @commands.admin_or_permissions(manage_roles=True)
    async def nickprefix(self, ctx):
        """Manage role prefixes."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @nickprefix.command()
    async def add(self, ctx, role: discord.Role, *, prefix: str):
        """Assign prefix to role."""

        data = await self.config.guild(ctx.guild).role_prefixes()
        data[str(role.id)] = prefix

        await self.config.guild(ctx.guild).role_prefixes.set(data)

        await ctx.send(f"Prefix `{prefix}` set for **{role.name}**")

    @nickprefix.command()
    async def remove(self, ctx, role: discord.Role):
        """Remove role prefix."""

        data = await self.config.guild(ctx.guild).role_prefixes()

        if str(role.id) not in data:
            await ctx.send("Role not configured.")
            return

        del data[str(role.id)]

        await self.config.guild(ctx.guild).role_prefixes.set(data)

        await ctx.send(f"Removed prefix for **{role.name}**")

    @nickprefix.command()
    async def list(self, ctx):
        """List configured prefixes."""

        data = await self.config.guild(ctx.guild).role_prefixes()

        if not data:
            await ctx.send("No prefixes configured.")
            return

        lines = []

        for role_id, prefix in data.items():
            role = ctx.guild.get_role(int(role_id))

            if role:
                lines.append(f"{role.name} → `{prefix}`")

        await ctx.send("\n".join(lines))

    @nickprefix.command()
    async def stacking(self, ctx, value: bool):
        """Toggle prefix stacking."""

        await self.config.guild(ctx.guild).stacking.set(value)

        state = "enabled" if value else "disabled"

        await ctx.send(f"Prefix stacking **{state}**")

    @nickprefix.command()
    async def force(self, ctx, member: discord.Member):
        """Force update a member."""

        await self.update_member(member)

        await ctx.send("Nickname updated.")

    @nickprefix.command()
    async def repair(self, ctx):
        """Repair all nicknames."""

        count = 0

        for member in ctx.guild.members:
            await self.update_member(member)
            count += 1

        await ctx.send(f"Checked {count} members.")


async def setup(bot):
    await bot.add_cog(RolePrefix(bot))