import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional, Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
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
            except:
                return {}
        return {}
    
    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.data, f, indent=4)
    
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
            except:
                return {}
        return {}
    
    def save_catalog(self):
        with open(CATALOG_FILE, 'w') as f:
            json.dump(self.data, f, indent=4)
    
    def get_categories(self, guild_id: int) -> List[str]:
        return list(self.data.get(str(guild_id), {}).keys())
    
    def get_items(self, guild_id: int, category: str) -> List[Dict]:
        return self.data.get(str(guild_id), {}).get(category, [])

class CategorySelect(discord.ui.Select):
    def __init__(self, guild_id: int, catalog: Catalog):
        self.guild_id = guild_id
        self.catalog = catalog
        categories = catalog.get_categories(guild_id)
        options = []
        for category in categories:
            options.append(discord.SelectOption(
                label=category,
                description=f"View items in {category}"
            ))
        super().__init__(
            placeholder="Choose a category...",
            min_values=1,
            max_values=1,
            options=options if options else [discord.SelectOption(label="No categories", value="none")]
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("No categories available.", ephemeral=True)
            return
        
        items = self.catalog.get_items(self.guild_id, self.values[0])
        if not items:
            await interaction.response.send_message("No items in this category.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"📦 {self.values[0]}",
            color=discord.Color.blue()
        )
        
        for item in items:
            embed.add_field(
                name=f"{item['name']} - ${item['price']}",
                value=item.get('description', 'No description'),
                inline=False
            )
        
        view = discord.ui.View()
        for item in items:
            button = BuyButton(
                self.guild_id,
                self.values[0],
                item['name'],
                item['price']
            )
            view.add_item(button)
        
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )

class CatalogView(discord.ui.View):
    def __init__(self, guild_id: int, catalog: Catalog):
        super().__init__(timeout=None)
        self.add_item(CategorySelect(guild_id, catalog))

class BuyButton(discord.ui.Button):
    def __init__(self, guild_id: int, category: str, item_name: str, price: float):
        super().__init__(
            label=f"Buy {item_name} (${price})",
            style=discord.ButtonStyle.green,
            custom_id=f"buy_{guild_id}_{category}_{item_name}"
        )
        self.guild_id = guild_id
        self.category = category
        self.item_name = item_name
        self.price = price
    
    async def callback(self, interaction: discord.Interaction):
        config = Config()
        guild_config = config.get_guild_config(self.guild_id)
        
        if not guild_config.get('ticket_category_id'):
            await interaction.response.send_message("Ticket system not configured.", ephemeral=True)
            return
        
        category = interaction.guild.get_channel(int(guild_config['ticket_category_id']))
        if not category:
            await interaction.response.send_message("Ticket category not found.", ephemeral=True)
            return
        
        staff_role = interaction.guild.get_role(int(guild_config.get('staff_role_id', 0)))
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        
        channel_name = f"ticket-{interaction.user.name}-{self.item_name[:20]}"
        channel = await interaction.guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites
        )
        
        embed = discord.Embed(
            title=f"🎫 Ticket: {self.item_name}",
            description=f"**Item:** {self.item_name}\n**Category:** {self.category}\n**Price:** ${self.price}\n**User:** {interaction.user.mention}",
            color=discord.Color.green()
        )
        
        await channel.send(content=f"{interaction.user.mention} {staff_role.mention if staff_role else ''}", embed=embed)
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)

class PricingTicketSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = Config()
        self.catalog = Catalog()
    
    async def cog_load(self):
        self.bot.add_view(CatalogView(0, self.catalog))
    
    @app_commands.command(name="setup", description="Configure the ticket system")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        class SetupModal(discord.ui.Modal, title="Ticket System Setup"):
            def __init__(self, cog):
                super().__init__()
                self.cog = cog
            
            staff_role = discord.ui.TextInput(
                label="Staff Role ID",
                placeholder="Enter the role ID for staff",
                required=True
            )
            
            ticket_category = discord.ui.TextInput(
                label="Ticket Category ID",
                placeholder="Enter the category ID for tickets",
                required=True
            )
            
            catalog_message = discord.ui.TextInput(
                label="Catalog Message",
                placeholder="Enter the message to display above the catalog",
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=2000
            )
            
            async def on_submit(self, interaction: discord.Interaction):
                try:
                    staff_role_id = int(self.staff_role.value)
                    ticket_category_id = int(self.ticket_category.value)
                    
                    role = interaction.guild.get_role(staff_role_id)
                    category = interaction.guild.get_channel(ticket_category_id)
                    
                    if not role:
                        await interaction.response.send_message("Invalid role ID.", ephemeral=True)
                        return
                    
                    if not category or not isinstance(category, discord.CategoryChannel):
                        await interaction.response.send_message("Invalid category ID.", ephemeral=True)
                        return
                    
                    guild_config = self.cog.config.get_guild_config(interaction.guild_id)
                    guild_config['staff_role_id'] = staff_role_id
                    guild_config['ticket_category_id'] = ticket_category_id
                    guild_config['catalog_channel_id'] = None
                    
                    self.cog.config.data[str(interaction.guild_id)] = guild_config
                    self.cog.config.save_config()
                    
                    embed = discord.Embed(
                        title="📋 Catalog",
                        description=self.catalog_message.value,
                        color=discord.Color.blue()
                    )
                    
                    view = CatalogView(interaction.guild_id, self.cog.catalog)
                    await interaction.channel.send(embed=embed, view=view)
                    
                    await interaction.response.send_message("Setup complete!", ephemeral=True)
                    
                except ValueError:
                    await interaction.response.send_message("Please enter valid IDs.", ephemeral=True)
        
        await interaction.response.send_modal(SetupModal(self))
    
    @app_commands.command(name="add-item", description="Add an item to the catalog")
    @app_commands.default_permissions(administrator=True)
    async def add_item(self, interaction: discord.Interaction):
        class AddItemModal(discord.ui.Modal, title="Add Catalog Item"):
            def __init__(self, cog):
                super().__init__()
                self.cog = cog
            
            category = discord.ui.TextInput(
                label="Category",
                placeholder="Enter category name (e.g., 'Gold', 'Accounts')",
                required=True
            )
            
            name = discord.ui.TextInput(
                label="Item Name",
                placeholder="Enter item name",
                required=True
            )
            
            price = discord.ui.TextInput(
                label="Price",
                placeholder="Enter price (numbers only)",
                required=True
            )
            
            description = discord.ui.TextInput(
                label="Description",
                placeholder="Enter item description",
                style=discord.TextStyle.paragraph,
                required=True
            )
            
            async def on_submit(self, interaction: discord.Interaction):
                try:
                    price = float(self.price.value)
                    
                    guild_id = str(interaction.guild_id)
                    
                    if guild_id not in self.cog.catalog.data:
                        self.cog.catalog.data[guild_id] = {}
                    
                    if self.category.value not in self.cog.catalog.data[guild_id]:
                        self.cog.catalog.data[guild_id][self.category.value] = []
                    
                    self.cog.catalog.data[guild_id][self.category.value].append({
                        'name': self.name.value,
                        'price': price,
                        'description': self.description.value
                    })
                    
                    self.cog.catalog.save_catalog()
                    
                    embed = discord.Embed(
                        title="✅ Item Added",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Category", value=self.category.value, inline=True)
                    embed.add_field(name="Item", value=self.name.value, inline=True)
                    embed.add_field(name="Price", value=f"${price}", inline=True)
                    embed.add_field(name="Description", value=self.description.value, inline=False)
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    
                except ValueError:
                    await interaction.response.send_message("Invalid price format.", ephemeral=True)
        
        await interaction.response.send_modal(AddItemModal(self))
    
    @app_commands.command(name="refresh-catalog", description="Refresh the catalog message")
    @app_commands.default_permissions(administrator=True)
    async def refresh_catalog(self, interaction: discord.Interaction):
        await interaction.response.send_message("Refreshing catalog...", ephemeral=True)
        # Implementation for refreshing catalog if needed

async def setup(bot: commands.Bot):
    await bot.add_cog(PricingTicketSystem(bot))