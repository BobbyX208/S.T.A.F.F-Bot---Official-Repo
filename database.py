import os
import json
import asyncio
from typing import Optional, Any, Dict, List
from dotenv import load_dotenv
import asyncpg
import aiomysql
from utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

class DatabaseHandler:
    """Handles database operations for PostgreSQL, MySQL, and JSON fallback"""
    
    def __init__(self):
        self.db_type = os.getenv('DB_TYPE', 'json')
        self.pool = None
        self.connection = None
        self.json_file = 'data.json'
        
    async def initialize(self):
        """Initialize database connection based on DB_TYPE"""
        try:
            if self.db_type == 'postgresql':
                await self._init_postgres()
            elif self.db_type == 'mysql':
                await self._init_mysql()
            else:
                await self._init_json()
            
            logger.info(f"Database initialized successfully: {self.db_type}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            # Fallback to JSON if other databases fail
            self.db_type = 'json'
            await self._init_json()
    
    async def _init_postgres(self):
        """Initialize PostgreSQL connection pool"""
        self.pool = await asyncpg.create_pool(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'discord_bot'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            min_size=1,
            max_size=10
        )
        
        # Create tables if they don't exist
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bot_config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    async def _init_mysql(self):
        """Initialize MySQL connection pool"""
        self.pool = await aiomysql.create_pool(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            db=os.getenv('DB_NAME', 'discord_bot'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            minsize=1,
            maxsize=10,
            autocommit=True
        )
        
        # Create tables if they don't exist
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute('''
                    CREATE TABLE IF NOT EXISTS bot_config (
                        `key` VARCHAR(255) PRIMARY KEY,
                        `value` TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
    
    async def _init_json(self):
        """Initialize JSON file storage"""
        if not os.path.exists(self.json_file):
            with open(self.json_file, 'w') as f:
                json.dump({}, f)
    
    async def get_config(self, key: str) -> Optional[str]:
        """Get configuration value by key"""
        try:
            if self.db_type == 'postgresql' and self.pool:
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow(
                        'SELECT value FROM bot_config WHERE key = $1',
                        key
                    )
                    return row['value'] if row else None
                    
            elif self.db_type == 'mysql' and self.pool:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            'SELECT `value` FROM bot_config WHERE `key` = %s',
                            (key,)
                        )
                        result = await cursor.fetchone()
                        return result[0] if result else None
                        
            else:  # JSON fallback
                with open(self.json_file, 'r') as f:
                    data = json.load(f)
                    return data.get(key)
                    
        except Exception as e:
            logger.error(f"Error getting config {key}: {e}")
            return None
    
    async def set_config(self, key: str, value: str):
        """Set configuration value"""
        try:
            if self.db_type == 'postgresql' and self.pool:
                async with self.pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO bot_config (key, value, updated_at)
                        VALUES ($1, $2, CURRENT_TIMESTAMP)
                        ON CONFLICT (key) 
                        DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
                    ''', key, value)
                    
            elif self.db_type == 'mysql' and self.pool:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute('''
                            INSERT INTO bot_config (`key`, `value`, updated_at)
                            VALUES (%s, %s, CURRENT_TIMESTAMP)
                            ON DUPLICATE KEY UPDATE
                            `value` = %s, updated_at = CURRENT_TIMESTAMP
                        ''', (key, value, value))
                        
            else:  # JSON fallback
                with open(self.json_file, 'r+') as f:
                    data = json.load(f)
                    data[key] = value
                    f.seek(0)
                    json.dump(data, f, indent=4)
                    f.truncate()
                    
            logger.info(f"Config updated: {key}")
            
        except Exception as e:
            logger.error(f"Error setting config {key}: {e}")

# Add to database.py

    async def get_guild_config(self, guild_id: int, module: str) -> dict:
        """Get configuration for a specific module"""
        try:
            if self.db_type == 'json':
                async with aiofiles.open('data/guild_configs.json', 'r') as f:
                    data = json.loads(await f.read())
                    return data.get(str(guild_id), {}).get(module, {})
            else:
                # SQL implementation
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT config FROM guild_configs WHERE guild_id = $1 AND module = $2",
                        guild_id, module
                    )
                    return json.loads(row['config']) if row else {}
        except:
            return {}
    
    async def update_guild_config(self, guild_id: int, module: str, config: dict):
        """Update configuration for a specific module"""
        try:
            if self.db_type == 'json':
                async with aiofiles.open('data/guild_configs.json', 'r+') as f:
                    data = json.loads(await f.read())
                    if str(guild_id) not in data:
                        data[str(guild_id)] = {}
                    data[str(guild_id)][module] = config
                    await f.seek(0)
                    await f.write(json.dumps(data, indent=2))
                    await f.truncate()
            else:
                # SQL implementation
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO guild_configs (guild_id, module, config, updated_at)
                        VALUES ($1, $2, $3, NOW())
                        ON CONFLICT (guild_id, module) 
                        DO UPDATE SET config = $3, updated_at = NOW()
                    """, guild_id, module, json.dumps(config))
        except Exception as e:
            logger.error(f"Failed to update guild config: {e}")
    
    async def create_ticket(self, ticket_data: dict) -> int:
        """Create a new ticket record"""
        try:
            if self.db_type == 'json':
                async with aiofiles.open('data/tickets.json', 'r+') as f:
                    data = json.loads(await f.read())
                    ticket_id = len(data) + 1
                    ticket_data['id'] = ticket_id
                    data[str(ticket_id)] = ticket_data
                    await f.seek(0)
                    await f.write(json.dumps(data, indent=2))
                    await f.truncate()
                    return ticket_id
            else:
                # SQL implementation
                async with self.pool.acquire() as conn:
                    ticket_id = await conn.fetchval("""
                        INSERT INTO tickets (guild_id, channel_id, user_id, user_name, 
                                           category_id, category_name, answers, status)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        RETURNING id
                    """, ticket_data['guild_id'], ticket_data['channel_id'], 
                        ticket_data['user_id'], ticket_data['user_name'],
                        ticket_data['category_id'], ticket_data['category_name'],
                        json.dumps(ticket_data['answers']), ticket_data['status'])
                    return ticket_id
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            return 0
    
    async def get_ticket(self, ticket_id: int) -> dict:
        """Get ticket by ID"""
        try:
            if self.db_type == 'json':
                async with aiofiles.open('data/tickets.json', 'r') as f:
                    data = json.loads(await f.read())
                    return data.get(str(ticket_id), {})
            else:
                # SQL implementation
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow("SELECT * FROM tickets WHERE id = $1", ticket_id)
                    return dict(row) if row else {}
        except:
            return {}
    
    async def find_ticket(self, query: dict) -> dict:
        """Find a ticket matching query"""
        try:
            if self.db_type == 'json':
                async with aiofiles.open('data/tickets.json', 'r') as f:
                    data = json.loads(await f.read())
                    for tid, ticket in data.items():
                        match = True
                        for key, value in query.items():
                            if ticket.get(key) != value:
                                match = False
                                break
                        if match:
                            return ticket
            else:
                # Build SQL query
                conditions = []
                values = []
                for i, (key, value) in enumerate(query.items()):
                    conditions.append(f"{key} = ${i+1}")
                    values.append(value)
                
                sql = f"SELECT * FROM tickets WHERE {' AND '.join(conditions)} LIMIT 1"
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow(sql, *values)
                    return dict(row) if row else {}
        except:
            return {}
    
    async def update_ticket(self, ticket_id: int, updates: dict):
        """Update ticket information"""
        try:
            if self.db_type == 'json':
                async with aiofiles.open('data/tickets.json', 'r+') as f:
                    data = json.loads(await f.read())
                    if str(ticket_id) in data:
                        data[str(ticket_id)].update(updates)
                        await f.seek(0)
                        await f.write(json.dumps(data, indent=2))
                        await f.truncate()
            else:
                # Build SQL SET clause
                set_parts = []
                values = []
                for i, (key, value) in enumerate(updates.items()):
                    set_parts.append(f"{key} = ${i+1}")
                    if isinstance(value, dict):
                        values.append(json.dumps(value))
                    else:
                        values.append(value)
                
                values.append(ticket_id)
                sql = f"UPDATE tickets SET {', '.join(set_parts)} WHERE id = ${len(values)}"
                async with self.pool.acquire() as conn:
                    await conn.execute(sql, *values)
        except Exception as e:
            logger.error(f"Failed to update ticket: {e}")
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            self.pool.close()
            if self.db_type == 'postgresql':
                await self.pool.wait_closed()
