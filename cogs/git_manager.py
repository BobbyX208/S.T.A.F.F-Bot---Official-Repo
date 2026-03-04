import os
import subprocess
import asyncio
from typing import List, Optional
import git
from discord.ext import commands, tasks
import discord
from dotenv import load_dotenv
from utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

class GitManager(commands.Cog):
    """Manages automatic git pulls and hot reloading of extensions"""
    
    def __init__(self, bot):
        self.bot = bot
        self.repo_url = f"https://github.com/{os.getenv('GITHUB_REPO')}.git" if os.getenv('GITHUB_REPO') else None
        self.branch = os.getenv('GITHUB_BRANCH', 'main')
        self.poll_interval = int(os.getenv('GITHUB_POLL_INTERVAL', 60))
        self.repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.last_commit_hash = None
        
        # Start the auto-pull task
        if self.repo_url:
            self.auto_pull.start()
            logger.info(f"Git auto-pull enabled for {self.repo_url} ({self.branch})")
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.auto_pull.cancel()
    
    @tasks.loop(seconds=60)
    async def auto_pull(self):
        """Background task to check for and pull updates from GitHub"""
        # Wait for bot to be ready
        await self.bot.wait_until_ready()
        
        try:
            # Check if it's time to pull (using configured interval)
            if self.auto_pull.current_loop % (self.poll_interval // 60) != 0:
                return
            
            logger.info("Checking for repository updates...")
            
            # Initialize or open repository
            if not os.path.exists(os.path.join(self.repo_path, '.git')):
                logger.warning("Not a git repository, cloning...")
                await self._clone_repository()
                return
            
            # Perform git pull
            changed_files = await self._git_pull()
            
            if changed_files:
                logger.info(f"Changes detected in: {', '.join(changed_files)}")
                
                # Auto-reload if enabled and changes are in cogs
                if self._should_reload(changed_files):
                    await self._reload_changed_extensions(changed_files)
                    
                    # Notify staff channel about reload
                    await self._notify_reload(changed_files)
            else:
                logger.debug("No changes detected")
                
        except Exception as e:
            logger.error(f"Error in auto_pull task: {e}")
    
    async def _clone_repository(self):
        """Clone the repository if it doesn't exist"""
        try:
            # Run git clone in a thread pool to avoid blocking
            def clone():
                return git.Repo.clone_from(
                    self.repo_url,
                    self.repo_path,
                    branch=self.branch
                )
            
            repo = await asyncio.to_thread(clone)
            self.last_commit_hash = str(repo.head.commit)
            logger.info(f"Repository cloned successfully: {self.repo_url}")
            
            # Initial load of all extensions
            await self._load_all_extensions()
            
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
    
    async def _git_pull(self) -> List[str]:
        """Perform git pull and return list of changed files"""
        try:
            repo = git.Repo(self.repo_path)
            
            # Get current commit hash
            current_hash = str(repo.head.commit)
            
            # Fetch updates
            def fetch():
                origin = repo.remotes.origin
                origin.fetch()
                return origin
            
            await asyncio.to_thread(fetch)
            
            # Check if there are changes
            if current_hash == str(repo.head.commit):
                return []
            
            # Perform pull
            def pull():
                origin = repo.remotes.origin
                pull_info = origin.pull(self.branch)
                
                # Get changed files between old and new commit
                diff = repo.git.diff(
                    current_hash,
                    pull_info[0].commit,
                    name_only=True
                ).split('\n')
                
                return [f for f in diff if f]
            
            changed_files = await asyncio.to_thread(pull)
            self.last_commit_hash = str(repo.head.commit)
            
            return changed_files
            
        except Exception as e:
            logger.error(f"Git pull failed: {e}")
            return []
    
    def _should_reload(self, changed_files: List[str]) -> bool:
        """Determine if we should reload based on changed files"""
        # Reload if any Python files in cogs directory changed
        for file in changed_files:
            if file.startswith('cogs/') and file.endswith('.py'):
                return True
            if file == 'main.py' or file == 'database.py':
                return True
        return False
    
    async def _reload_changed_extensions(self, changed_files: List[str]):
        """Reload extensions that were affected by changes"""
        reloaded = []
        failed = []
        
        for file in changed_files:
            if file.startswith('cogs/') and file.endswith('.py'):
                # Convert file path to extension name
                extension = file.replace('/', '.').replace('.py', '')
                
                try:
                    if extension in self.bot.extensions:
                        await self.bot.reload_extension(extension)
                        logger.info(f"Reloaded extension: {extension}")
                        reloaded.append(extension)
                    else:
                        await self.bot.load_extension(extension)
                        logger.info(f"Loaded new extension: {extension}")
                        reloaded.append(extension)
                        
                except Exception as e:
                    logger.error(f"Failed to reload {extension}: {e}")
                    failed.append(extension)
            
            elif file == 'main.py':
                logger.warning("main.py changed - full restart may be required")
        
        return reloaded, failed
    
    async def _notify_reload(self, changed_files: List[str]):
        """Notify staff channel about reload"""
        # Find first available staff channel
        for guild in self.bot.guilds:
            # Look for a channel named 'staff-commands' or 'admin-log'
            channel = discord.utils.get(
                guild.text_channels,
                name__in=['staff-commands', 'admin-log', 'bot-log']
            )
            
            if channel:
                embed = discord.Embed(
                    title="🔄 Auto-Reload Complete",
                    description="Changes detected and extensions reloaded",
                    color=0x5865F2
                )
                embed.add_field(
                    name="Changed Files",
                    value=f"```\n{', '.join(changed_files[:5])}\n```",
                    inline=False
                )
                embed.set_footer(text=f"Commit: {self.last_commit_hash[:7]}")
                
                try:
                    await channel.send(embed=embed)
                except:
                    pass
                break
    
    async def _load_all_extensions(self):
        """Load all extensions from cogs directory"""
        import os
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and filename != '__init__.py':
                try:
                    await self.bot.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f"Loaded extension: cogs.{filename[:-3]}")
                except Exception as e:
                    logger.error(f"Failed to load cogs.{filename[:-3]}: {e}")
    
    @auto_pull.before_loop
    async def before_auto_pull(self):
        """Wait for bot to be ready before starting auto-pull"""
        await self.bot.wait_until_ready()
    
    @commands.command(name='reload')
    @commands.has_permissions(administrator=True)
    async def reload_extension(self, ctx, extension: str = None):
        """Reload a specific extension or all extensions"""
        if not extension:
            # Reload all extensions
            reloaded = []
            failed = []
            
            for ext in list(self.bot.extensions.keys()):
                try:
                    await self.bot.reload_extension(ext)
                    reloaded.append(ext)
                except Exception as e:
                    failed.append(f"{ext}: {e}")
            
            embed = discord.Embed(
                title="🔄 Extension Reload",
                color=0x57F287 if not failed else 0xED4245
            )
            
            if reloaded:
                embed.add_field(
                    name="✅ Reloaded",
                    value=f"```\n{chr(10).join(reloaded[:10])}\n```",
                    inline=False
                )
            
            if failed:
                embed.add_field(
                    name="❌ Failed",
                    value=f"```\n{chr(10).join(failed[:5])}\n```",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        else:
            # Reload specific extension
            try:
                await self.bot.reload_extension(f'cogs.{extension}')
                await ctx.send(f"✅ Successfully reloaded `cogs.{extension}`")
            except Exception as e:
                await ctx.send(f"❌ Failed to reload `cogs.{extension}`: {e}")
    
    @commands.command(name='gitpull')
    @commands.has_permissions(administrator=True)
    async def manual_git_pull(self, ctx):
        """Manually trigger a git pull"""
        async with ctx.typing():
            changed_files = await self._git_pull()
            
            if changed_files:
                reloaded, failed = await self._reload_changed_extensions(changed_files)
                
                embed = discord.Embed(
                    title="📥 Manual Git Pull Complete",
                    color=0x57F287
                )
                embed.add_field(
                    name="Changed Files",
                    value=f"```\n{', '.join(changed_files[:10])}\n```",
                    inline=False
                )
                
                if reloaded:
                    embed.add_field(
                        name="Reloaded Extensions",
                        value=f"```\n{', '.join(reloaded)}\n```",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("✅ No changes detected in repository")
    
    @commands.command(name='gitstatus')
    @commands.has_permissions(administrator=True)
    async def git_status(self, ctx):
        """Show current git status"""
        try:
            repo = git.Repo(self.repo_path)
            
            embed = discord.Embed(
                title="📊 Git Status",
                color=0x5865F2
            )
            embed.add_field(
                name="Branch",
                value=f"`{repo.active_branch.name}`",
                inline=True
            )
            embed.add_field(
                name="Latest Commit",
                value=f"`{str(repo.head.commit)[:7]}`",
                inline=True
            )
            embed.add_field(
                name="Remote",
                value=f"`{self.repo_url}`",
                inline=True
            )
            
            # Check for uncommitted changes
            if repo.is_dirty():
                embed.add_field(
                    name="⚠️ Warning",
                    value="There are uncommitted changes",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting git status: {e}")

async def setup(bot):
    await bot.add_cog(GitManager(bot))