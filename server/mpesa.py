import requests
import base64
import json
from datetime import datetime
import time
from db_setup import get_db_connection, dict_from_row
from mysql.connector import Error

# M-Pesa API credentials
CONSUMER_KEY = "sMwMwGZ8oOiSkNrUIrPbcCeWIO8UiQ3SV4CyX739uAyZVs1F"
CONSUMER_SECRET = "A3Hs5zRY3nDCn7XpxPuc1iAKpfy6UDdetiCalIAfuAIpgTROI5yCqqOewDfThh2o"
BUSINESS_SHORT_CODE = "174379"  # Lipa Na M-Pesa Shortcode
PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
CALLBACK_URL = "https://webhook.site/3c1f62b5-4214-47d6-9f26-71c1f4b9c8f0"
API_BASE_URL = "https://sandbox.safaricom.co.ke"

def get_access_token():
    """Get OAuth access token from M-Pesa"""
    url = f"{API_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    auth = base64.b64encode(f"{CONSUMER_KEY}:{CONSUMER_SECRET}".encode()).decode('utf-8')
    headers = {
        "Authorization": f"Basic {auth}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response_data = response.json()
        
        if "access_token" in response_data:
            return response_data["access_token"]
        else:
            print("Error getting access token:", response_data)
            return None
    except Exception as e:
        print(f"Exception while getting access token: {e}")
        return None

def generate_password():
    """Generate password for M-Pesa STK Push"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password_str = f"{BUSINESS_SHORT_CODE}{PASSKEY}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode('utf-8')
    return password, timestamp

def initiate_stk_push(phone_number, amount, account_reference, order_type, order_id, user_id):
    """Initiate STK Push to customer's phone"""
    access_token = get_access_token()
    if not access_token:
        return {"error": "Failed to get access token"}
    
    password, timestamp = generate_password()
    
    # Format phone number
    if phone_number.startswith('+'):
        phone_number = phone_number[1:]
    if phone_number.startswith('0'):
        phone_number = '254' + phone_number[1:]
    
    url = f"{API_BASE_URL}/mpesa/stkpush/v1/processrequest"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Ensure amount is an integer (M-Pesa requires integer values)
    try:
        amount_int = int(float(amount))
    except (ValueError, TypeError):
        return {"error": "Invalid amount format. Must be a number."}
    
    payload = {
        "BusinessShortCode": BUSINESS_SHORT_CODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount_int,
        "PartyA": phone_number.replace("+", ""),  # Remove any + character
        "PartyB": BUSINESS_SHORT_CODE,
        "PhoneNumber": phone_number.replace("+", ""),  # Remove any + character
        "CallBackURL": CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": f"Payment for {order_type} #{order_id}"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        print(f"STK Push result: {result}")
        
        if "ResponseCode" in result and result["ResponseCode"] == "0":
            # Create the order/booking in pending state
            connection = get_db_connection()
            if not connection:
                return {"error": "Database connection failed"}
            
            cursor = connection.cursor()
            
            try:
                # For artwork orders
                if order_type == 'artwork':
                    query = """
                    INSERT INTO artwork_orders (user_id, artwork_id, amount, delivery_fee, delivery_address, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    """
                    cursor.execute(query, (
                        user_id,
                        order_id,
                        amount * 0.9,  # 90% of amount for artwork
                        amount * 0.1,  # 10% for delivery
                        "To be provided"  # Default address
                    ))
                    order_id = cursor.lastrowid
                
                # For exhibition bookings
                elif order_type == 'exhibition':
                    query = """
                    INSERT INTO exhibition_bookings (user_id, exhibition_id, slots, amount, status)
                    VALUES (%s, %s, %s, %s, 'pending')
                    """
                    cursor.execute(query, (
                        user_id,
                        order_id,
                        int(amount / (amount / 1)),  # Calculate slots
                        amount,
                        "pending"
                    ))
                    order_id = cursor.lastrowid
                
                # Save transaction details
                query = """
                INSERT INTO mpesa_transactions 
                (order_type, order_id, user_id, amount, phone_number, merchant_request_id, checkout_request_id, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
                """
                cursor.execute(query, (
                    order_type,
                    order_id,
                    user_id,
                    amount_int,
                    phone_number,
                    result["MerchantRequestID"],
                    result["CheckoutRequestID"]
                ))
                
                connection.commit()
                
                return {
                    "success": True,
                    "checkoutRequestId": result["CheckoutRequestID"],
                    "merchantRequestId": result["MerchantRequestID"],
                    "orderId": order_id
                }
            
            except Exception as e:
                print(f"Database error: {e}")
                connection.rollback()
                return {"error": "Failed to save order details"}
            finally:
                cursor.close()
                connection.close()
        else:
            return {
                "error": result.get("errorMessage", "STK Push failed"),
                "details": result
            }
    except Exception as e:
        print(f"Exception during STK Push: {e}")
        return {"error": str(e)}

def check_transaction_status(checkout_request_id):
    """Check status of an STK Push transaction"""
    connection = get_db_connection()
    if not connection:
        return {"error": "Database connection failed"}
    
    cursor = connection.cursor()
    
    try:
        # Check if transaction exists in database
        query = """
        SELECT * FROM mpesa_transactions 
        WHERE checkout_request_id = %s
        """
        cursor.execute(query, (checkout_request_id,))
        row = cursor.fetchone()
        
        if not row:
            return {"error": "Transaction not found"}
        
        transaction = dict_from_row(row, cursor)
        
        # If transaction is still pending, check status from M-Pesa
        if transaction["status"] == "pending":
            access_token = get_access_token()
            if not access_token:
                return {"error": "Failed to get access token"}
            
            password, timestamp = generate_password()
            
            url = f"{API_BASE_URL}/mpesa/stkpushquery/v1/query"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "BusinessShortCode": BUSINESS_SHORT_CODE,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            try:
                response = requests.post(url, json=payload, headers=headers)
                result = response.json()
                print(f"Transaction status query result: {result}")
                
                if "ResultCode" in result:
                    if result["ResultCode"] == "0":
                        # Update transaction status to completed
                        update_transaction_status(
                            checkout_request_id,
                            "completed",
                            result.get("ResultCode"),
                            result.get("ResultDesc")
                        )
                        
                        # Update order status
                        update_order_status(
                            transaction["order_type"],
                            transaction["order_id"],
                            "completed"
                        )
                        
                        return {
                            "success": True,
                            "status": "completed",
                            "message": "Payment completed successfully"
                        }
                    else:
                        # Update transaction status to failed
                        update_transaction_status(
                            checkout_request_id,
                            "failed",
                            result.get("ResultCode"),
                            result.get("ResultDesc")
                        )
                        
                        return {
                            "success": False,
                            "status": "failed",
                            "message": result.get("ResultDesc", "Payment failed")
                        }
                else:
                    return {
                        "status": "pending",
                        "message": "Payment is being processed"
                    }
            except Exception as e:
                print(f"Exception during status check: {e}")
                return {"error": str(e)}
        else:
            # Return status from database
            return {
                "status": transaction["status"],
                "message": transaction["result_desc"] if transaction["result_desc"] else 
                          "Payment completed" if transaction["status"] == "completed" else "Payment failed"
            }
    except Exception as e:
        print(f"Error checking transaction: {e}")
        return {"error": str(e)}
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def save_transaction_request(checkout_request_id, merchant_request_id, order_type, order_id, user_id, amount, phone_number):
    """Save M-Pesa transaction request to database"""
    connection = get_db_connection()
    if not connection:
        return False
    
    cursor = connection.cursor()
    
    try:
        query = """
        INSERT INTO mpesa_transactions
        (checkout_request_id, merchant_request_id, order_type, order_id, user_id, amount, phone_number)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            checkout_request_id,
            merchant_request_id,
            order_type,
            order_id,
            user_id,
            amount,
            phone_number
        ))
        connection.commit()
        return True
    except Error as e:
        print(f"Error saving transaction: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def update_transaction_status(checkout_request_id, status, result_code=None, result_desc=None):
    """Update M-Pesa transaction status in database"""
    connection = get_db_connection()
    if not connection:
        return False
    
    cursor = connection.cursor()
    
    try:
        query = """
        UPDATE mpesa_transactions
        SET status = %s, result_code = %s, result_desc = %s
        WHERE checkout_request_id = %s
        """
        cursor.execute(query, (status, result_code, result_desc, checkout_request_id))
        connection.commit()
        return True
    except Error as e:
        print(f"Error updating transaction: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def update_order_status(order_type, order_id, payment_status):
    """Update order payment status in database"""
    connection = get_db_connection()
    if not connection:
        return False
    
    cursor = connection.cursor()
    
    try:
        if order_type == "artwork":
            query = """
            UPDATE artwork_orders
            SET payment_status = %s
            WHERE id = %s
            """
        elif order_type == "exhibition":
            query = """
            UPDATE exhibition_bookings
            SET payment_status = %s
            WHERE id = %s
            """
        else:
            return False
        
        cursor.execute(query, (payment_status, order_id))
        connection.commit()
        
        # If it's an artwork order and payment is completed, update artwork status
        if order_type == "artwork" and payment_status == "completed":
            query = """
            UPDATE artworks a
            JOIN artwork_orders o ON a.id = o.artwork_id
            SET a.status = 'sold'
            WHERE o.id = %s
            """
            cursor.execute(query, (order_id,))
            connection.commit()
        
        # If it's an exhibition booking and payment is completed, update available slots
        if order_type == "exhibition" and payment_status == "completed":
            query = """
            UPDATE exhibitions e
            JOIN exhibition_bookings b ON e.id = b.exhibition_id
            SET e.available_slots = e.available_slots - b.slots
            WHERE b.id = %s
            """
            cursor.execute(query, (order_id,))
            connection.commit()
        
        return True
    except Error as e:
        print(f"Error updating order: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def handle_mpesa_callback(callback_data):
    """Handle M-Pesa callback data"""
    try:
        checkout_request_id = callback_data.get("CheckoutRequestID")
        result_code = callback_data.get("ResultCode")
        result_desc = callback_data.get("ResultDesc")
        
        if not checkout_request_id:
            return {"error": "Missing CheckoutRequestID"}
        
        if result_code == "0":
            # Payment successful
            status = "completed"
        else:
            # Payment failed
            status = "failed"
        
        # Update transaction status
        success = update_transaction_status(checkout_request_id, status, result_code, result_desc)
        
        if success:
            # Get transaction details
            connection = get_db_connection()
            if not connection:
                return {"error": "Database connection failed"}
            
            cursor = connection.cursor()
            
            try:
                query = """
                SELECT order_type, order_id FROM mpesa_transactions 
                WHERE checkout_request_id = %s
                """
                cursor.execute(query, (checkout_request_id,))
                row = cursor.fetchone()
                
                if row:
                    order_type = row[0]
                    order_id = row[1]
                    
                    # Update order status
                    update_order_status(order_type, order_id, status)
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
        
        return {"success": True}
    except Exception as e:
        print(f"Error handling M-Pesa callback: {e}")
        return {"error": str(e)}

def handle_stk_push_request(request_data):
    """Handle STK Push request from frontend"""
    try:
        # Extract all required fields from request data
        required_fields = ["phoneNumber", "amount", "orderType", "orderId", "userId", "accountReference"]
        missing_fields = [field for field in required_fields if field not in request_data or not request_data.get(field)]
        
        if missing_fields:
            return {"error": f"Missing required fields: {', '.join(missing_fields)}"}
        
        phone_number = request_data.get("phoneNumber")
        amount = request_data.get("amount")
        order_type = request_data.get("orderType")
        order_id = request_data.get("orderId")
        user_id = request_data.get("userId")
        account_reference = request_data.get("accountReference")
        
        # Log the request data for debugging
        print(f"STK Push request data: {request_data}")
        
        # Proceed with STK Push
        return initiate_stk_push(phone_number, amount, account_reference, order_type, order_id, user_id)
    except Exception as e:
        print(f"Error handling STK Push request: {e}")
        return {"error": str(e)}

def get_user_orders(user_id):
    """Get all orders and tickets for a user"""
    connection = get_db_connection()
    if not connection:
        return {"error": "Database connection failed"}
    
    cursor = connection.cursor()
    try:
        # Get artwork orders
        orders_query = """
        SELECT o.*, a.title as artwork_title, a.artist, a.image_url
        FROM artwork_orders o
        JOIN artworks a ON o.artwork_id = a.id
        WHERE o.user_id = %s
        ORDER BY o.created_at DESC
        """
        cursor.execute(orders_query, (user_id,))
        orders = [dict_from_row(row, cursor) for row in cursor.fetchall()]
        
        # Get exhibition bookings
        tickets_query = """
        SELECT b.*, e.title as exhibition_title, e.location, e.image_url
        FROM exhibition_bookings b
        JOIN exhibitions e ON b.exhibition_id = e.id
        WHERE b.user_id = %s
        ORDER BY b.created_at DESC
        """
        cursor.execute(tickets_query, (user_id,))
        tickets = [dict_from_row(row, cursor) for row in cursor.fetchall()]
        
        return {
            "orders": orders,
            "tickets": tickets
        }
    except Exception as e:
        print(f"Error getting user orders: {e}")
        return {"error": str(e)}
    finally:
        cursor.close()
        connection.close()

def get_all_admin_orders():
    """Get all orders and tickets for admin dashboard"""
    connection = get_db_connection()
    if not connection:
        return {"error": "Database connection failed"}
    
    cursor = connection.cursor()
    try:
        # Get all artwork orders
        orders_query = """
        SELECT o.*, u.name as customer_name, u.email as customer_email,
               a.title as artwork_title, a.artist, a.image_url
        FROM artwork_orders o
        JOIN users u ON o.user_id = u.id
        JOIN artworks a ON o.artwork_id = a.id
        ORDER BY o.created_at DESC
        """
        cursor.execute(orders_query)
        orders = [dict_from_row(row, cursor) for row in cursor.fetchall()]
        
        # Get all exhibition bookings
        tickets_query = """
        SELECT b.*, u.name as customer_name, u.email as customer_email,
               e.title as exhibition_title, e.location, e.image_url
        FROM exhibition_bookings b
        JOIN users u ON b.user_id = u.id
        JOIN exhibitions e ON b.exhibition_id = e.id
        ORDER BY b.created_at DESC
        """
        cursor.execute(tickets_query)
        tickets = [dict_from_row(row, cursor) for row in cursor.fetchall()]
        
        return {
            "orders": orders,
            "tickets": tickets
        }
    except Exception as e:
        print(f"Error getting admin orders: {e}")
        return {"error": str(e)}
    finally:
        cursor.close()
        connection.close()
