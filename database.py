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
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            self.pool.close()
            if self.db_type == 'postgresql':
                await self.pool.wait_closed()