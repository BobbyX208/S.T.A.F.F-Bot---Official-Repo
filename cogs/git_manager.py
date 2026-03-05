import os
import asyncio
from typing import List
import git
from git.exc import GitCommandError, InvalidGitRepositoryError
from discord.ext import commands, tasks
import discord
from dotenv import load_dotenv
from utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

class GitManager(commands.Cog):
    """Production-hardened Git auto-update system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.repo_path = os.getcwd()  # Pterodactyl launches here
        
        # Initialize ALL config vars first, then validate
        self.enabled = os.getenv('ENABLE_GIT_SYNC', 'false').lower() == 'true'
        self.repo_url = os.getenv('GITHUB_REPO')
        self.branch = os.getenv('GITHUB_BRANCH', 'main')
        self.poll_interval = int(os.getenv('GITHUB_POLL_INTERVAL', 60))
        self.fetch_timeout = 30  # seconds
        
        # Early validation
        if not self.repo_url:
            logger.error("❌ GITHUB_REPO not set in .env")
            self.enabled = False
            return
        
        # Sync lock
        self._sync_lock = asyncio.Lock()
        self.repo = None
        
        # Validate git repository exists
        git_dir = os.path.join(self.repo_path, '.git')
        if not os.path.exists(git_dir):
            logger.error(f"❌ No .git folder found at {self.repo_path}")
            self.enabled = False
            return
        
        # Initialize repo
        try:
            self.repo = git.Repo(self.repo_path)
            logger.info(f"✅ Git repository loaded from {self.repo_path}")
        except InvalidGitRepositoryError:
            logger.error("❌ Invalid git repository")
            self.enabled = False
            return
        
        # Validate remote exists
        if 'origin' not in [r.name for r in self.repo.remotes]:
            try:
                self.repo.create_remote('origin', self.repo_url)
                logger.info(f"✅ Added remote origin: {self.repo_url}")
            except Exception as e:
                logger.error(f"❌ Failed to add remote: {e}")
                self.enabled = False
                return
        
        # Start auto-sync if enabled
        if self.enabled:
            self.auto_sync.change_interval(seconds=self.poll_interval)
            self.auto_sync.start()
            logger.info(f"🔄 Auto-sync ENABLED (interval: {self.poll_interval}s, branch: {self.branch})")
        else:
            logger.info("⏸️ Auto-sync DISABLED (set ENABLE_GIT_SYNC=true to enable)")
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        if hasattr(self, 'auto_sync') and self.auto_sync.is_running():
            self.auto_sync.cancel()
    
    async def _fetch(self) -> bool:
        """Fetch from remote with timeout"""
        try:
            def fetch():
                self.repo.remotes.origin.fetch()
            
            await asyncio.wait_for(
                asyncio.to_thread(fetch),
                timeout=self.fetch_timeout
            )
            logger.debug(f"✅ Fetched from origin")
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"❌ Fetch timeout after {self.fetch_timeout}s")
            return False
        except Exception as e:
            logger.error(f"❌ Fetch failed: {e}")
            return False
    
    async def _sync(self) -> bool:
        """Core sync operation"""
        
        # Quick validation
        if 'origin' not in [r.name for r in self.repo.remotes]:
            logger.error("❌ No remote 'origin' configured")
            return False
        
        # Warn about local changes (optional but useful)
        if self.repo.is_dirty(untracked_files=True):
            logger.warning("⚠️ Local changes detected - they will be overwritten")
        
        # Get current commit
        try:
            old_commit = self.repo.head.commit.hexsha
        except Exception as e:
            logger.error(f"❌ Cannot get current commit: {e}")
            return False
        
        # Fetch with timeout
        if not await self._fetch():
            return False
        
        # Verify remote branch exists
        try:
            remote_commit = self.repo.commit(f'origin/{self.branch}').hexsha
        except Exception:
            logger.error(f"❌ Remote branch origin/{self.branch} not found")
            return False
        
        # Compare
        if old_commit == remote_commit:
            logger.debug(f"No changes (both at {old_commit[:7]})")
            return False
        
        logger.info(f"📥 Changes: {old_commit[:7]} -> {remote_commit[:7]}")
        
        # Hard reset
        try:
            def reset():
                self.repo.git.reset('--hard', f'origin/{self.branch}')
            
            await asyncio.to_thread(reset)
            logger.info(f"✅ Hard reset to origin/{self.branch}")
        except Exception as e:
            logger.error(f"❌ Reset failed: {e}")
            return False
        
        # Get changed files
        new_commit = self.repo.head.commit.hexsha
        
        try:
            def get_diff():
                return self.repo.git.diff('--name-only', old_commit, new_commit).splitlines()
            
            changed_files = await asyncio.to_thread(get_diff)
        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            changed_files = []
        
        if changed_files:
            logger.info(f"📁 Files changed: {len(changed_files)}")
            
            reloaded = []
            failed = []
            
            # Limit to first 50 files to prevent massive reload storms
            for file_path in changed_files[:50]:
                if file_path.startswith('cogs/') and file_path.endswith('.py'):
                    extension = file_path.replace(os.sep, '.').replace('.py', '')
                    
                    try:
                        if extension in self.bot.extensions:
                            await self.bot.reload_extension(extension)
                        else:
                            await self.bot.load_extension(extension)
                        logger.info(f"  ✅ {extension}")
                        reloaded.append(extension)
                    except Exception as e:
                        logger.error(f"  ❌ {extension}: {e}")
                        failed.append(extension)
                
                # Use .endswith() for main.py detection
                elif file_path.endswith('main.py'):
                    logger.warning("⚠️ main.py changed - Manual restart required")
            
            if len(changed_files) > 50:
                logger.warning(f"⚠️ Only processed first 50 of {len(changed_files)} changed files")
            
            # Log summary
            if reloaded:
                logger.info(f"✅ Reloaded {len(reloaded)} cogs")
            if failed:
                logger.warning(f"❌ Failed {len(failed)} cogs")

        # Dispatch GitHub event for logging
        if changed_files:
            try:
                commit_data = {
                    'repo': self.repo_url,
                    'branch': self.branch,
                    'commits': [{
                        'id': new_commit,
                        'message': self.repo.head.commit.message.strip(),
                        'author': str(self.repo.head.commit.author)
                    }],
                    'files_changed': changed_files[:20],
                    'total_files': len(changed_files),
                    'old_commit': old_commit,
                    'new_commit': new_commit
                }
                self.bot.dispatch('git_sync_complete', commit_data)
                logger.debug(f"Dispatched git_sync_complete event with {len(changed_files)} files")
            except Exception as e:
                logger.error(f"Failed to dispatch git event: {e}")
        return True
    
    @tasks.loop(seconds=60)  # Default, changed in __init__
    async def auto_sync(self):
        """Background sync task"""
        async with self._sync_lock:
            try:
                logger.debug("Checking for updates...")
                await self._sync()
            except Exception as e:
                logger.error(f"❌ Sync error: {e}")
    
    @auto_sync.before_loop
    async def before_auto_sync(self):
        await self.bot.wait_until_ready()
        logger.info("Git sync system ready")
    
    @commands.command(name='sync')
    @commands.has_permissions(administrator=True)
    async def manual_sync(self, ctx):
        """Manually trigger git sync"""
        if not self.enabled:
            await ctx.send("❌ Git sync is disabled")
            return
        
        async with ctx.typing():
            async with self._sync_lock:
                try:
                    success = await self._sync()
                    if success:
                        await ctx.send(f"✅ Sync completed. Current: `{self.repo.head.commit.hexsha[:7]}`")
                    else:
                        await ctx.send("✅ Already up to date")
                except Exception as e:
                    await ctx.send(f"❌ Sync failed: {e}")
    
    @commands.command(name='gitstatus')
    @commands.has_permissions(administrator=True)
    async def git_status(self, ctx):
        """Show git status"""
        try:
            if not self.repo:
                await ctx.send("❌ No git repository")
                return
            
            # Get commits
            local = self.repo.head.commit.hexsha[:7]
            
            try:
                await self._fetch()
                remote = self.repo.commit(f'origin/{self.branch}').hexsha[:7]
            except:
                remote = "unknown"
            
            is_dirty = self.repo.is_dirty(untracked_files=True)
            
            embed = discord.Embed(
                title="📊 Git Status",
                color=0x5865F2,
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name="Branch", value=f"`{self.branch}`", inline=True)
            embed.add_field(name="Local", value=f"`{local}`", inline=True)
            embed.add_field(name="Remote", value=f"`{remote}`", inline=True)
            embed.add_field(name="Auto-Sync", value="✅ On" if self.enabled else "❌ Off", inline=False)
            
            if local != remote and remote != "unknown":
                embed.add_field(name="📥 Status", value="Behind remote - run `!sync`", inline=False)
            
            if is_dirty:
                embed.add_field(name="⚠️ Warning", value="Local uncommitted changes", inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(GitManager(bot))
