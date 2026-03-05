import discord
from discord.ext import commands
from discord import app_commands
import time
import asyncio
from datetime import datetime, timedelta
from utils.logger import get_logger

log = get_logger(__name__)

class Help(commands.Cog):
    """Custom help command with latency and auto-delete"""
    
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command('help')  # Remove default help
        self.start_time = time.time()
    
    def get_prefix(self):
        """Get the actual command prefix as a string"""
        prefix = self.bot.command_prefix
        
        if callable(prefix):
            if hasattr(prefix, '__self__'):
                try:
                    if 'when_mentioned_or' in str(prefix):
                        # Default to '!' if we can't determine
                        return '!'
                except:
                    pass
            return '!'  # Default fallback
        
        return prefix
    
    def get_command_signature(self, command):
        """Get command signature with prefix"""
        prefix = self.get_prefix()
        signature = f"{prefix}{command.qualified_name}"
        if command.signature:
            signature += f" {command.signature}"
        return signature
    
    def get_cog_commands(self, cog_name):
        """Get all commands from a cog"""
        cog = self.bot.get_cog(cog_name)
        if not cog:
            return []
        
        commands_list = []
        for cmd in cog.walk_commands():
            if not cmd.hidden:
                commands_list.append(cmd)
        return commands_list
    
    # =========================================================================
    # PING COMMAND
    # =========================================================================
    
    @commands.hybrid_command(name='ping', description='Check bot latency and response time')
    async def ping(self, ctx: commands.Context):
        """Check bot's response time and WebSocket latency"""
        # Record start time
        start_time = time.time()
        
        # Send initial message
        msg = await ctx.send("🏓 Pinging...")
        
        # Calculate response times
        response_time = round((time.time() - start_time) * 1000)
        ws_latency = round(self.bot.latency * 1000)
        uptime_seconds = time.time() - self.start_time
        uptime = str(timedelta(seconds=int(uptime_seconds)))
        
        # Create embed
        embed = discord.Embed(
            title="🏓 Pong!",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="📡 WebSocket Latency", value=f"`{ws_latency}ms`", inline=True)
        embed.add_field(name="🔄 Response Time", value=f"`{response_time}ms`", inline=True)
        embed.add_field(name="⏱️ Uptime", value=f"`{uptime}`", inline=False)
        embed.add_field(name="👤 Requested By", value=ctx.author.mention, inline=True)
        
        embed.set_footer(text="This message will auto-delete in 3 minutes")
        
        # Edit the message with embed
        await msg.edit(content=None, embed=embed)
        
        # Auto-delete after 3 minutes
        await asyncio.sleep(180)
        try:
            await msg.delete()
        except:
            pass
    
    # =========================================================================
    # HELP COMMAND
    # =========================================================================
    
    @commands.hybrid_command(name='help', description='Show all available commands')
    @app_commands.describe(command='Specific command to get help with')
    async def help(self, ctx: commands.Context, command: str = None):
        """Show help for all commands or a specific command"""
        
        # If a specific command is requested
        if command:
            cmd = self.bot.get_command(command)
            if not cmd or cmd.hidden:
                embed = discord.Embed(
                    title="❌ Command Not Found",
                    description=f"Could not find command `{command}`",
                    color=0xED4245,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="👤 Requested By", value=ctx.author.mention)
                embed.set_footer(text="This message will auto-delete in 3 minutes")
                
                msg = await ctx.send(embed=embed)
                
                # Auto-delete after 3 minutes
                await asyncio.sleep(180)
                try:
                    await msg.delete()
                except:
                    pass
                return
            
            # Show help for specific command
            embed = discord.Embed(
                title=f"📚 Command: {cmd.qualified_name}",
                description=cmd.help or "No description provided.",
                color=0x5865F2,
                timestamp=datetime.utcnow()
            )
            
            # Usage
            embed.add_field(
                name="📝 Usage",
                value=f"`{self.get_command_signature(cmd)}`",
                inline=False
            )
            
            # Aliases
            if cmd.aliases:
                embed.add_field(
                    name="🔀 Aliases",
                    value=", ".join([f"`{alias}`" for alias in cmd.aliases]),
                    inline=False
                )
            
            # Permissions
            if cmd.requires.permissions:
                perms = []
                for perm, value in cmd.requires.permissions.__dict__.items():
                    if value and not perm.startswith('_'):
                        perms.append(f"`{perm.replace('_', ' ').title()}`")
                if perms:
                    embed.add_field(
                        name="🔒 Required Permissions",
                        value=", ".join(perms),
                        inline=False
                    )
            
            embed.add_field(name="👤 Requested By", value=ctx.author.mention)
            embed.set_footer(text="This message will auto-delete in 3 minutes")
            
            msg = await ctx.send(embed=embed)
            
        else:
            # Show all commands grouped by cog
            prefix = self.get_prefix()
            embed = discord.Embed(
                title="📚 Command List",
                description=f"Use `{prefix}help <command>` for more info on a command.",
                color=0x5865F2,
                timestamp=datetime.utcnow()
            )
            
            # Get all cogs
            for cog_name in self.bot.cogs:
                cog = self.bot.get_cog(cog_name)
                if not cog:
                    continue
                
                # Skip hidden cogs
                if cog_name in ['Help']:
                    continue
                
                # Get commands from this cog
                commands_list = self.get_cog_commands(cog_name)
                if not commands_list:
                    continue
                
                # Format commands
                cmd_text = ""
                for cmd in commands_list[:10]:
                    if not cmd.hidden:
                        cmd_text += f"`{cmd.name}` "
                
                if cmd_text:
                    embed.add_field(
                        name=f"📁 {cog_name}",
                        value=cmd_text,
                        inline=False
                    )
            
            # Add system info
            ws_latency = round(self.bot.latency * 1000)
            embed.add_field(
                name="📊 System Info",
                value=f"📡 Latency: `{ws_latency}ms`\n👤 Requested by: {ctx.author.mention}",
                inline=False
            )
            
            embed.set_footer(text="This message will auto-delete in 3 minutes")
            
            msg = await ctx.send(embed=embed)
        
        # Auto-delete after 3 minutes
        await asyncio.sleep(180)
        try:
            await msg.delete()
            # Also try to delete the command message if possible
            if not ctx.interaction:
                await ctx.message.delete()
        except:
            pass
    
    # =========================================================================
    # ADDITIONAL USEFUL COMMANDS
    # =========================================================================
    
    @commands.hybrid_command(name='uptime', description='Show how long the bot has been running')
    async def uptime(self, ctx: commands.Context):
        """Show bot uptime"""
        uptime_seconds = time.time() - self.start_time
        uptime = str(timedelta(seconds=int(uptime_seconds)))
        
        embed = discord.Embed(
            title="⏱️ Bot Uptime",
            description=f"Bot has been running for: **{uptime}**",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="📡 WebSocket Latency", value=f"`{round(self.bot.latency * 1000)}ms`")
        embed.add_field(name="👤 Requested By", value=ctx.author.mention)
        embed.set_footer(text="This message will auto-delete in 3 minutes")
        
        msg = await ctx.send(embed=embed)
        
        # Auto-delete after 3 minutes
        await asyncio.sleep(180)
        try:
            await msg.delete()
        except:
            pass
    
    @commands.hybrid_command(name='invite', description='Get bot invite link')
    async def invite(self, ctx: commands.Context):
        """Get bot invite link"""
        # Generate invite link with required permissions
        permissions = discord.Permissions(administrator=True)
        
        invite_link = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=permissions
        )
        
        embed = discord.Embed(
            title="🔗 Invite Me!",
            description=f"[Click here to invite me to your server]({invite_link})",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="👤 Requested By", value=ctx.author.mention)
        embed.set_footer(text="This message will auto-delete in 3 minutes")
        
        msg = await ctx.send(embed=embed)
        
        # Auto-delete after 3 minutes
        await asyncio.sleep(180)
        try:
            await msg.delete()
        except:
            pass

    @commands.command(name='forcesync')
    @commands.has_permissions(administrator=True)
    async def force_sync(self, ctx: commands.Context):
        """Force sync all slash commands"""
        async with ctx.typing():
            try:
                # Sync to current guild first (instant)
                guild = discord.Object(id=ctx.guild.id)
                self.bot.tree.copy_global_to(guild=guild)
                synced = await self.bot.tree.sync(guild=guild)
                
                embed = discord.Embed(
                    title="✅ Slash Commands Synced",
                    color=0x57F287,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Guild Commands", value=f"`{len(synced)}` commands synced to this server")
                embed.add_field(name="Note", value="Global sync may take up to 1 hour", inline=False)
                embed.set_footer(text="Commands should appear immediately in this server")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ Sync failed: {e}")

async def setup(bot):
    await bot.add_cog(Help(bot))
