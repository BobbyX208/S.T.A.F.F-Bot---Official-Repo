import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime
import io
import traceback
from typing import Optional, Union, Literal
from utils.logger import get_logger
import os
import aiofiles
import json

# Setup module logger
log = get_logger(__name__)

class Logging(commands.Cog):
    """Comprehensive logging system for server events and GitHub commits"""
    
    def __init__(self, bot):
        self.bot = bot
        self.server_log_channel = {}  # guild_id: channel_id
        self.github_log_channel = {}  # guild_id: channel_id
        self.sniped_messages = {}     # channel_id: message
        self.load_config()
    
    def load_config(self):
        """Load logging configuration from database/JSON"""
        try:
            if os.path.exists('data/logging_config.json'):
                with open('data/logging_config.json', 'r') as f:
                    config = json.load(f)
                    self.server_log_channel = {int(k): v for k, v in config.get('server_logs', {}).items()}
                    self.github_log_channel = {int(k): v for k, v in config.get('github_logs', {}).items()}
        except Exception as e:
            log.error(f"Failed to load logging config: {e}")
    
    async def save_config(self):
        """Save logging configuration"""
        try:
            os.makedirs('data', exist_ok=True)
            config = {
                'server_logs': {str(k): v for k, v in self.server_log_channel.items()},
                'github_logs': {str(k): v for k, v in self.github_log_channel.items()}
            }
            async with aiofiles.open('data/logging_config.json', 'w') as f:
                await f.write(json.dumps(config, indent=2))
        except Exception as e:
            log.error(f"Failed to save logging config: {e}")
    
    async def get_server_log_channel(self, guild_id: int) -> Optional[discord.TextChannel]:
        """Get the server log channel for a guild"""
        channel_id = self.server_log_channel.get(guild_id)
        if not channel_id:
            return None
        
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return None
        
        return guild.get_channel(channel_id)
    
    async def get_github_log_channel(self, guild_id: int) -> Optional[discord.TextChannel]:
        """Get the GitHub log channel for a guild"""
        channel_id = self.github_log_channel.get(guild_id)
        if not channel_id:
            return None
        
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return None
        
        return guild.get_channel(channel_id)
    
    # =========================================================================
    # HYBRID SETUP COMMANDS (Both Slash & Prefix)
    # =========================================================================
    
    @commands.hybrid_group(name='setup', description='Configure logging channels')
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx: commands.Context):
        """Setup logging channels (both prefix and slash)"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="📋 Logging Setup",
                description="Choose a subcommand:",
                color=0x5865F2
            )
            embed.add_field(name="`/setup logger #channel`", value="Set server event log channel", inline=False)
            embed.add_field(name="`/setup github #channel`", value="Set GitHub commit log channel", inline=False)
            embed.add_field(name="`/setup status`", value="Show current logging configuration", inline=False)
            embed.add_field(name="`/setup disable [logger/github/all]`", value="Disable logging channels", inline=False)
            
            await ctx.send(embed=embed)
    
    @setup.command(name='logger', description='Set the server event logging channel')
    @app_commands.describe(channel='The channel to send server logs to')
    @commands.has_permissions(administrator=True)
    async def setup_logger(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the server event logging channel"""
        self.server_log_channel[ctx.guild.id] = channel.id
        await self.save_config()
        
        embed = discord.Embed(
            title="✅ Logger Configured",
            description=f"Server events will be logged to {channel.mention}",
            color=0x57F287
        )
        embed.add_field(
            name="Events Tracked", 
            value="🗑️ Deleted • ✏️ Edited • 👋 Joins/Leaves • 📢 Channels • 🔊 Voice • And more...", 
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        # Send test message
        try:
            test_embed = discord.Embed(
                title="📝 Logger Active",
                description="This channel has been configured to receive server event logs.",
                color=0x5865F2,
                timestamp=datetime.utcnow()
            )
            test_embed.set_footer(text="Test Message")
            await channel.send(embed=test_embed)
        except:
            pass
    
    @setup.command(name='github', description='Set the GitHub commit logging channel')
    @app_commands.describe(channel='The channel to send GitHub commit logs to')
    @commands.has_permissions(administrator=True)
    async def setup_github(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the GitHub commit logging channel"""
        self.github_log_channel[ctx.guild.id] = channel.id
        await self.save_config()
        
        embed = discord.Embed(
            title="✅ GitHub Logger Configured",
            description=f"GitHub commits will be logged to {channel.mention}",
            color=0x57F287
        )
        embed.add_field(name="Events Tracked", value="🔗 Pushes • 📦 Commits • 🌿 Branch updates", inline=False)
        
        await ctx.send(embed=embed)
        
        # Send test message
        try:
            test_embed = discord.Embed(
                title="🔗 GitHub Logger Active",
                description="This channel will receive GitHub commit notifications.",
                color=0x5865F2,
                timestamp=datetime.utcnow()
            )
            test_embed.set_footer(text="Test Message")
            await channel.send(embed=test_embed)
        except:
            pass
    
    @setup.command(name='status', description='Show current logging configuration')
    @commands.has_permissions(administrator=True)
    async def setup_status(self, ctx: commands.Context):
        """Show current logging configuration"""
        server_channel = await self.get_server_log_channel(ctx.guild.id)
        github_channel = await self.get_github_log_channel(ctx.guild.id)
        
        embed = discord.Embed(
            title="📊 Logging Configuration",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📝 Server Events",
            value=server_channel.mention if server_channel else "❌ Not configured",
            inline=False
        )
        
        embed.add_field(
            name="🔗 GitHub Commits",
            value=github_channel.mention if github_channel else "❌ Not configured",
            inline=False
        )
        
        embed.set_footer(text=f"Guild: {ctx.guild.name}")
        
        await ctx.send(embed=embed)
    
    @setup.command(name='disable', description='Disable logging channels')
    @app_commands.describe(target='What to disable (logger/github/all)')
    @commands.has_permissions(administrator=True)
    async def setup_disable(
        self, 
        ctx: commands.Context, 
        target: Literal['logger', 'github', 'all'] = 'all'
    ):
        """Disable logging channels"""
        if target in ['logger', 'all']:
            if ctx.guild.id in self.server_log_channel:
                del self.server_log_channel[ctx.guild.id]
        
        if target in ['github', 'all']:
            if ctx.guild.id in self.github_log_channel:
                del self.github_log_channel[ctx.guild.id]
        
        await self.save_config()
        
        embed = discord.Embed(
            title="✅ Logging Disabled",
            description=f"Disabled: **{target}**",
            color=0xED4245
        )
        
        await ctx.send(embed=embed)
    
    # =========================================================================
    # HYBRID UTILITY COMMANDS
    # =========================================================================
    
    @commands.hybrid_command(name='snipe', description='Recover the last deleted message')
    @app_commands.describe(channel='Channel to snipe (defaults to current)')
    @commands.has_permissions(manage_messages=True)
    async def snipe(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Snipe the last deleted message in a channel"""
        channel = channel or ctx.channel
        
        message = self.sniped_messages.get(channel.id)
        if not message:
            await ctx.send("❌ No deleted message found in this channel.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔫 Sniped Message",
            description=message.content or "*No content*",
            color=0x5865F2,
            timestamp=message.created_at
        )
        
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        embed.set_footer(text=f"Deleted in #{channel.name}")
        
        if message.attachments:
            embed.add_field(name="Attachments", value=f"📎 {len(message.attachments)} file(s)", inline=False)
            # Add first attachment as image if it's an image
            for attachment in message.attachments:
                if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    embed.set_image(url=attachment.url)
                    break
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='logs', description='View recent bot logs')
    @app_commands.describe(lines='Number of lines to show (default: 50)')
    @commands.has_permissions(administrator=True)
    async def view_logs(self, ctx: commands.Context, lines: int = 50):
        """View recent bot logs"""
        await ctx.defer(ephemeral=True)  # Defer for both slash and prefix
        
        try:
            # Find latest log file
            log_files = sorted(Path('logs').glob('bot_*.log'), reverse=True)
            if not log_files:
                await ctx.send("❌ No log files found.", ephemeral=True)
                return
            
            latest_log = log_files[0]
            
            # Read last N lines
            async with aiofiles.open(latest_log, 'r') as f:
                content = await f.read()
                lines_list = content.split('\n')[-lines:]
                log_text = '\n'.join(lines_list)
            
            # Create file to send
            file = discord.File(
                io.BytesIO(log_text.encode()),
                filename=f"recent_{latest_log.name}"
            )
            
            embed = discord.Embed(
                title="📋 Recent Logs",
                description=f"Last {lines} lines from `{latest_log.name}`",
                color=0x5865F2
            )
            
            await ctx.send(embed=embed, file=file, ephemeral=True)
            
        except Exception as e:
            await ctx.send(f"❌ Error reading logs: {e}", ephemeral=True)
    
    # =========================================================================
    # MESSAGE LOGGING (Event Listeners)
    # =========================================================================
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log deleted messages"""
        if message.author.bot or not message.guild:
            return
        
        channel = await self.get_server_log_channel(message.guild.id)
        if not channel:
            return
        
        # Store for snipe command
        self.sniped_messages[message.channel.id] = message
        
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=0xED4245,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        
        if message.content:
            content = message.content[:1000] + "..." if len(message.content) > 1000 else message.content
            embed.add_field(name="Content", value=content, inline=False)
        
        if message.attachments:
            files = "\n".join([f"[{f.filename}]({f.url})" for f in message.attachments])
            embed.add_field(name="Attachments", value=files[:1000], inline=False)
        
        embed.set_footer(text=f"Message ID: {message.id}")
        
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log edited messages"""
        if before.author.bot or not before.guild or before.content == after.content:
            return
        
        channel = await self.get_server_log_channel(before.guild.id)
        if not channel:
            return
        
        embed = discord.Embed(
            title="✏️ Message Edited",
            color=0xFEE75C,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Author", value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Jump", value=f"[Click]({after.jump_url})", inline=True)
        
        # Before content
        before_content = before.content[:500] + "..." if len(before.content) > 500 else before.content
        embed.add_field(name="Before", value=before_content or "*No content*", inline=False)
        
        # After content
        after_content = after.content[:500] + "..." if len(after.content) > 500 else after.content
        embed.add_field(name="After", value=after_content or "*No content*", inline=False)
        
        embed.set_footer(text=f"Message ID: {before.id}")
        
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        """Log bulk message deletions"""
        if not messages or not messages[0].guild:
            return
        
        guild = messages[0].guild
        channel = await self.get_server_log_channel(guild.id)
        if not channel:
            return
        
        embed = discord.Embed(
            title="🗑️ Bulk Message Delete",
            description=f"**{len(messages)}** messages deleted in {messages[0].channel.mention}",
            color=0xED4245,
            timestamp=datetime.utcnow()
        )
        
        # Sample a few messages
        sample = list(messages)[:5]
        sample_text = ""
        for msg in sample:
            if msg.content:
                sample_text += f"**{msg.author}**: {msg.content[:50]}\n"
        
        if sample_text:
            embed.add_field(name="Sample", value=sample_text[:1000], inline=False)
        
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log member joins"""
        channel = await self.get_server_log_channel(member.guild.id)
        if not channel:
            return
        
        embed = discord.Embed(
            title="👋 Member Joined",
            color=0x57F287,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="User", value=f"{member.mention}\n{member}", inline=True)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Member Count", value=str(member.guild.member_count), inline=True)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID: {member.id}")
        
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log member leaves"""
        channel = await self.get_server_log_channel(member.guild.id)
        if not channel:
            return
        
        embed = discord.Embed(
            title="👋 Member Left",
            color=0xED4245,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="User", value=f"{member}\n{member.mention}", inline=True)
        embed.add_field(name="Joined", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown", inline=True)
        embed.add_field(name="Member Count", value=str(member.guild.member_count), inline=True)
        
        # Get roles (excluding @everyone)
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        if roles:
            embed.add_field(name="Roles", value=" ".join(roles[:5]), inline=False)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID: {member.id}")
        
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Log member changes (nickname, roles)"""
        if before == after or not before.guild:
            return
        
        channel = await self.get_server_log_channel(before.guild.id)
        if not channel:
            return
        
        # Nickname change
        if before.nick != after.nick:
            embed = discord.Embed(
                title="📝 Nickname Changed",
                color=0xFEE75C,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="User", value=before.mention, inline=True)
            embed.add_field(name="Before", value=before.nick or "*None*", inline=True)
            embed.add_field(name="After", value=after.nick or "*None*", inline=True)
            
            embed.set_footer(text=f"ID: {before.id}")
            await channel.send(embed=embed)
        
        # Role changes
        if before.roles != after.roles:
            added = [role for role in after.roles if role not in before.roles]
            removed = [role for role in before.roles if role not in after.roles]
            
            if added:
                embed = discord.Embed(
                    title="✅ Role Added",
                    color=0x57F287,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="User", value=before.mention, inline=True)
                embed.add_field(name="Role", value=added[0].mention, inline=True)
                embed.set_footer(text=f"ID: {before.id}")
                await channel.send(embed=embed)
            
            if removed:
                embed = discord.Embed(
                    title="❌ Role Removed",
                    color=0xED4245,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="User", value=before.mention, inline=True)
                embed.add_field(name="Role", value=removed[0].mention, inline=True)
                embed.set_footer(text=f"ID: {before.id}")
                await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Log channel creation"""
        if not channel.guild:
            return
            
        log_channel = await self.get_server_log_channel(channel.guild.id)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="📢 Channel Created",
            color=0x57F287,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
        embed.add_field(name="Category", value=channel.category.name if channel.category else "None", inline=True)
        
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Log channel deletion"""
        if not channel.guild:
            return
            
        log_channel = await self.get_server_log_channel(channel.guild.id)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="📢 Channel Deleted",
            color=0xED4245,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Channel Name", value=channel.name, inline=True)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
        embed.add_field(name="Category", value=channel.category.name if channel.category else "None", inline=True)
        
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        """Log channel updates"""
        if before == after or not before.guild:
            return
        
        log_channel = await self.get_server_log_channel(before.guild.id)
        if not log_channel:
            return
        
        # Name change
        if before.name != after.name:
            embed = discord.Embed(
                title="📝 Channel Renamed",
                color=0xFEE75C,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Before", value=before.name, inline=True)
            embed.add_field(name="After", value=after.mention, inline=True)
            await log_channel.send(embed=embed)
        
        # Topic change
        if hasattr(before, 'topic') and before.topic != after.topic:
            embed = discord.Embed(
                title="📝 Channel Topic Updated",
                color=0xFEE75C,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Channel", value=after.mention, inline=False)
            embed.add_field(name="Before", value=before.topic or "*None*", inline=False)
            embed.add_field(name="After", value=after.topic or "*None*", inline=False)
            await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Log voice channel changes"""
        if not member.guild or before.channel == after.channel:
            return
        
        channel = await self.get_server_log_channel(member.guild.id)
        if not channel:
            return
        
        # Joined voice
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(
                title="🔊 Joined Voice Channel",
                color=0x57F287,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="User", value=member.mention, inline=True)
            embed.add_field(name="Channel", value=after.channel.mention, inline=True)
        
        # Left voice
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(
                title="🔇 Left Voice Channel",
                color=0xED4245,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="User", value=member.mention, inline=True)
            embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        
        # Moved
        else:
            embed = discord.Embed(
                title="🔊 Moved Voice Channels",
                color=0xFEE75C,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="User", value=member.mention, inline=False)
            embed.add_field(name="From", value=before.channel.mention, inline=True)
            embed.add_field(name="To", value=after.channel.mention, inline=True)
        
        embed.set_footer(text=f"ID: {member.id}")
        await channel.send(embed=embed)
    
    # =========================================================================
    # GITHUB COMMIT LOGGING
    # =========================================================================
    
    @commands.Cog.listener()
    async def on_git_sync_complete(self, commit_data: dict):
        """Event listener for git sync completions"""
        # This would be dispatched by git_manager
        for guild in self.bot.guilds:
            await self.log_github_commit(guild.id, commit_data)
    
    async def log_github_commit(self, guild_id: int, commit_data: dict):
        """Log GitHub commit to configured channel"""
        channel = await self.get_github_log_channel(guild_id)
        if not channel:
            return
        
        embed = discord.Embed(
            title="🔗 GitHub Sync Complete",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        
        repo = commit_data.get('repo', 'unknown')
        branch = commit_data.get('branch', 'main')
        commits = commit_data.get('commits', [])
        files_changed = commit_data.get('files_changed', [])
        
        # Truncate repo URL for display
        if repo.startswith('https://'):
            repo = repo.replace('https://github.com/', '')
        
        embed.add_field(name="Repository", value=f"`{repo}`", inline=True)
        embed.add_field(name="Branch", value=f"`{branch}`", inline=True)
        
        if commits:
            commit_list = ""
            for i, commit in enumerate(commits[:3]):
                sha = commit.get('id', '')[:7]
                message = commit.get('message', '').split('\n')[0]
                commit_list += f"`{sha}` {message[:50]}\n"
            
            if commit_list:
                embed.add_field(name="Latest Commits", value=commit_list[:1000], inline=False)
        
        if files_changed:
            files_list = "\n".join(files_changed[:5])
            if len(files_changed) > 5:
                files_list += f"\n... and {len(files_changed) - 5} more"
            embed.add_field(name="Files Changed", value=f"```\n{files_list}\n```", inline=False)
        
        embed.set_footer(text=f"Total commits: {len(commits)}")
        
        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logging(bot))