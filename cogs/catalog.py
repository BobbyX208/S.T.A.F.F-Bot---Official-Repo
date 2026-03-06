import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional, Dict, Any, List
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG_FILE = 'catalog_config.json'
CATALOG_FILE = 'catalog.json'

class Config:
    def __init__(self):
        self.data = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                return {}
        return {}
    
    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        return self.data.get(str(guild_id), {})

class Catalog:
    def __init__(self):
        self.data = self.load_catalog()
    
    def load_catalog(self) -> Dict[str, Any]:
        if os.path.exists(CATALOG_FILE):
            try:
                with open(CATALOG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading catalog: {e}")
                return {}
        return {}
    
    def save_catalog(self):
        try:
            with open(CATALOG_FILE, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving catalog: {e}")
    
    def get_categories(self, guild_id: int) -> List[str]:
        return list(self.data.get(str(guild_id), {}).keys())
    
    def get_items(self, guild_id: int, category: str) -> List[Dict]:
        return self.data.get(str(guild_id), {}).get(category, [])

# ============================================================================
# BUY BUTTON - Must have custom_id
# ============================================================================

class BuyButton(discord.ui.Button):
    def __init__(self, guild_id: int, category: str, item_name: str, price: float):
        # Create a unique custom_id for each button
        custom_id = f"buy_{guild_id}_{category}_{item_name}".replace(" ", "_")[:100]
        
        super().__init__(
            label=f"Buy {item_name} (${price})",
            style=discord.ButtonStyle.green,
            custom_id=custom_id  # REQUIRED for persistent views
        )
        self.guild_id = guild_id
        self.category = category
        self.item_name = item_name
        self.price = price
    
    async def callback(self, interaction: discord.Interaction):
        """Handle buy button click"""
        config = Config()
        guild_config = config.get_guild_config(self.guild_id)
        
        # Check if ticket system is configured
        if not guild_config.get('ticket_category_id'):
            await interaction.response.send_message(
                "❌ Ticket system not configured. Please contact an admin.",
                ephemeral=True
            )
            return
        
        # Get the ticket category
        category = interaction.guild.get_channel(int(guild_config['ticket_category_id']))
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                "❌ Ticket category not found. Please contact an admin.",
                ephemeral=True
            )
            return
        
        # Get staff role
        staff_role = None
        if guild_config.get('staff_role_id'):
            staff_role = interaction.guild.get_role(int(guild_config['staff_role_id']))
        
        # Check for existing open ticket
        for channel in category.channels:
            if channel.name.startswith(f"ticket-{interaction.user.name.lower()}"):
                await interaction.response.send_message(
                    f"❌ You already have an open ticket: {channel.mention}",
                    ephemeral=True
                )
                return
        
        # Create permission overwrites
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, 
                send_messages=True, 
                read_message_history=True
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
        }
        
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True, 
                send_messages=True, 
                read_message_history=True
            )
        
        # Create channel name
        safe_name = interaction.user.name.replace(" ", "-").lower()[:20]
        safe_item = self.item_name.replace(" ", "-").lower()[:20]
        channel_name = f"ticket-{safe_name}-{safe_item}"
        
        try:
            # Create ticket channel
            channel = await interaction.guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Purchase: {self.item_name} | User: {interaction.user}"
            )
            
            # Create ticket embed
            embed = discord.Embed(
                title=f"🎫 Purchase Ticket: {self.item_name}",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name="📦 Item", value=self.item_name, inline=True)
            embed.add_field(name="📁 Category", value=self.category, inline=True)
            embed.add_field(name="💰 Price", value=f"${self.price}", inline=True)
            embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
            
            embed.set_footer(text="A staff member will assist you shortly.")
            
            # Create close button for the ticket
            close_view = discord.ui.View(timeout=None)
            close_button = discord.ui.Button(
                label="Close Ticket",
                style=discord.ButtonStyle.danger,
                emoji="🔒",
                custom_id=f"close_{channel.id}"  # Unique custom_id
            )
            
            async def close_callback(close_interaction: discord.Interaction):
                if not close_interaction.user.guild_permissions.administrator and \
                   close_interaction.user != interaction.user and \
                   (not staff_role or staff_role not in close_interaction.user.roles):
                    await close_interaction.response.send_message(
                        "❌ You don't have permission to close this ticket.",
                        ephemeral=True
                    )
                    return
                
                await close_interaction.response.send_message(
                    "🔒 Closing ticket in 5 seconds...",
                    ephemeral=True
                )
                await asyncio.sleep(5)
                await channel.delete()
            
            close_button.callback = close_callback
            close_view.add_item(close_button)
            
            # Send welcome message
            mention_text = f"{interaction.user.mention}"
            if staff_role:
                mention_text += f" {staff_role.mention}"
            
            await channel.send(content=mention_text, embed=embed, view=close_view)
            
            # Confirm to user
            await interaction.response.send_message(
                f"✅ Ticket created: {channel.mention}",
                ephemeral=True
            )
            
            # Log to configured channel if exists
            if guild_config.get('log_channel_id'):
                log_channel = interaction.guild.get_channel(int(guild_config['log_channel_id']))
                if log_channel:
                    log_embed = discord.Embed(
                        title="🎫 New Purchase Ticket",
                        description=f"**User:** {interaction.user.mention}\n"
                                   f"**Item:** {self.item_name}\n"
                                   f"**Category:** {self.category}\n"
                                   f"**Price:** ${self.price}\n"
                                   f"**Ticket:** {channel.mention}",
                        color=discord.Color.blue(),
                        timestamp=discord.utils.utcnow()
                    )
                    await log_channel.send(embed=log_embed)
            
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await interaction.response.send_message(
                "❌ Failed to create ticket. Please try again or contact an admin.",
                ephemeral=True
            )

# ============================================================================
# CATEGORY SELECT - Must have custom_id
# ============================================================================

class CategorySelect(discord.ui.Select):
    def __init__(self, guild_id: int, catalog: Catalog):
        self.guild_id = guild_id
        self.catalog = catalog
        categories = catalog.get_categories(guild_id)
        
        options = []
        for category in categories:
            options.append(discord.SelectOption(
                label=category,
                description=f"View items in {category}",
                emoji="📦"
            ))
        
        # If no categories, add a placeholder
        if not options:
            options.append(discord.SelectOption(
                label="No categories",
                description="Add items first using /add-item",
                emoji="⚠️",
                default=True
            ))
        
        super().__init__(
            placeholder="Select a category...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"cat_select_{guild_id}"  # REQUIRED for persistent views
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle category selection"""
        if self.values[0] == "No categories" or not self.values:
            await interaction.response.send_message(
                "❌ No categories available. Please add items first using `/add-item`.",
                ephemeral=True
            )
            return
        
        selected_category = self.values[0]
        items = self.catalog.get_items(self.guild_id, selected_category)
        
        if not items:
            await interaction.response.send_message(
                f"❌ No items in {selected_category}.",
                ephemeral=True
            )
            return
        
        # Create embed with items
        embed = discord.Embed(
            title=f"📦 {selected_category}",
            description=f"Items available in **{selected_category}**:",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        for item in items:
            embed.add_field(
                name=f"**{item['name']}** - 💰 ${item['price']}",
                value=item.get('description', 'No description provided'),
                inline=False
            )
        
        # Create view with buy buttons
        view = discord.ui.View(timeout=None)
        for item in items:
            button = BuyButton(
                self.guild_id,
                selected_category,
                item['name'],
                item['price']
            )
            view.add_item(button)
        
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )

# ============================================================================
# CATALOG VIEW - Main persistent view
# ============================================================================

class CatalogView(discord.ui.View):
    def __init__(self, guild_id: int, catalog: Catalog):
        super().__init__(timeout=None)
        self.add_item(CategorySelect(guild_id, catalog))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

# ============================================================================
# SETUP MODAL
# ============================================================================

class SetupModal(discord.ui.Modal, title="🎫 Ticket System Setup"):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
    
    staff_role = discord.ui.TextInput(
        label="Staff Role ID",
        placeholder="Enter the role ID for staff (e.g., 123456789012345678)",
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
        label="Log Channel ID (Optional)",
        placeholder="Enter channel ID for logs (or leave blank)",
        required=False,
        max_length=20
    )
    
    catalog_message = discord.ui.TextInput(
        label="Catalog Message",
        placeholder="Welcome to our shop! Click below to browse items.",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle setup form submission"""
        try:
            staff_role_id = int(self.staff_role.value)
            ticket_category_id = int(self.ticket_category.value)
            log_channel_id = int(self.log_channel.value) if self.log_channel.value else None
            
            # Validate role
            role = interaction.guild.get_role(staff_role_id)
            if not role:
                await interaction.response.send_message(
                    "❌ Invalid staff role ID. Please check and try again.",
                    ephemeral=True
                )
                return
            
            # Validate category
            category = interaction.guild.get_channel(ticket_category_id)
            if not category or not isinstance(category, discord.CategoryChannel):
                await interaction.response.send_message(
                    "❌ Invalid ticket category ID. Please provide a valid category channel.",
                    ephemeral=True
                )
                return
            
            # Validate log channel if provided
            if log_channel_id:
                log_ch = interaction.guild.get_channel(log_channel_id)
                if not log_ch or not isinstance(log_ch, discord.TextChannel):
                    await interaction.response.send_message(
                        "❌ Invalid log channel ID. Please provide a valid text channel.",
                        ephemeral=True
                    )
                    return
            
            # Save configuration
            guild_config = self.cog.config.get_guild_config(interaction.guild_id)
            guild_config['staff_role_id'] = staff_role_id
            guild_config['ticket_category_id'] = ticket_category_id
            guild_config['log_channel_id'] = log_channel_id
            
            self.cog.config.data[str(interaction.guild_id)] = guild_config
            self.cog.config.save_config()
            
            # Create catalog embed
            embed = discord.Embed(
                title="🛒 Server Catalog",
                description=self.catalog_message.value,
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text="Select a category below to view items")
            
            # Create persistent view
            view = CatalogView(interaction.guild_id, self.cog.catalog)
            
            # Send catalog message
            await interaction.channel.send(embed=embed, view=view)
            
            # Confirm setup
            confirm_embed = discord.Embed(
                title="✅ Setup Complete!",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            confirm_embed.add_field(name="Staff Role", value=role.mention, inline=True)
            confirm_embed.add_field(name="Ticket Category", value=category.mention, inline=True)
            if log_channel_id:
                log_ch = interaction.guild.get_channel(log_channel_id)
                confirm_embed.add_field(name="Log Channel", value=log_ch.mention, inline=True)
            
            await interaction.response.send_message(embed=confirm_embed, ephemeral=True)
            
            logger.info(f"Ticket system setup complete for guild {interaction.guild_id}")
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter valid numeric IDs.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Setup error: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

# ============================================================================
# ADD ITEM MODAL
# ============================================================================

class AddItemModal(discord.ui.Modal, title="📦 Add Catalog Item"):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
    
    category = discord.ui.TextInput(
        label="Category",
        placeholder="e.g., 'Gold', 'Accounts', 'Services'",
        required=True,
        max_length=50
    )
    
    name = discord.ui.TextInput(
        label="Item Name",
        placeholder="e.g., '1000 Gold', 'Premium Account'",
        required=True,
        max_length=100
    )
    
    price = discord.ui.TextInput(
        label="Price",
        placeholder="e.g., '10.99' (numbers only)",
        required=True,
        max_length=10
    )
    
    description = discord.ui.TextInput(
        label="Description",
        placeholder="Describe what the buyer gets...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle add item form submission"""
        try:
            price = float(self.price.value)
            
            guild_id = str(interaction.guild_id)
            
            # Initialize guild data if needed
            if guild_id not in self.cog.catalog.data:
                self.cog.catalog.data[guild_id] = {}
            
            if self.category.value not in self.cog.catalog.data[guild_id]:
                self.cog.catalog.data[guild_id][self.category.value] = []
            
            # Add item
            item_data = {
                'name': self.name.value,
                'price': price,
                'description': self.description.value
            }
            
            self.cog.catalog.data[guild_id][self.category.value].append(item_data)
            self.cog.catalog.save_catalog()
            
            # Create confirmation embed
            embed = discord.Embed(
                title="✅ Item Added Successfully",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="📁 Category", value=self.category.value, inline=True)
            embed.add_field(name="📦 Item", value=self.name.value, inline=True)
            embed.add_field(name="💰 Price", value=f"${price:.2f}", inline=True)
            embed.add_field(name="📝 Description", value=self.description.value, inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log to configured channel
            guild_config = self.cog.config.get_guild_config(interaction.guild_id)
            if guild_config.get('log_channel_id'):
                log_channel = interaction.guild.get_channel(int(guild_config['log_channel_id']))
                if log_channel:
                    log_embed = discord.Embed(
                        title="📦 New Catalog Item",
                        description=f"**Added by:** {interaction.user.mention}",
                        color=discord.Color.blue(),
                        timestamp=discord.utils.utcnow()
                    )
                    log_embed.add_field(name="Category", value=self.category.value)
                    log_embed.add_field(name="Item", value=self.name.value)
                    log_embed.add_field(name="Price", value=f"${price:.2f}")
                    await log_channel.send(embed=log_embed)
            
            logger.info(f"Item added to catalog in guild {interaction.guild_id}: {self.name.value}")
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid price format. Please use numbers only (e.g., 10.99).",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Add item error: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

# ============================================================================
# MAIN COG
# ============================================================================

class PricingTicketSystem(commands.Cog):
    """Pricing ticket system with catalog and automatic ticket creation"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = Config()
        self.catalog = Catalog()
        logger.info("PricingTicketSystem cog initialized")
    
    async def cog_load(self):
        """Called when cog is loaded - register persistent views"""
        # Register all persistent views for all guilds
        for guild in self.bot.guilds:
            try:
                # Create and add view for this guild
                view = CatalogView(guild.id, self.catalog)
                self.bot.add_view(view)
                logger.info(f"Registered catalog view for guild {guild.id}")
            except Exception as e:
                logger.error(f"Failed to register view for guild {guild.id}: {e}")
    
    @app_commands.command(name="catalog-setup", description="Configure the ticket system")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Setup the ticket system"""
        await interaction.response.send_modal(SetupModal(self))
    
    @app_commands.command(name="add-item", description="Add an item to the catalog")
    @app_commands.default_permissions(administrator=True)
    async def add_item(self, interaction: discord.Interaction):
        """Add an item to the catalog"""
        await interaction.response.send_modal(AddItemModal(self))
    
    @app_commands.command(name="refresh-catalog", description="Refresh the catalog message")
    @app_commands.default_permissions(administrator=True)
    async def refresh_catalog(self, interaction: discord.Interaction):
        """Refresh the catalog (send a new panel)"""
        guild_config = self.config.get_guild_config(interaction.guild_id)
        
        if not guild_config.get('catalog_channel_id'):
            await interaction.response.send_message(
                "❌ Please run `/setup` first to configure the catalog.",
                ephemeral=True
            )
            return
        
        # Get the catalog channel
        channel = interaction.guild.get_channel(int(guild_config['catalog_channel_id']))
        if not channel:
            await interaction.response.send_message(
                "❌ Catalog channel not found.",
                ephemeral=True
            )
            return
        
        # Create catalog embed
        embed = discord.Embed(
            title="🛒 Server Catalog",
            description=guild_config.get('catalog_message', 'Welcome to our shop!'),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        # Create view
        view = CatalogView(interaction.guild_id, self.catalog)
        
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Catalog refreshed!", ephemeral=True)
    
    @app_commands.command(name="catalog-status", description="View catalog status")
    @app_commands.default_permissions(administrator=True)
    async def catalog_status(self, interaction: discord.Interaction):
        """View catalog status"""
        guild_config = self.config.get_guild_config(interaction.guild_id)
        categories = self.catalog.get_categories(interaction.guild_id)
        
        embed = discord.Embed(
            title="📊 Catalog Status",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        # Configuration status
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
        
        # Catalog stats
        total_items = 0
        for category in categories:
            items = self.catalog.get_items(interaction.guild_id, category)
            total_items += len(items)
        
        embed.add_field(name="Categories", value=str(len(categories)), inline=True)
        embed.add_field(name="Total Items", value=str(total_items), inline=True)
        
        if categories:
            cats = "\n".join([f"• {c}" for c in categories[:10]])
            embed.add_field(name="Categories List", value=cats[:1024], inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(PricingTicketSystem(bot))
