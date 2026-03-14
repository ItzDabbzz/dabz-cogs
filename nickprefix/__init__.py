from .roleprefix import RolePrefix

async def setup(bot):
    await bot.add_cog(RolePrefix(bot))