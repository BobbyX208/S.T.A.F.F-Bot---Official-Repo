import discord
from discord.ext import commands

class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("🔧 TEST COG LOADED - Version 1")
    
    @commands.command(name='test')
    async def test(self, ctx):
        await ctx.send("✅ Test cog v1 is working!")

async def setup(bot):
    await bot.add_cog(Test(bot))