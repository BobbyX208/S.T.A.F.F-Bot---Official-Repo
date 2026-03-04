import os
import sys
import asyncio
import json
from pathlib import Path
import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import DatabaseHandler
from utils.logger import get_logger

# Load environment variables
load_dotenv()

# Setup logging
logger = get_logger(__name__)

class StaffBot(commands.Bot):
    """Main bot class with database integration"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=commands.when_mentioned_or(os.getenv('COMMAND_PREFIX', '!')),
            intents=intents,
            help_command=None  # We'll implement custom help later
        )
        
        self.db = DatabaseHandler()
        self.config = self.load_config()
        self.start_time = None
        
    def load_config(self) -> dict:
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config.json: {e}")
            return {}
    
    async def setup_hook(self):
        """Initialize bot components"""
        self.start_time = discord.utils.utcnow()
        
        # Initialize database
        await self.db.initialize()
        
        # Load all cogs
        await self.load_extensions()
        
        # Sync commands (optional - can be slow)
        # await self.tree.sync()
        
        logger.info("Bot setup complete")
    
    async def load_extensions(self):
        """Load all cogs from the cogs directory"""
        cogs_dir = Path('./cogs')
        if not cogs_dir.exists():
            cogs_dir.mkdir()
            logger.info("Created cogs directory")
            
            # Create a sample __init__.py
            with open(cogs_dir / '__init__.py', 'w') as f:
                f.write('"""Cogs package"""')
        
        # Load all .py files in cogs directory
        for cog_file in cogs_dir.glob('*.py'):
            if cog_file.name != '__init__.py':
                try:
                    await self.load_extension(f'cogs.{cog_file.stem}')
                    logger.info(f"Loaded extension: cogs.{cog_file.stem}")
                except Exception as e:
                    logger.error(f"Failed to load extension cogs.{cog_file.stem}: {e}")
    
    async def on_ready(self):
        """Event triggered when bot is ready"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set bot status
        activity_name = self.config.get('bot', {}).get('activity', 'for updates')
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=activity_name
            ),
            status=discord.Status.online
        )
        
        # Log guild information
        for guild in self.guilds:
            logger.info(f"Guild: {guild.name} (ID: {guild.id}) | Members: {guild.member_count}")
    
    async def on_command_error(self, ctx, error):
        """Global error handler"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument: {error}")
        else:
            logger.error(f"Command error in {ctx.command}: {error}")
            await ctx.send(f"❌ An error occurred: {error}")
    
    async def close(self):
        """Clean up when bot shuts down"""
        await self.db.close()
        await super().close()

async def main():
    """Main entry point"""
    # Create bot instance
    bot = StaffBot()
    
    # Get token from environment
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("No Discord token found in environment variables")
        sys.exit(1)
    
    # Run bot
    try:
        async with bot:
            await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())