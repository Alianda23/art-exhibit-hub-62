
import mysql.connector
from mysql.connector import Error

# Database connection configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Update with your MySQL username
    'password': '',  # Update with your MySQL password
    'database': 'artgallery'
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("MySQL Database connection successful")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
    return None

def initialize_database():
    """Create database tables if they don't exist"""
    connection = get_db_connection()
    if connection is None:
        print("Failed to connect to database")
        return False
    
    cursor = connection.cursor()
    
    # Create users table
    users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        phone VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Create admins table
    admins_table = """
    CREATE TABLE IF NOT EXISTS admins (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Create artworks table
    artworks_table = """
    CREATE TABLE IF NOT EXISTS artworks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        artist VARCHAR(255) NOT NULL,
        description TEXT,
        price DECIMAL(10, 2) NOT NULL,
        image_url VARCHAR(255),
        dimensions VARCHAR(100),
        medium VARCHAR(100),
        year INT,
        status ENUM('available', 'sold') NOT NULL DEFAULT 'available',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Create exhibitions table
    exhibitions_table = """
    CREATE TABLE IF NOT EXISTS exhibitions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        location VARCHAR(255) NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        ticket_price DECIMAL(10, 2) NOT NULL,
        image_url VARCHAR(255),
        total_slots INT NOT NULL,
        available_slots INT NOT NULL,
        status ENUM('upcoming', 'ongoing', 'past') NOT NULL DEFAULT 'upcoming',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Create artwork orders table
    artwork_orders_table = """
    CREATE TABLE IF NOT EXISTS artwork_orders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        artwork_id INT NOT NULL,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL,
        phone VARCHAR(20) NOT NULL,
        delivery_address TEXT NOT NULL,
        payment_method ENUM('mpesa') NOT NULL,
        payment_status ENUM('pending', 'completed', 'failed') NOT NULL DEFAULT 'pending',
        total_amount DECIMAL(10, 2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (artwork_id) REFERENCES artworks(id) ON DELETE CASCADE
    );
    """
    
    # Create exhibition bookings (tickets) table
    exhibition_bookings_table = """
    CREATE TABLE IF NOT EXISTS exhibition_bookings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        exhibition_id INT NOT NULL,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL,
        phone VARCHAR(20) NOT NULL,
        slots INT NOT NULL,
        payment_method ENUM('mpesa') NOT NULL,
        payment_status ENUM('pending', 'completed', 'failed') NOT NULL DEFAULT 'pending',
        total_amount DECIMAL(10, 2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ticket_code VARCHAR(50) UNIQUE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (exhibition_id) REFERENCES exhibitions(id) ON DELETE CASCADE
    );
    """
    
    # Create mpesa transactions table
    mpesa_transactions_table = """
    CREATE TABLE IF NOT EXISTS mpesa_transactions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        checkout_request_id VARCHAR(100) NOT NULL,
        merchant_request_id VARCHAR(100) NOT NULL,
        order_type ENUM('artwork', 'exhibition') NOT NULL,
        order_id INT NOT NULL,
        user_id INT NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        phone_number VARCHAR(20) NOT NULL,
        result_code VARCHAR(10),
        result_desc VARCHAR(255),
        transaction_id VARCHAR(50),
        status ENUM('pending', 'completed', 'failed') NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """
    
    # Create contact messages table
    contact_messages_table = """
    CREATE TABLE IF NOT EXISTS contact_messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL,
        phone VARCHAR(20),
        message TEXT NOT NULL,
        status ENUM('new', 'read', 'replied') NOT NULL DEFAULT 'new',
        source VARCHAR(50) DEFAULT 'contact_form',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        cursor.execute(users_table)
        cursor.execute(admins_table)
        cursor.execute(artworks_table)
        cursor.execute(exhibitions_table)
        cursor.execute(artwork_orders_table)
        cursor.execute(exhibition_bookings_table)
        cursor.execute(mpesa_transactions_table)
        cursor.execute(contact_messages_table)
        connection.commit()
        print("Database tables created successfully")
        return True
    except Error as e:
        print(f"Error creating tables: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def dict_from_row(row, cursor):
    """Convert a database row to a dictionary"""
    return {cursor.column_names[i]: value for i, value in enumerate(row)}

if __name__ == "__main__":
    # Create database if it doesn't exist
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        print(f"Database '{DB_CONFIG['database']}' created or already exists")
        conn.close()
    except Error as err:
        print(f"Error creating database: {err}")
    
    # Initialize tables
    initialize_database()

