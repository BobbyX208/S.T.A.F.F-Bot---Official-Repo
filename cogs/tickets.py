"""
Modular Ticket System for S.T.A.F.F. Bot
Features:
- Per-server configuration
- Database persistence
- Dropdown category selection
- Dynamic modals per category
- Persistent buttons after restart
- Transcript generation
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, Any, List
import logging
import asyncio
import json
import aiofiles
from datetime import datetime
import os
from utils.logger import get_logger

logger = get_logger(__name__)

# =============================================================================
# CONFIGURATION MODELS
# =============================================================================

class TicketCategory:
    """Represents a ticket category with its settings"""
    def __init__(self, category_id: str, name: str, description: str, 
                 modal_fields: List[Dict], emoji: str = "🎫", 
                 staff_role_id: Optional[int] = None):
        self.id = category_id
        self.name = name
        self.description = description
        self.modal_fields = modal_fields  # List of field definitions
        self.emoji = emoji
        self.staff_role_id = staff_role_id
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'modal_fields': self.modal_fields,
            'emoji': self.emoji,
            'staff_role_id': self.staff_role_id
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(
            category_id=data['id'],
            name=data['name'],
            description=data['description'],
            modal_fields=data['modal_fields'],
            emoji=data.get('emoji', '🎫'),
            staff_role_id=data.get('staff_role_id')
        )


# =============================================================================
# TICKET MODALS (Dynamic per category)
# =============================================================================

class DynamicTicketModal(discord.ui.Modal):
    """Dynamic modal that generates fields based on category configuration"""
    
    def __init__(self, category: TicketCategory, cog: 'Tickets'):
        self.category = category
        self.cog = cog
        super().__init__(title=f"New {category.name} Ticket")
        
        # Dynamically add fields from category config
        for field_config in category.modal_fields:
            field_type = field_config.get('type', 'short')
            style = discord.TextStyle.paragraph if field_type == 'paragraph' else discord.TextStyle.short
            
            self.add_item(
                discord.ui.TextInput(
                    label=field_config['label'],
                    placeholder=field_config.get('placeholder', ''),
                    required=field_config.get('required', True),
                    style=style,
                    max_length=field_config.get('max_length', 1000),
                    min_length=field_config.get('min_length', 1)
                )
            )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        # Collect all field values
        answers = {}
        for i, field in enumerate(self.category.modal_fields):
            answers[field['label']] = self.children[i].value
        
        # Create the ticket
        await self.cog.create_ticket(interaction, self.category, answers)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Handle errors"""
        logger.error(f"Modal error: {error}")
        await interaction.response.send_message(
            "❌ An error occurred. Please try again.",
            ephemeral=True
        )


# =============================================================================
# TICKET VIEWS
# =============================================================================

class TicketCategorySelect(discord.ui.Select):
    """Dropdown for selecting ticket category"""
    
    def __init__(self, categories: List[TicketCategory], cog: 'Tickets'):
        self.cog = cog
        
        options = []
        for cat in categories:
            options.append(
                discord.SelectOption(
                    label=cat.name,
                    description=cat.description,
                    emoji=cat.emoji,
                    value=cat.id
                )
            )
        
        super().__init__(
            placeholder="Select ticket type...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_category_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle category selection"""
        category_id = self.values[0]
        category = self.cog.categories.get(category_id)
        
        if not category:
            await interaction.response.send_message(
                "❌ Category not found. Please try again.",
                ephemeral=True
            )
            return
        
        # Show the appropriate modal
        modal = DynamicTicketModal(category, self.cog)
        await interaction.response.send_modal(modal)


class TicketCreatePanel(discord.ui.View):
    """Main ticket creation panel with dropdown"""
    
    def __init__(self, cog: 'Tickets'):
        super().__init__(timeout=None)  # Persistent
        self.cog = cog
        
        # Add category dropdown when view is created
        self.update_categories()
    
    def update_categories(self):
        """Update dropdown with current categories"""
        # Clear existing items
        self.clear_items()
        
        # Add dropdown if there are categories
        if self.cog.categories:
            self.add_item(TicketCategorySelect(list(self.cog.categories.values()), self.cog))
        
        # Add emergency button (optional)
        emergency_button = discord.ui.Button(
            label="Emergency",
            style=discord.ButtonStyle.danger,
            emoji="🚨",
            custom_id="emergency_ticket",
            row=1
        )
        emergency_button.callback = self.emergency_callback
        self.add_item(emergency_button)
    
    async def emergency_callback(self, interaction: discord.Interaction):
        """Handle emergency ticket (bypasses modal)"""
        # Create emergency category or use default
        emergency_cat = self.cog.categories.get('emergency')
        if not emergency_cat:
            # Create temporary emergency category
            emergency_cat = TicketCategory(
                category_id='emergency',
                name='Emergency',
                description='Urgent assistance needed',
                modal_fields=[
                    {'label': 'Emergency Type', 'placeholder': 'What is the emergency?', 'type': 'short'},
                    {'label': 'Details', 'placeholder': 'Please describe the situation', 'type': 'paragraph'}
                ],
                emoji='🚨'
            )
        
        modal = DynamicTicketModal(emergency_cat, self.cog)
        await interaction.response.send_modal(modal)


class TicketControlPanel(discord.ui.View):
    """Persistent ticket control buttons"""
    
    def __init__(self, cog: 'Tickets', ticket_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.ticket_id = ticket_id
    
    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close ticket button"""
        await self.cog.close_ticket(interaction, self.ticket_id)
    
    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary, emoji="👋", custom_id="claim_ticket")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Claim ticket button"""
        await self.cog.claim_ticket(interaction, self.ticket_id)
    
    @discord.ui.button(label="Add Member", style=discord.ButtonStyle.secondary, emoji="➕", custom_id="add_member")
    async def add_member_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add member to ticket"""
        # Create modal for adding member
        modal = AddMemberModal(self.cog, self.ticket_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, emoji="📄", custom_id="transcript")
    async def transcript_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Generate transcript"""
        await self.cog.generate_transcript(interaction, self.ticket_id)


class AddMemberModal(discord.ui.Modal):
    """Modal for adding a member to a ticket"""
    
    def __init__(self, cog: 'Tickets', ticket_id: int):
        super().__init__(title="Add Member to Ticket")
        self.cog = cog
        self.ticket_id = ticket_id
        
        self.member_input = discord.ui.TextInput(
            label="User ID or Mention",
            placeholder="123456789012345678 or @username",
            required=True,
            style=discord.TextStyle.short
        )
        self.add_item(self.member_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle member addition"""
        # Parse input (could be ID or mention)
        value = self.member_input.value.strip()
        
        # Extract ID from mention if needed
        if value.startswith('<@') and value.endswith('>'):
            value = value.replace('<@', '').replace('>', '').replace('!', '')
        
        try:
            user_id = int(value)
            member = interaction.guild.get_member(user_id)
            
            if not member:
                await interaction.response.send_message(
                    "❌ User not found in this server.",
                    ephemeral=True
                )
                return
            
            # Add member to ticket channel
            await interaction.channel.set_permissions(
                member,
                read_messages=True,
                send_messages=True
            )
            
            await interaction.response.send_message(
                f"✅ Added {member.mention} to this ticket.",
                ephemeral=True
            )
            
            # Log the addition
            await interaction.channel.send(f"👤 {member.mention} was added to the ticket by {interaction.user.mention}")
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid user ID or mention.",
                ephemeral=True
            )


# =============================================================================
# MAIN TICKETS COG
# =============================================================================

class Tickets(commands.Cog):
    """Modular ticket system with per-server configuration"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db  # Your database handler
        self.active_views = {}  # Store persistent views
        self.categories = {}  # Current guild categories (loaded per guild)
        
        # Load categories from database on startup
        asyncio.create_task(self.load_all_configs())
    
    async def load_all_configs(self):
        """Load ticket configurations for all guilds"""
        await self.bot.wait_until_ready()
        
        for guild in self.bot.guilds:
            await self.load_guild_config(guild.id)
        
        logger.info(f"Loaded ticket configs for {len(self.bot.guilds)} guilds")
    
    async def load_guild_config(self, guild_id: int):
        """Load ticket configuration for a specific guild"""
        try:
            # Get guild config from database
            config = await self.db.get_guild_config(guild_id, 'tickets')
            
            if config and 'categories' in config:
                # Load categories
                categories = {}
                for cat_data in config['categories']:
                    category = TicketCategory.from_dict(cat_data)
                    categories[category.id] = category
                
                # Store in memory (keyed by guild_id)
                if not hasattr(self, 'guild_categories'):
                    self.guild_categories = {}
                self.guild_categories[guild_id] = categories
                
                logger.info(f"Loaded {len(categories)} ticket categories for guild {guild_id}")
            else:
                # Initialize with default categories
                await self.create_default_categories(guild_id)
                
        except Exception as e:
            logger.error(f"Failed to load ticket config for guild {guild_id}: {e}")
    
    async def create_default_categories(self, guild_id: int):
        """Create default ticket categories for a guild"""
        default_categories = [
            TicketCategory(
                category_id='support',
                name='General Support',
                description='General questions and help',
                modal_fields=[
                    {'label': 'Subject', 'placeholder': 'Brief summary of your issue', 'type': 'short'},
                    {'label': 'Description', 'placeholder': 'Please describe your issue in detail', 'type': 'paragraph'}
                ],
                emoji='❓'
            ),
            TicketCategory(
                category_id='billing',
                name='Billing/Purchase',
                description='Payment, refunds, and purchase issues',
                modal_fields=[
                    {'label': 'Transaction ID', 'placeholder': 'Your transaction ID (if available)', 'type': 'short'},
                    {'label': 'Issue Description', 'placeholder': 'Describe the billing issue', 'type': 'paragraph'}
                ],
                emoji='💰'
            ),
            TicketCategory(
                category_id='report',
                name='Report Player',
                description='Report rule violations or players',
                modal_fields=[
                    {'label': 'Player Name', 'placeholder': 'Who are you reporting?', 'type': 'short'},
                    {'label': 'Reason', 'placeholder': 'Why are you reporting them?', 'type': 'paragraph'},
                    {'label': 'Evidence', 'placeholder': 'Links to screenshots/videos (optional)', 'type': 'paragraph', 'required': False}
                ],
                emoji='🚩'
            ),
            TicketCategory(
                category_id='application',
                name='Staff Application',
                description='Apply for staff position',
                modal_fields=[
                    {'label': 'Age', 'placeholder': 'Your age', 'type': 'short'},
                    {'label': 'Experience', 'placeholder': 'Previous staff experience', 'type': 'paragraph'},
                    {'label': 'Why you?', 'placeholder': 'Why should we choose you?', 'type': 'paragraph'}
                ],
                emoji='📝'
            )
        ]
        
        # Store in database
        categories_data = [cat.to_dict() for cat in default_categories]
        await self.db.update_guild_config(guild_id, 'tickets', {'categories': categories_data})
        
        # Store in memory
        if not hasattr(self, 'guild_categories'):
            self.guild_categories = {}
        self.guild_categories[guild_id] = {cat.id: cat for cat in default_categories}
        
        logger.info(f"Created default ticket categories for guild {guild_id}")
    
    def get_categories(self, guild_id: int) -> Dict[str, TicketCategory]:
        """Get categories for a guild"""
        if hasattr(self, 'guild_categories'):
            return self.guild_categories.get(guild_id, {})
        return {}
    
    # =========================================================================
    # TICKET CREATION
    # =========================================================================
    
    async def create_ticket(self, interaction: discord.Interaction, 
                           category: TicketCategory, answers: Dict[str, str]):
        """Create a new ticket channel"""
        guild = interaction.guild
        user = interaction.user
        
        # Get guild config
        config = await self.db.get_guild_config(guild.id, 'tickets')
        if not config:
            await interaction.response.send_message(
                "❌ Ticket system not configured. Please run `/ticket-setup` first.",
                ephemeral=True
            )
            return
        
        # Get category channel
        category_channel_id = config.get('category_channel')
        if not category_channel_id:
            await interaction.response.send_message(
                "❌ Ticket category not set. Please run `/ticket-setup`.",
                ephemeral=True
            )
            return
        
        category_channel = guild.get_channel(category_channel_id)
        if not category_channel or not isinstance(category_channel, discord.CategoryChannel):
            await interaction.response.send_message(
                "❌ Ticket category not found.",
                ephemeral=True
            )
            return
        
        # Check for existing open tickets
        existing = await self.db.find_ticket({
            'guild_id': guild.id,
            'user_id': user.id,
            'status': 'open'
        })
        
        if existing:
            # Get the channel if it still exists
            channel = guild.get_channel(existing['channel_id'])
            if channel:
                await interaction.response.send_message(
                    f"❌ You already have an open ticket: {channel.mention}",
                    ephemeral=True
                )
                return
            else:
                # Channel was deleted, update database
                await self.db.update_ticket(existing['id'], {'status': 'orphaned'})
        
        # Create permission overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add staff roles
        staff_role_id = config.get('staff_role')
        if staff_role_id:
            staff_role = guild.get_role(staff_role_id)
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                )
        
        # Add category-specific staff role
        if category.staff_role_id:
            cat_staff_role = guild.get_role(category.staff_role_id)
            if cat_staff_role:
                overwrites[cat_staff_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                )
        
        # Create channel name
        safe_name = user.name.replace(' ', '-').lower()[:20]
        channel_name = f"ticket-{category.id}-{safe_name}"
        
        # Create channel
        try:
            channel = await category_channel.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                topic=f"Ticket: {category.name} | User: {user}"
            )
        except Exception as e:
            logger.error(f"Failed to create ticket channel: {e}")
            await interaction.response.send_message(
                "❌ Failed to create ticket channel. Check permissions.",
                ephemeral=True
            )
            return
        
        # Store ticket in database
        ticket_data = {
            'guild_id': guild.id,
            'channel_id': channel.id,
            'user_id': user.id,
            'user_name': str(user),
            'category_id': category.id,
            'category_name': category.name,
            'answers': answers,
            'status': 'open',
            'claimed_by': None,
            'created_at': datetime.utcnow().isoformat(),
            'closed_at': None
        }
        
        ticket_id = await self.db.create_ticket(ticket_data)
        
        # Create welcome embed
        embed = discord.Embed(
            title=f"🎫 {category.name} Ticket",
            description=f"Welcome {user.mention}!",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        
        # Add answers to embed
        answers_text = ""
        for question, answer in answers.items():
            answers_text += f"**{question}:** {answer}\n"
        
        embed.add_field(name="📋 Information", value=answers_text[:1024], inline=False)
        embed.add_field(name="📌 Ticket ID", value=f"`{ticket_id}`", inline=True)
        embed.add_field(name="📊 Status", value="Open", inline=True)
        
        embed.set_footer(text="Use the buttons below to manage this ticket")
        
        # Send control panel
        view = TicketControlPanel(self, ticket_id)
        await channel.send(content=f"{user.mention} | <@&{staff_role_id}>" if staff_role_id else user.mention, embed=embed, view=view)
        
        # Log creation
        log_channel_id = config.get('log_channel')
        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                log_embed = discord.Embed(
                    title="🎫 New Ticket Created",
                    description=f"**Ticket:** {channel.mention}\n"
                               f"**User:** {user.mention}\n"
                               f"**Category:** {category.name}\n"
                               f"**ID:** `{ticket_id}`",
                    color=0x57F287,
                    timestamp=datetime.utcnow()
                )
                await log_channel.send(embed=log_embed)
        
        # Confirm to user
        await interaction.response.send_message(
            f"✅ Ticket created! {channel.mention}",
            ephemeral=True
        )
        
        logger.info(f"Ticket {ticket_id} created by {user} in {guild}")
    
    # =========================================================================
    # TICKET MANAGEMENT
    # =========================================================================
    
    async def claim_ticket(self, interaction: discord.Interaction, ticket_id: int):
        """Claim a ticket"""
        # Get ticket from database
        ticket = await self.db.get_ticket(ticket_id)
        if not ticket:
            await interaction.response.send_message(
                "❌ Ticket not found.",
                ephemeral=True
            )
            return
        
        # Check if channel still exists
        channel = interaction.guild.get_channel(ticket['channel_id'])
        if not channel:
            await interaction.response.send_message(
                "❌ Ticket channel no longer exists.",
                ephemeral=True
            )
            await self.db.update_ticket(ticket_id, {'status': 'orphaned'})
            return
        
        # Check if already claimed
        if ticket['claimed_by']:
            claimer = interaction.guild.get_member(ticket['claimed_by'])
            await interaction.response.send_message(
                f"❌ This ticket is already claimed by {claimer.mention if claimer else 'someone'}.",
                ephemeral=True
            )
            return
        
        # Update database
        await self.db.update_ticket(ticket_id, {
            'claimed_by': interaction.user.id,
            'claimed_at': datetime.utcnow().isoformat()
        })
        
        # Update channel name
        new_name = f"claimed-{ticket['user_name']}"[:100]
        try:
            await channel.edit(name=new_name)
        except:
            pass
        
        await interaction.response.send_message(
            f"👋 Ticket claimed by {interaction.user.mention}"
        )
        
        logger.info(f"Ticket {ticket_id} claimed by {interaction.user}")
    
    async def close_ticket(self, interaction: discord.Interaction, ticket_id: int):
        """Close a ticket"""
        # Get ticket from database
        ticket = await self.db.get_ticket(ticket_id)
        if not ticket:
            await interaction.response.send_message(
                "❌ Ticket not found.",
                ephemeral=True
            )
            return
        
        # Check if channel still exists
        channel = interaction.guild.get_channel(ticket['channel_id'])
        if not channel:
            await interaction.response.send_message(
                "❌ Ticket channel no longer exists.",
                ephemeral=True
            )
            await self.db.update_ticket(ticket_id, {'status': 'orphaned'})
            return
        
        # Check permissions
        is_owner = interaction.user.id == ticket['user_id']
        is_claimer = interaction.user.id == ticket.get('claimed_by')
        is_staff = interaction.user.guild_permissions.administrator
        
        config = await self.db.get_guild_config(interaction.guild.id, 'tickets')
        staff_role_id = config.get('staff_role') if config else None
        has_staff_role = staff_role_id and staff_role_id in [r.id for r in interaction.user.roles]
        
        if not (is_owner or is_claimer or is_staff or has_staff_role):
            await interaction.response.send_message(
                "❌ You don't have permission to close this ticket.",
                ephemeral=True
            )
            return
        
        # Generate transcript before closing
        await self.generate_transcript(interaction, ticket_id, silent=True)
        
        # Update database
        await self.db.update_ticket(ticket_id, {
            'status': 'closed',
            'closed_by': interaction.user.id,
            'closed_at': datetime.utcnow().isoformat()
        })
        
        # Send closing message
        embed = discord.Embed(
            title="🔒 Ticket Closing",
            description=f"This ticket is being closed by {interaction.user.mention}.\n\n"
                       f"The channel will be deleted in 5 seconds...",
            color=0xED4245
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Log closure
        config = await self.db.get_guild_config(interaction.guild.id, 'tickets')
        log_channel_id = config.get('log_channel') if config else None
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                log_embed = discord.Embed(
                    title="🔒 Ticket Closed",
                    description=f"**Ticket:** {channel.mention}\n"
                               f"**Closed by:** {interaction.user.mention}\n"
                               f"**ID:** `{ticket_id}`",
                    color=0xED4245,
                    timestamp=datetime.utcnow()
                )
                await log_channel.send(embed=log_embed)
        
        # Wait and delete
        await asyncio.sleep(5)
        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user}")
        except:
            logger.error(f"Failed to delete ticket channel {channel.id}")
    
    async def generate_transcript(self, interaction: discord.Interaction, 
                                  ticket_id: int, silent: bool = False):
        """Generate HTML transcript of ticket"""
        ticket = await self.db.get_ticket(ticket_id)
        if not ticket:
            if not silent:
                await interaction.response.send_message("❌ Ticket not found.", ephemeral=True)
            return
        
        channel = interaction.guild.get_channel(ticket['channel_id'])
        if not channel:
            if not silent:
                await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
            return
        
        # Fetch messages
        messages = []
        async for msg in channel.history(limit=1000, oldest_first=True):
            messages.append({
                'author': str(msg.author),
                'author_id': msg.author.id,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat(),
                'attachments': [a.url for a in msg.attachments]
            })
        
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Ticket #{ticket_id} Transcript</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .ticket-header {{ background: #5865F2; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .message {{ background: white; margin: 10px 0; padding: 10px; border-radius: 5px; }}
        .author {{ font-weight: bold; color: #5865F2; }}
        .timestamp {{ color: #999; font-size: 0.8em; }}
        .content {{ margin-top: 5px; }}
        .attachment {{ color: #00aaff; }}
    </style>
</head>
<body>
    <div class="ticket-header">
        <h1>Ticket #{ticket_id} Transcript</h1>
        <p>Category: {ticket['category_name']}</p>
        <p>User: {ticket['user_name']}</p>
        <p>Created: {ticket['created_at']}</p>
        <p>Messages: {len(messages)}</p>
    </div>
"""
        
        for msg in messages:
            html += f"""
    <div class="message">
        <span class="author">{msg['author']}</span>
        <span class="timestamp">{msg['timestamp']}</span>
        <div class="content">{msg['content']}</div>
"""
            if msg['attachments']:
                for url in msg['attachments']:
                    html += f'        <div class="attachment">📎 <a href="{url}">{url}</a></div>\n'
            html += "    </div>\n"
        
        html += "</body></html>"
        
        # Save to file
        transcript_dir = f"data/transcripts/{interaction.guild.id}"
        os.makedirs(transcript_dir, exist_ok=True)
        
        filename = f"{transcript_dir}/ticket_{ticket_id}.html"
        async with aiofiles.open(filename, 'w') as f:
            await f.write(html)
        
        if not silent:
            file = discord.File(filename)
            await interaction.response.send_message(
                "📄 Ticket transcript generated:",
                file=file,
                ephemeral=True
            )
        
        return filename
    
    # =========================================================================
    # SETUP COMMANDS
    # =========================================================================
    
    @commands.hybrid_group(name='ticket', description='Ticket system commands')
    async def ticket(self, ctx: commands.Context):
        """Ticket system commands"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🎫 Ticket System Commands",
                description="Use the subcommands below:",
                color=0x5865F2
            )
            embed.add_field(name="`/ticket setup`", value="Configure ticket system", inline=False)
            embed.add_field(name="`/ticket panel`", value="Send ticket creation panel", inline=False)
            embed.add_field(name="`/ticket categories`", value="Manage ticket categories", inline=False)
            embed.add_field(name="`/ticket config`", value="View current configuration", inline=False)
            
            await ctx.send(embed=embed)
    
    @ticket.command(name='setup', description='Setup ticket system (Admin)')
    @app_commands.describe(
        category='Category for ticket channels',
        log_channel='Channel for ticket logs',
        staff_role='Role to ping for new tickets'
    )
    @commands.has_permissions(administrator=True)
    async def ticket_setup(
        self,
        ctx: commands.Context,
        category: discord.CategoryChannel,
        log_channel: discord.TextChannel,
        staff_role: Optional[discord.Role] = None
    ):
        """Setup ticket system"""
        # Save configuration
        config = {
            'category_channel': category.id,
            'log_channel': log_channel.id
        }
        if staff_role:
            config['staff_role'] = staff_role.id
        
        await self.db.update_guild_config(ctx.guild.id, 'tickets', config)
        
        # Load categories if not exist
        if ctx.guild.id not in getattr(self, 'guild_categories', {}):
            await self.create_default_categories(ctx.guild.id)
        
        embed = discord.Embed(
            title="✅ Ticket System Configured",
            color=0x57F287,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="📁 Category", value=category.mention)
        embed.add_field(name="📋 Log Channel", value=log_channel.mention)
        if staff_role:
            embed.add_field(name="👥 Staff Role", value=staff_role.mention)
        
        await ctx.send(embed=embed)
        
        logger.info(f"Ticket system setup in {ctx.guild}")
    
    @ticket.command(name='panel', description='Send ticket creation panel')
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx: commands.Context):
        """Send ticket creation panel"""
        # Check if configured
        config = await self.db.get_guild_config(ctx.guild.id, 'tickets')
        if not config:
            await ctx.send("❌ Please run `/ticket setup` first.")
            return
        
        # Create panel embed
        embed = discord.Embed(
            title="🎫 Support Tickets",
            description="Need help? Select a ticket type below!",
            color=0x5865F2
        )
        
        # Add categories to embed
        categories = self.get_categories(ctx.guild.id)
        if categories:
            cats_text = ""
            for cat in categories.values():
                cats_text += f"{cat.emoji} **{cat.name}** - {cat.description}\n"
            embed.add_field(name="Available Options", value=cats_text, inline=False)
        
        embed.set_footer(text="Select an option from the dropdown below")
        
        # Create view with dropdown
        view = TicketCreatePanel(self)
        
        await ctx.send(embed=embed, view=view)
        await ctx.send("✅ Panel sent!", ephemeral=True)
    
    @ticket.group(name='categories', description='Manage ticket categories')
    @commands.has_permissions(administrator=True)
    async def ticket_categories(self, ctx: commands.Context):
        """Manage ticket categories"""
        if ctx.invoked_subcommand is None:
            categories = self.get_categories(ctx.guild.id)
            
            embed = discord.Embed(
                title="📋 Ticket Categories",
                color=0x5865F2
            )
            
            if categories:
                for cat in categories.values():
                    embed.add_field(
                        name=f"{cat.emoji} {cat.name}",
                        value=f"ID: `{cat.id}`\n{cat.description}",
                        inline=False
                    )
            else:
                embed.description = "No categories configured."
            
            await ctx.send(embed=embed)
    
    @ticket_categories.command(name='add', description='Add a ticket category')
    @app_commands.describe(
        name='Category name',
        description='Category description',
        emoji='Emoji for the category',
        modal_fields='JSON of modal fields (advanced)'
    )
    async def category_add(
        self,
        ctx: commands.Context,
        name: str,
        description: str,
        emoji: str = '🎫',
        modal_fields: str = None
    ):
        """Add a ticket category"""
        # Generate ID from name
        category_id = name.lower().replace(' ', '_')
        
        # Default modal fields if none provided
        if not modal_fields:
            fields = [
                {'label': 'Subject', 'placeholder': 'Brief summary', 'type': 'short'},
                {'label': 'Description', 'placeholder': 'Detailed description', 'type': 'paragraph'}
            ]
        else:
            try:
                fields = json.loads(modal_fields)
            except:
                await ctx.send("❌ Invalid JSON for modal fields.")
                return
        
        # Create category
        category = TicketCategory(
            category_id=category_id,
            name=name,
            description=description,
            modal_fields=fields,
            emoji=emoji
        )
        
        # Get existing categories
        categories = self.get_categories(ctx.guild.id)
        categories[category_id] = category
        
        # Save to database
        categories_data = [cat.to_dict() for cat in categories.values()]
        await self.db.update_guild_config(ctx.guild.id, 'tickets', 
                                         {'categories': categories_data})
        
        # Update memory
        if not hasattr(self, 'guild_categories'):
            self.guild_categories = {}
        self.guild_categories[ctx.guild.id] = categories
        
        await ctx.send(f"✅ Added category: {emoji} **{name}**")
    
    @ticket_categories.command(name='remove', description='Remove a ticket category')
    @app_commands.describe(category_id='ID of the category to remove')
    async def category_remove(self, ctx: commands.Context, category_id: str):
        """Remove a ticket category"""
        categories = self.get_categories(ctx.guild.id)
        
        if category_id not in categories:
            await ctx.send(f"❌ Category `{category_id}` not found.")
            return
        
        removed = categories.pop(category_id)
        
        # Save to database
        categories_data = [cat.to_dict() for cat in categories.values()]
        await self.db.update_guild_config(ctx.guild.id, 'tickets', 
                                         {'categories': categories_data})
        
        # Update memory
        self.guild_categories[ctx.guild.id] = categories
        
        await ctx.send(f"✅ Removed category: {removed.emoji} **{removed.name}**")
    
    @ticket.command(name='config', description='View current ticket configuration')
    @commands.has_permissions(administrator=True)
    async def ticket_config(self, ctx: commands.Context):
        """View current ticket configuration"""
        config = await self.db.get_guild_config(ctx.guild.id, 'tickets')
        
        embed = discord.Embed(
            title="🎫 Ticket Configuration",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        
        if config:
            category_channel = ctx.guild.get_channel(config.get('category_channel', 0))
            log_channel = ctx.guild.get_channel(config.get('log_channel', 0))
            staff_role = ctx.guild.get_role(config.get('staff_role', 0))
            
            embed.add_field(
                name="📁 Category Channel",
                value=category_channel.mention if category_channel else "❌ Not set",
                inline=False
            )
            embed.add_field(
                name="📋 Log Channel",
                value=log_channel.mention if log_channel else "❌ Not set",
                inline=False
            )
            embed.add_field(
                name="👥 Staff Role",
                value=staff_role.mention if staff_role else "❌ Not set",
                inline=False
            )
            
            # Categories
            categories = self.get_categories(ctx.guild.id)
            if categories:
                cats_text = "\n".join([f"{c.emoji} {c.name}" for c in categories.values()])
                embed.add_field(name="📋 Categories", value=cats_text, inline=False)
        else:
            embed.description = "❌ Not configured. Run `/ticket setup`"
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Tickets(bot))