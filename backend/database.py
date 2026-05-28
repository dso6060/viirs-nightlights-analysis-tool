"""
Database models and operations for VIIRS nightlights data.

Supports SQLite for local development and testing with 140+ cities.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    SQLite database manager for VIIRS nightlights data.
    
    Handles cities, VIIRS data, and test results storage.
    """
    
    def __init__(self, db_path: str = "viirs_data.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            
            # Cities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    country TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    radius_km REAL DEFAULT 10.0,
                    display_name TEXT,
                    osm_id TEXT,
                    place_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, country)
                )
            """)
            
            # VIIRS data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS viirs_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    radiance REAL,
                    radiance_corrected REAL,
                    cloud_free_coverage REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (city_id) REFERENCES cities (id),
                    UNIQUE(city_id, date)
                )
            """)
            
            # Test results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    test_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    execution_time REAL,
                    data_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Quick test buttons configuration
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quick_test_buttons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    button_name TEXT NOT NULL UNIQUE,
                    cities TEXT NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cities_name ON cities(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cities_country ON cities(country)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_viirs_city_date ON viirs_data(city_id, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_viirs_date ON viirs_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_results_type ON test_results(test_type)")
            
            conn.commit()
            logger.info("Database initialized successfully")

        # Run lightweight schema migrations if needed.
        self._migrate_schema_if_needed()

    def _migrate_schema_if_needed(self):
        """
        Perform in-place migrations for older DB schema versions.

        Currently:
        - Allow NULL radiance fields in `viirs_data` so low-quality months can be stored.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA table_info(viirs_data)")
                cols = cur.fetchall()
                if not cols:
                    return

                # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
                col_by_name = {c[1]: c for c in cols}
                rad_notnull = col_by_name.get("radiance", (None, None, None, 0))[3]
                radc_notnull = col_by_name.get("radiance_corrected", (None, None, None, 0))[3]

                if rad_notnull == 0 and radc_notnull == 0:
                    return  # already migrated

                logger.info("Migrating schema: making viirs_data radiance fields nullable...")

                conn.execute("PRAGMA foreign_keys = OFF")
                conn.execute("BEGIN")

                cur.execute("""
                    CREATE TABLE viirs_data_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        city_id INTEGER NOT NULL,
                        date TEXT NOT NULL,
                        radiance REAL,
                        radiance_corrected REAL,
                        cloud_free_coverage REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (city_id) REFERENCES cities (id),
                        UNIQUE(city_id, date)
                    )
                """)

                cur.execute("""
                    INSERT INTO viirs_data_new (id, city_id, date, radiance, radiance_corrected, cloud_free_coverage, created_at)
                    SELECT id, city_id, date, radiance, radiance_corrected, cloud_free_coverage, created_at
                    FROM viirs_data
                """)

                cur.execute("DROP TABLE viirs_data")
                cur.execute("ALTER TABLE viirs_data_new RENAME TO viirs_data")

                # Recreate indexes
                cur.execute("CREATE INDEX IF NOT EXISTS idx_viirs_city_date ON viirs_data(city_id, date)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_viirs_date ON viirs_data(date)")

                conn.execute("COMMIT")
                conn.execute("PRAGMA foreign_keys = ON")
                logger.info("Schema migration complete.")
        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            # Don't block app startup if migration fails; caller can handle manually.
            return
    
    def add_city(self, city_data: Dict) -> int:
        """
        Add a city to the database.
        
        Args:
            city_data: Dictionary with city information
            
        Returns:
            City ID
        """
        # Validate data types
        try:
            float(city_data['lat'])
            float(city_data['lon'])
        except (ValueError, TypeError):
            raise ValueError(f"Invalid coordinate data types: lat={city_data['lat']}, lon={city_data['lon']}")
        
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            
            # Check if city already exists
            cursor.execute("SELECT id FROM cities WHERE name = ? AND country = ?", 
                         (city_data['name'], city_data['country']))
            existing_city = cursor.fetchone()
            
            if existing_city:
                # Update existing city
                city_id = existing_city[0]
                cursor.execute("""
                    UPDATE cities SET 
                        latitude = ?, longitude = ?, radius_km = ?, 
                        display_name = ?, osm_id = ?, place_type = ?, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    city_data['lat'],
                    city_data['lon'],
                    city_data.get('radius_km', 10.0),
                    city_data.get('display_name', ''),
                    city_data.get('osm_id', ''),
                    city_data.get('place_type', 'city'),
                    city_id
                ))
            else:
                # Insert new city
                cursor.execute("""
                    INSERT INTO cities 
                    (name, country, latitude, longitude, radius_km, display_name, osm_id, place_type, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    city_data['name'],
                    city_data['country'],
                    city_data['lat'],
                    city_data['lon'],
                    city_data.get('radius_km', 10.0),
                    city_data.get('display_name', ''),
                    city_data.get('osm_id', ''),
                    city_data.get('place_type', 'city')
                ))
                city_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Added city: {city_data['name']}, {city_data['country']} (ID: {city_id})")
            return city_id
    
    def get_city_by_name(self, name: str, country: str = None) -> Optional[Dict]:
        """
        Get city by name and country.
        
        Args:
            name: City name
            country: Country name (optional)
            
        Returns:
            City data dictionary or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if country:
                cursor.execute("""
                    SELECT * FROM cities WHERE name = ? AND country = ?
                """, (name, country))
            else:
                cursor.execute("""
                    SELECT * FROM cities WHERE name = ?
                """, (name,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def get_all_cities(self, limit: int = None) -> List[Dict]:
        """
        Get all cities from database.
        
        Args:
            limit: Maximum number of cities to return
            
        Returns:
            List of city dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM cities ORDER BY name, country"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    def add_viirs_data(self, city_id: int, viirs_data: List[Dict]) -> int:
        """
        Add VIIRS data for a city.
        
        Args:
            city_id: City ID
            viirs_data: List of VIIRS data points
            
        Returns:
            Number of records added
        """
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            
            added_count = 0
            for data_point in viirs_data:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO viirs_data 
                        (city_id, date, radiance, radiance_corrected, cloud_free_coverage)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        city_id,
                        data_point['date'],
                        data_point['radiance'],
                        data_point['radiance_corrected'],
                        data_point.get('cloud_free_coverage')
                    ))
                    added_count += 1
                except sqlite3.IntegrityError as e:
                    if "FOREIGN KEY constraint failed" in str(e):
                        raise e  # Re-raise foreign key constraint errors
                    else:
                        logger.warning(f"Failed to add VIIRS data for {data_point['date']}: {e}")
                        continue
                except Exception as e:
                    logger.warning(f"Failed to add VIIRS data for {data_point['date']}: {e}")
                    continue
            
            conn.commit()
            logger.info(f"Added {added_count} VIIRS data points for city ID {city_id}")
            return added_count
    
    def get_viirs_data(self, city_id: int = None, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        Get VIIRS data with optional filters.
        
        Args:
            city_id: Filter by city ID
            start_date: Filter by start date (YYYY-MM)
            end_date: Filter by end date (YYYY-MM)
            
        Returns:
            List of VIIRS data dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT v.*, c.name as city_name, c.country, c.latitude, c.longitude
                FROM viirs_data v
                JOIN cities c ON v.city_id = c.id
            """
            conditions = []
            params = []
            
            if city_id:
                conditions.append("v.city_id = ?")
                params.append(city_id)
            
            if start_date:
                conditions.append("v.date >= ?")
                params.append(start_date)
            
            if end_date:
                conditions.append("v.date <= ?")
                params.append(end_date)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY v.date, c.name"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    def get_city_viirs_data(self, city_name: str, country: str = None, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        Get VIIRS data for a specific city.
        
        Args:
            city_name: City name
            country: Country name (optional)
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of VIIRS data dictionaries
        """
        city = self.get_city_by_name(city_name, country)
        if not city:
            return []
        
        return self.get_viirs_data(city['id'], start_date, end_date)
    
    def add_test_result(self, test_name: str, test_type: str, status: str, message: str = None, execution_time: float = None, data_count: int = None):
        """
        Add test result to database.
        
        Args:
            test_name: Name of the test
            test_type: Type of test (database, backend, frontend, integration)
            status: Test status (passed, failed, error)
            message: Test message or error details
            execution_time: Test execution time in seconds
            data_count: Number of data points tested
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO test_results 
                (test_name, test_type, status, message, execution_time, data_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (test_name, test_type, status, message, execution_time, data_count))
            
            conn.commit()
            logger.info(f"Added test result: {test_name} - {status}")
    
    def get_test_results(self, test_type: str = None, limit: int = 100) -> List[Dict]:
        """
        Get test results with optional filtering.
        
        Args:
            test_type: Filter by test type
            limit: Maximum number of results
            
        Returns:
            List of test result dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM test_results"
            params = []
            
            if test_type:
                query += " WHERE test_type = ?"
                params.append(test_type)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    def add_quick_test_button(self, button_name: str, cities: List[str], description: str = None):
        """
        Add a quick test button configuration.
        
        Args:
            button_name: Name of the button
            cities: List of city names
            description: Button description
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO quick_test_buttons 
                (button_name, cities, description)
                VALUES (?, ?, ?)
            """, (button_name, json.dumps(cities), description))
            
            conn.commit()
            logger.info(f"Added quick test button: {button_name}")
    
    def get_quick_test_buttons(self) -> List[Dict]:
        """
        Get all quick test button configurations.
        
        Returns:
            List of quick test button dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM quick_test_buttons WHERE is_active = 1 ORDER BY button_name")
            rows = cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            buttons = []
            for row in rows:
                button = dict(zip(columns, row))
                button['cities'] = json.loads(button['cities'])
                buttons.append(button)
            
            return buttons
    
    def get_database_stats(self) -> Dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Count cities
            cursor.execute("SELECT COUNT(*) FROM cities")
            city_count = cursor.fetchone()[0]
            
            # Count VIIRS data points
            cursor.execute("SELECT COUNT(*) FROM viirs_data")
            viirs_count = cursor.fetchone()[0]
            
            # Count test results
            cursor.execute("SELECT COUNT(*) FROM test_results")
            test_count = cursor.fetchone()[0]
            
            # Date range of VIIRS data
            cursor.execute("SELECT MIN(date), MAX(date) FROM viirs_data")
            date_range = cursor.fetchone()
            
            # Countries represented
            cursor.execute("SELECT COUNT(DISTINCT country) FROM cities")
            country_count = cursor.fetchone()[0]
            
            return {
                "cities": city_count,
                "viirs_data_points": viirs_count,
                "test_results": test_count,
                "countries": country_count,
                "date_range": {
                    "start": date_range[0],
                    "end": date_range[1]
                } if date_range[0] else None,
                "database_size_mb": self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
            }
    
    def clear_test_data(self):
        """Clear all test data from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM test_results")
            cursor.execute("DELETE FROM viirs_data")
            cursor.execute("DELETE FROM cities")
            cursor.execute("DELETE FROM quick_test_buttons")
            
            conn.commit()
            logger.info("Cleared all test data from database")
    
    def backup_database(self, backup_path: str = None):
        """
        Create a backup of the database.
        
        Args:
            backup_path: Path for backup file
        """
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"viirs_data_backup_{timestamp}.db"
        
        backup_path = Path(backup_path)
        
        with sqlite3.connect(self.db_path) as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)
        
        logger.info(f"Database backed up to: {backup_path}")
        return backup_path


# Global database instance
db = DatabaseManager()
