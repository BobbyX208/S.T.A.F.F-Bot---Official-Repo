import os
import json
import asyncio
from typing import Optional, Any, Dict, List, Union
from dotenv import load_dotenv
import aiomysql
from utils.logger import get_logger
import aiofiles
from datetime import datetime

load_dotenv()

logger = get_logger(__name__)

class DatabaseHandler:
    """Handles database operations for MySQL with JSON fallback"""
    
    def __init__(self):
        self.db_type = os.getenv('DB_TYPE', 'mysql').lower()
        self.pool = None
        self.json_file = 'data.json'
        
    async def initialize(self):
        """Initialize database connection based on DB_TYPE"""
        try:
            if self.db_type == 'mysql':
                await self._init_mysql()
                # Create all necessary tables
                await self._create_tables()
            else:
                await self._init_json()
            
            logger.info(f"Database initialized successfully: {self.db_type}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            # Fallback to JSON
            self.db_type = 'json'
            await self._init_json()
    
    async def _init_mysql(self):
        """Initialize MySQL connection pool"""
        try:
            self.pool = await aiomysql.create_pool(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 3306)),
                db=os.getenv('DB_NAME', 'discord_bot'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', ''),
                minsize=1,
                maxsize=10,
                autocommit=True,
                charset='utf8mb4'
            )
            logger.info("MySQL connection pool created")
        except Exception as e:
            logger.error(f"MySQL connection failed: {e}")
            raise
    
    async def _init_json(self):
        """Initialize JSON file storage"""
        os.makedirs('data', exist_ok=True)
        if not os.path.exists(self.json_file):
            async with aiofiles.open(self.json_file, 'w') as f:
                await f.write(json.dumps({}, indent=2))
        logger.info("JSON storage initialized")
    
    async def _create_tables(self):
        """Create all necessary tables if they don't exist"""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS guild_configs (
                guild_id BIGINT NOT NULL,
                module VARCHAR(50) NOT NULL,
                config JSON NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, module)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                user_name VARCHAR(255) NOT NULL,
                subject VARCHAR(255),
                description TEXT,
                category VARCHAR(100),
                status VARCHAR(50) DEFAULT 'open',
                claimed_by BIGINT,
                claimed_at TIMESTAMP NULL,
                closed_by BIGINT,
                closed_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_guild_status (guild_id, status),
                INDEX idx_user (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS catalog_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                category VARCHAR(100) NOT NULL,
                name VARCHAR(255) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_guild_category (guild_id, category)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS catalog_categories (
                guild_id BIGINT NOT NULL,
                category VARCHAR(100) NOT NULL,
                emoji VARCHAR(10) DEFAULT '📦',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, category)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        ]
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for table_sql in tables:
                    try:
                        await cursor.execute(table_sql)
                        logger.debug(f"Table created/verified")
                    except Exception as e:
                        logger.error(f"Error creating table: {e}")
        
        logger.info("All database tables verified")
    
    # =========================================================================
    # GUILD CONFIG METHODS
    # =========================================================================
    
    async def get_guild_config(self, guild_id: int, module: str) -> dict:
        """Get configuration for a specific module"""
        try:
            if self.db_type == 'mysql' and self.pool:
                async with self.pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cursor:
                        await cursor.execute(
                            "SELECT config FROM guild_configs WHERE guild_id = %s AND module = %s",
                            (guild_id, module)
                        )
                        result = await cursor.fetchone()
                        if result:
                            return json.loads(result['config'])
                        return {}
            else:
                # JSON fallback
                filename = f'data/{module}_config.json'
                if os.path.exists(filename):
                    async with aiofiles.open(filename, 'r') as f:
                        data = json.loads(await f.read())
                        return data.get(str(guild_id), {})
                return {}
        except Exception as e:
            logger.error(f"Error getting guild config: {e}")
            return {}
    
    async def update_guild_config(self, guild_id: int, module: str, config: dict):
        """Update configuration for a specific module"""
        try:
            if self.db_type == 'mysql' and self.pool:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            """INSERT INTO guild_configs (guild_id, module, config, updated_at)
                               VALUES (%s, %s, %s, NOW())
                               ON DUPLICATE KEY UPDATE
                               config = VALUES(config),
                               updated_at = NOW()""",
                            (guild_id, module, json.dumps(config))
                        )
                logger.info(f"Updated {module} config for guild {guild_id}")
            else:
                # JSON fallback
                filename = f'data/{module}_config.json'
                
                # Read existing
                if os.path.exists(filename):
                    async with aiofiles.open(filename, 'r') as f:
                        data = json.loads(await f.read())
                else:
                    data = {}
                
                # Update
                data[str(guild_id)] = config
                
                # Write back
                async with aiofiles.open(filename, 'w') as f:
                    await f.write(json.dumps(data, indent=2))
                
                logger.info(f"Updated {module} config for guild {guild_id} (JSON)")
        except Exception as e:
            logger.error(f"Error updating guild config: {e}")
    
    # =========================================================================
    # TICKET METHODS
    # =========================================================================
    
    async def create_ticket(self, guild_id: int, ticket_data: dict) -> int:
        """Create a new ticket and return ID"""
        try:
            if self.db_type == 'mysql' and self.pool:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            """INSERT INTO tickets 
                               (guild_id, channel_id, user_id, user_name, subject, description, category, status)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                            (
                                guild_id,
                                ticket_data.get('channel_id'),
                                ticket_data.get('user_id'),
                                ticket_data.get('user_name'),
                                ticket_data.get('subject'),
                                ticket_data.get('description'),
                                ticket_data.get('category', 'general'),
                                ticket_data.get('status', 'open')
                            )
                        )
                        ticket_id = cursor.lastrowid
                        logger.info(f"Created ticket {ticket_id} for guild {guild_id}")
                        return ticket_id
            else:
                # JSON fallback
                filename = 'data/tickets.json'
                
                if os.path.exists(filename):
                    async with aiofiles.open(filename, 'r') as f:
                        data = json.loads(await f.read())
                else:
                    data = {}
                
                guild_str = str(guild_id)
                if guild_str not in data:
                    data[guild_str] = []
                
                ticket_id = len(data[guild_str]) + 1
                ticket_data['id'] = ticket_id
                ticket_data['created_at'] = datetime.utcnow().isoformat()
                data[guild_str].append(ticket_data)
                
                async with aiofiles.open(filename, 'w') as f:
                    await f.write(json.dumps(data, indent=2))
                
                return ticket_id
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            return 0
    
    async def get_ticket(self, guild_id: int, ticket_id: int) -> Optional[dict]:
        """Get ticket by ID"""
        try:
            if self.db_type == 'mysql' and self.pool:
                async with self.pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cursor:
                        await cursor.execute(
                            "SELECT * FROM tickets WHERE guild_id = %s AND id = %s",
                            (guild_id, ticket_id)
                        )
                        result = await cursor.fetchone()
                        return result
            else:
                # JSON fallback
                filename = 'data/tickets.json'
                if os.path.exists(filename):
                    async with aiofiles.open(filename, 'r') as f:
                        data = json.loads(await f.read())
                        guild_str = str(guild_id)
                        if guild_str in data:
                            for ticket in data[guild_str]:
                                if ticket.get('id') == ticket_id:
                                    return ticket
                return None
        except Exception as e:
            logger.error(f"Error getting ticket: {e}")
            return None
    
    async def find_ticket(self, guild_id: int, **kwargs) -> Optional[dict]:
        """Find ticket matching criteria"""
        try:
            if self.db_type == 'mysql' and self.pool:
                query = "SELECT * FROM tickets WHERE guild_id = %s"
                values = [guild_id]
                
                for key, value in kwargs.items():
                    query += f" AND {key} = %s"
                    values.append(value)
                
                query += " LIMIT 1"
                
                async with self.pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cursor:
                        await cursor.execute(query, values)
                        return await cursor.fetchone()
            else:
                # JSON fallback
                filename = 'data/tickets.json'
                if os.path.exists(filename):
                    async with aiofiles.open(filename, 'r') as f:
                        data = json.loads(await f.read())
                        guild_str = str(guild_id)
                        if guild_str in data:
                            for ticket in data[guild_str]:
                                match = True
                                for key, value in kwargs.items():
                                    if ticket.get(key) != value:
                                        match = False
                                        break
                                if match:
                                    return ticket
                return None
        except Exception as e:
            logger.error(f"Error finding ticket: {e}")
            return None
    
    async def update_ticket(self, guild_id: int, ticket_id: int, updates: dict):
        """Update ticket information"""
        try:
            if self.db_type == 'mysql' and self.pool:
                set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
                values = list(updates.values()) + [guild_id, ticket_id]
                
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            f"UPDATE tickets SET {set_clause} WHERE guild_id = %s AND id = %s",
                            values
                        )
                logger.info(f"Updated ticket {ticket_id}")
            else:
                # JSON fallback
                filename = 'data/tickets.json'
                if os.path.exists(filename):
                    async with aiofiles.open(filename, 'r') as f:
                        data = json.loads(await f.read())
                    
                    guild_str = str(guild_id)
                    if guild_str in data:
                        for ticket in data[guild_str]:
                            if ticket.get('id') == ticket_id:
                                ticket.update(updates)
                                break
                    
                    async with aiofiles.open(filename, 'w') as f:
                        await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Error updating ticket: {e}")
    
    # =========================================================================
    # CATALOG METHODS
    # =========================================================================
    
    async def get_catalog_categories(self, guild_id: int) -> List[str]:
        """Get all categories for a guild"""
        try:
            if self.db_type == 'mysql' and self.pool:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            "SELECT DISTINCT category FROM catalog_items WHERE guild_id = %s",
                            (guild_id,)
                        )
                        results = await cursor.fetchall()
                        return [r[0] for r in results]
            else:
                # JSON fallback
                filename = 'data/catalog.json'
                if os.path.exists(filename):
                    async with aiofiles.open(filename, 'r') as f:
                        data = json.loads(await f.read())
                        return list(data.get(str(guild_id), {}).keys())
                return []
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    async def get_catalog_items(self, guild_id: int, category: str) -> List[dict]:
        """Get all items in a category"""
        try:
            if self.db_type == 'mysql' and self.pool:
                async with self.pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cursor:
                        await cursor.execute(
                            "SELECT * FROM catalog_items WHERE guild_id = %s AND category = %s",
                            (guild_id, category)
                        )
                        return await cursor.fetchall()
            else:
                # JSON fallback
                filename = 'data/catalog.json'
                if os.path.exists(filename):
                    async with aiofiles.open(filename, 'r') as f:
                        data = json.loads(await f.read())
                        return data.get(str(guild_id), {}).get(category, [])
                return []
        except Exception as e:
            logger.error(f"Error getting items: {e}")
            return []
    
    async def add_catalog_item(self, guild_id: int, category: str, name: str, price: float, description: str):
        """Add an item to catalog"""
        try:
            if self.db_type == 'mysql' and self.pool:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            """INSERT INTO catalog_items (guild_id, category, name, price, description)
                               VALUES (%s, %s, %s, %s, %s)""",
                            (guild_id, category, name, price, description)
                        )
                logger.info(f"Added catalog item: {name}")
            else:
                # JSON fallback
                filename = 'data/catalog.json'
                
                if os.path.exists(filename):
                    async with aiofiles.open(filename, 'r') as f:
                        data = json.loads(await f.read())
                else:
                    data = {}
                
                guild_str = str(guild_id)
                if guild_str not in data:
                    data[guild_str] = {}
                
                if category not in data[guild_str]:
                    data[guild_str][category] = []
                
                data[guild_str][category].append({
                    'name': name,
                    'price': price,
                    'description': description
                })
                
                async with aiofiles.open(filename, 'w') as f:
                    await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Error adding catalog item: {e}")
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    async def get_config(self, key: str) -> Optional[str]:
        """Get configuration value by key"""
        try:
            if self.db_type == 'mysql' and self.pool:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            'SELECT `value` FROM bot_config WHERE `key` = %s',
                            (key,)
                        )
                        result = await cursor.fetchone()
                        return result[0] if result else None
            else:
                with open(self.json_file, 'r') as f:
                    data = json.load(f)
                    return data.get(key)
        except Exception as e:
            logger.error(f"Error getting config {key}: {e}")
            return None
    
    async def set_config(self, key: str, value: str):
        """Set configuration value"""
        try:
            if self.db_type == 'mysql' and self.pool:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute('''
                            INSERT INTO bot_config (`key`, `value`, updated_at)
                            VALUES (%s, %s, NOW())
                            ON DUPLICATE KEY UPDATE
                            `value` = %s, updated_at = NOW()
                        ''', (key, value, value))
            else:
                with open(self.json_file, 'r+') as f:
                    data = json.load(f)
                    data[key] = value
                    f.seek(0)
                    json.dump(data, f, indent=4)
                    f.truncate()
            logger.info(f"Config updated: {key}")
        except Exception as e:
            logger.error(f"Error setting config {key}: {e}")
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("Database connection closed")