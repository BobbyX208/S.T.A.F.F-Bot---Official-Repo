"""
Modular Ticket System for S.T.A.F.F. Bot
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional, Dict, Any, List
import logging
import asyncio
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TICKET_CONFIG_FILE = 'tickets_config.json'
TICKETS_FILE = 'tickets_data.json'

class TicketConfig:
    def __init__(self):
        self.data = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        if os.path.exists(TICKET_CONFIG_FILE):
            try:
                with open(TICKET_CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading ticket config: {e}")
                return {}
        return {}
    
    def save_config(self):
        try:
            with open(TICKET_CONFIG_FILE, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving ticket config: {e}")
    
    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        return self.data.get(str(guild_id), {})

class TicketData:
    def __init__(self):
        self.data = self.load_data()
    
    def load_data(self) -> Dict[str, Any]:
        if os.path.exists(TICKETS_FILE):
            try:
                with open(TICKETS_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading tickets: {e}")
                return {}
        return {}
    
    def save_data(self):
        try:
            with open(TICKETS_FILE, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving tickets: {e}")
    
    def create_ticket(self, guild_id: int, ticket_data: dict) -> int:
        """Create a new ticket and return ID"""
        guild_id_str = str(guild_id)
        
        if guild_id_str not in self.data:
            self.data[guild_id_str] = []
        
        ticket_id = len(self.data[guild_id_str]) + 1
        ticket_data['id'] = ticket_id
        ticket_data['created_at'] = datetime.utcnow().isoformat()
        self.data[guild_id_str].append(ticket_data)
        self.save_data()
        return ticket_id
    
    def get_ticket(self, guild_id: int, ticket_id: int) -> Optional[dict]:
        """Get ticket by ID"""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.data:
            return None
        
        for ticket in self.data[guild_id_str]:
            if ticket.get('id') == ticket_id:
                return ticket
        return None
    
    def find_ticket(self, guild_id: int, **kwargs) -> Optional[dict]:
        """Find ticket matching criteria"""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.data:
            return None
        
        for ticket in self.data[guild_id_str]:
            match = True
            for key, value in kwargs.items():
                if ticket.get(key) != value:
                    match = False
                    break
            if match:
                return ticket
        return None
    
    def update_ticket(self, guild_id: int, ticket_id: int, updates: dict):
        """Update ticket information"""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.data:
            return
        
        for ticket in self.data[guild_id_str]:
            if ticket.get('id') == ticket_id:
                ticket.update(updates)
                break
        
        self.save_data()

# ============================================================================
# TICKET SETUP MODAL
# ============================================================================

class TicketSetupModal(discord.ui.Modal, title="🎫 Ticket System Setup"):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
    
    staff_role = discord.ui.TextInput(
        label="Staff Role ID",
        placeholder="Enter the role ID for staff",
        required=True,
        max_length=20
    )
    
    ticket_category = discord.ui.TextInput(
        label="Ticket Category ID",
        placeholder="Enter the category ID for tickets",
        required=True,
        max_length=20
    )
    
    log_channel = discord.ui.TextInput(
        label="Log Channel ID",
        placeholder="Enter channel ID for logs",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle setup form submission"""
        try:
            staff_role_id = int(self.staff_role.value)
            ticket_category_id = int(self.ticket_category.value)
            log_channel_id = int(self.log_channel.value)
            
            # Validate role
            role = interaction.guild.get_role(staff_role_id)
            if not role:
                await interaction.response.send_message(
                    "❌ Invalid staff role ID.",
                    ephemeral=True
                )
                return
            
            # Validate category
            category = interaction.guild.get_channel(ticket_category_id)
            if not category or not isinstance(category, discord.CategoryChannel):
                await interaction.response.send_message(
                    "❌ Invalid ticket category ID.",
                    ephemeral=True
                )
                return
            
            # Validate log channel
            log_ch = interaction.guild.get_channel(log_channel_id)
            if not log_ch or not isinstance(log_ch, discord.TextChannel):
                await interaction.response.send_message(
                    "❌ Invalid log channel ID.",
                    ephemeral=True
                )
                return
            
            # Save configuration
            guild_config = self.cog.config.get_guild_config(interaction.guild_id)
            guild_config.update({
                'staff_role_id': staff_role_id,
                'ticket_category_id': ticket_category_id,
                'log_channel_id': log_channel_id
            })
            
            self.cog.config.data[str(interaction.guild_id)] = guild_config
            self.cog.config.save_config()
            
            # Create ticket panel button
            view = discord.ui.View(timeout=None)
            button = discord.ui.Button(
                label="Create Ticket",
                style=discord.ButtonStyle.primary,
                emoji="🎫",
                custom_id=f"create_ticket_{interaction.guild_id}"
            )
            
            async def button_callback(btn_interaction: discord.Interaction):
                await self.cog.create_ticket_modal(btn_interaction)
            
            button.callback = button_callback
            view.add_item(button)
            
            # Send setup confirmation
            embed = discord.Embed(
                title="🎫 Ticket System",
                description="Click the button below to create a support ticket.",
                color=discord.Color.blue()
            )
            
            await interaction.channel.send(embed=embed, view=view)
            
            # Confirm setup
            confirm_embed = discord.Embed(
                title="✅ Ticket System Setup Complete!",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            confirm_embed.add_field(name="Staff Role", value=role.mention, inline=True)
            confirm_embed.add_field(name="Ticket Category", value=category.mention, inline=True)
            confirm_embed.add_field(name="Log Channel", value=log_ch.mention, inline=True)
            
            await interaction.response.send_message(embed=confirm_embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter valid numeric IDs.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Setup error: {e}")
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )

# ============================================================================
# TICKET CREATE MODAL
# ============================================================================

class TicketCreateModal(discord.ui.Modal, title="🎫 Create Support Ticket"):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
    
    subject = discord.ui.TextInput(
        label="Subject",
        placeholder="Brief summary of your issue",
        required=True,
        max_length=100
    )
    
    description = discord.ui.TextInput(
        label="Description",
        placeholder="Please describe your issue in detail",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle ticket creation"""
        await self.cog.create_ticket_channel(
            interaction, 
            self.subject.value, 
            self.description.value
        )

# ============================================================================
# TICKET CONTROL BUTTONS
# ============================================================================

class TicketControlView(discord.ui.View):
    def __init__(self, cog, ticket_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.ticket_id = ticket_id
        
        # Close button
        close_btn = discord.ui.Button(
            label="Close Ticket",
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            custom_id=f"close_{ticket_id}"
        )
        close_btn.callback = self.close_callback
        self.add_item(close_btn)
    
    async def close_callback(self, interaction: discord.Interaction):
        """Handle ticket closure"""
        await self.cog.close_ticket(interaction, self.ticket_id)

# ============================================================================
# MAIN TICKETS COG
# ============================================================================

class Tickets(commands.Cog):
    """Support ticket system"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = TicketConfig()
        self.tickets = TicketData()
        logger.info("Tickets cog initialized")
    
    async def cog_load(self):
        """Register persistent views"""
        await self.bot.wait_until_ready()
        
        # Register create ticket buttons for all guilds
        for guild in self.bot.guilds:
            view = discord.ui.View(timeout=None)
            button = discord.ui.Button(
                label="Create Ticket",
                style=discord.ButtonStyle.primary,
                emoji="🎫",
                custom_id=f"create_ticket_{guild.id}"
            )
            
            async def make_callback(guild_id):
                async def callback(interaction: discord.Interaction):
                    if interaction.guild_id == guild_id:
                        await self.create_ticket_modal(interaction)
                return callback
            
            button.callback = await make_callback(guild.id)
            view.add_item(button)
            self.bot.add_view(view)
            logger.info(f"Registered ticket view for guild {guild.id}")
    
    async def create_ticket_modal(self, interaction: discord.Interaction):
        """Show ticket creation modal"""
        await interaction.response.send_modal(TicketCreateModal(self))
    
    async def create_ticket_channel(self, interaction: discord.Interaction, subject: str, description: str):
        """Create actual ticket channel"""
        guild_config = self.config.get_guild_config(interaction.guild_id)
        
        if not guild_config.get('ticket_category_id'):
            await interaction.response.send_message(
                "❌ Ticket system not configured.",
                ephemeral=True
            )
            return
        
        # Get category
        category = interaction.guild.get_channel(int(guild_config['ticket_category_id']))
        if not category:
            await interaction.response.send_message(
                "❌ Ticket category not found.",
                ephemeral=True
            )
            return
        
        # Check for existing ticket
        for channel in category.channels:
            if channel.name.startswith(f"ticket-{interaction.user.name.lower()}"):
                await interaction.response.send_message(
                    f"❌ You already have a ticket: {channel.mention}",
                    ephemeral=True
                )
                return
        
        # Get staff role
        staff_role = None
        if guild_config.get('staff_role_id'):
            staff_role = interaction.guild.get_role(int(guild_config['staff_role_id']))
        
        # Create permissions
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        
        # Create channel
        safe_name = interaction.user.name.replace(" ", "-").lower()[:20]
        channel = await interaction.guild.create_text_channel(
            f"ticket-{safe_name}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket: {subject}"
        )
        
        # Save to database
        ticket_id = self.tickets.create_ticket(interaction.guild_id, {
            'channel_id': channel.id,
            'user_id': interaction.user.id,
            'user_name': str(interaction.user),
            'subject': subject,
            'description': description,
            'status': 'open',
            'claimed_by': None
        })
        
        # Create welcome embed
        embed = discord.Embed(
            title=f"🎫 Ticket #{ticket_id}",
            description=f"Welcome {interaction.user.mention}!",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Subject", value=subject, inline=False)
        embed.add_field(name="Description", value=description, inline=False)
        
        # Add control view
        view = TicketControlView(self, ticket_id)
        
        mention = f"{interaction.user.mention}"
        if staff_role:
            mention += f" {staff_role.mention}"
        
        await channel.send(content=mention, embed=embed, view=view)
        
        # Confirm
        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )
        
        # Log
        if guild_config.get('log_channel_id'):
            log_ch = interaction.guild.get_channel(int(guild_config['log_channel_id']))
            if log_ch:
                log_embed = discord.Embed(
                    title="🎫 New Ticket",
                    description=f"**User:** {interaction.user.mention}\n"
                               f"**Subject:** {subject}\n"
                               f"**Ticket:** {channel.mention}",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                await log_ch.send(embed=log_embed)
    
    async def close_ticket(self, interaction: discord.Interaction, ticket_id: int):
        """Close a ticket"""
        ticket = self.tickets.get_ticket(interaction.guild_id, ticket_id)
        if not ticket:
            await interaction.response.send_message("❌ Ticket not found.", ephemeral=True)
            return
        
        # Check permissions
        guild_config = self.config.get_guild_config(interaction.guild_id)
        staff_role = None
        if guild_config.get('staff_role_id'):
            staff_role = interaction.guild.get_role(int(guild_config['staff_role_id']))
        
        is_owner = interaction.user.id == ticket['user_id']
        is_staff = staff_role and staff_role in interaction.user.roles
        is_admin = interaction.user.guild_permissions.administrator
        
        if not (is_owner or is_staff or is_admin):
            await interaction.response.send_message(
                "❌ You don't have permission to close this ticket.",
                ephemeral=True
            )
            return
        
        # Update database
        self.tickets.update_ticket(interaction.guild_id, ticket_id, {
            'status': 'closed',
            'closed_by': interaction.user.id,
            'closed_at': datetime.utcnow().isoformat()
        })
        
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        
        try:
            await interaction.channel.delete()
        except:
            pass
    
    # =========================================================================
    # SLASH COMMANDS
    # =========================================================================
    
    @app_commands.command(name="ticket-setup", description="Setup the ticket system")
    @app_commands.default_permissions(administrator=True)
    async def ticket_setup(self, interaction: discord.Interaction):
        """Setup ticket system"""
        await interaction.response.send_modal(TicketSetupModal(self))
    
    @app_commands.command(name="ticket-status", description="View ticket system status")
    @app_commands.default_permissions(administrator=True)
    async def ticket_status(self, interaction: discord.Interaction):
        """View ticket system status"""
        guild_config = self.config.get_guild_config(interaction.guild_id)
        
        embed = discord.Embed(
            title="🎫 Ticket System Status",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if guild_config.get('staff_role_id'):
            role = interaction.guild.get_role(int(guild_config['staff_role_id']))
            embed.add_field(name="Staff Role", value=role.mention if role else "Unknown", inline=True)
        else:
            embed.add_field(name="Staff Role", value="❌ Not set", inline=True)
        
        if guild_config.get('ticket_category_id'):
            category = interaction.guild.get_channel(int(guild_config['ticket_category_id']))
            embed.add_field(name="Ticket Category", value=category.mention if category else "Unknown", inline=True)
        else:
            embed.add_field(name="Ticket Category", value="❌ Not set", inline=True)
        
        if guild_config.get('log_channel_id'):
            log_ch = interaction.guild.get_channel(int(guild_config['log_channel_id']))
            embed.add_field(name="Log Channel", value=log_ch.mention if log_ch else "Unknown", inline=True)
        else:
            embed.add_field(name="Log Channel", value="❌ Not set", inline=True)
        
        # Count tickets
        guild_id_str = str(interaction.guild_id)
        if guild_id_str in self.tickets.data:
            tickets = self.tickets.data[guild_id_str]
            open_tickets = sum(1 for t in tickets if t.get('status') == 'open')
            embed.add_field(name="Open Tickets", value=str(open_tickets), inline=True)
            embed.add_field(name="Total Tickets", value=str(len(tickets)), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))