
// M-Pesa API utilities

// M-Pesa credentials
const CONSUMER_KEY = "sMwMwGZ8oOiSkNrUIrPbcCeWIO8UiQ3SV4CyX739uAyZVs1F";
const CONSUMER_SECRET = "A3Hs5zRY3nDCn7XpxPuc1iAKpfy6UDdetiCalIAfuAIpgTROI5yCqqOewDfThh2o";
const API_URL = 'http://localhost:8000';
const CALLBACK_URL = "https://webhook.site/3c1f62b5-4214-47d6-9f26-71c1f4b9c8f0";
const API_BASE_URL = "https://sandbox.safaricom.co.ke";

// Function to initiate STK Push
export const initiateSTKPush = async (
  phoneNumber: string,
  amount: number,
  orderType: 'artwork' | 'exhibition',
  orderId: string,
  accountReference: string
): Promise<any> => {
  try {
    // Format phone number to match M-Pesa requirements (remove '+' if present)
    const formattedPhone = phoneNumber.startsWith('+') 
      ? phoneNumber.substring(1) 
      : phoneNumber;
    
    // Add validation for Kenyan phone numbers
    // Should start with 254 (country code)
    let validatedPhone = formattedPhone;
    if (validatedPhone.startsWith('0')) {
      // Convert format from 07XXXXXXXX to 2547XXXXXXXX
      validatedPhone = '254' + validatedPhone.substring(1);
    } else if (!validatedPhone.startsWith('254')) {
      // Add country code if missing
      validatedPhone = '254' + validatedPhone;
    }
    
    console.log(`Initiating STK Push for phone: ${validatedPhone}, amount: ${amount}, order type: ${orderType}, orderId: ${orderId}`);
    
    // Add user ID to request body
    const userId = localStorage.getItem('userId') || '';
    
    // Ensure all required fields are included
    const requestBody = {
      phoneNumber: validatedPhone,
      amount: Math.round(amount), // Ensure amount is an integer
      orderType,
      orderId,
      userId,
      accountReference,
      callbackUrl: CALLBACK_URL
    };
    
    console.log('STK Push request body:', requestBody);
    
    const response = await fetch(`${API_URL}/mpesa/stk-push`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      console.error('STK Push failed with server response:', errorData);
      throw new Error(`M-Pesa API Error: ${errorData.error || 'Unknown error'}`);
    }
    
    const responseData = await response.json();
    console.log('STK Push response:', responseData);
    return responseData;
  } catch (error) {
    console.error('M-Pesa STK Push error:', error);
    throw error;
  }
};

// Function to check transaction status
export const checkTransactionStatus = async (checkoutRequestId: string): Promise<any> => {
  try {
    console.log(`Checking transaction status for checkoutRequestId: ${checkoutRequestId}`);
    
    const response = await fetch(`${API_URL}/mpesa/status/${checkoutRequestId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      console.error('Transaction status check failed with server response:', errorData);
      throw new Error(`M-Pesa API Error: ${errorData.error || 'Unknown error'}`);
    }
    
    const responseData = await response.json();
    console.log('Transaction status response:', responseData);
    return responseData;
  } catch (error) {
    console.error('M-Pesa transaction status check error:', error);
    throw error;
  }
};

// Function to finalize order after payment
export const finalizeOrder = async (
  checkoutRequestId: string,
  orderType: 'artwork' | 'exhibition',
  orderData: any
): Promise<any> => {
  try {
    const response = await fetch(`${API_URL}/orders/finalize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        checkoutRequestId,
        orderType,
        orderData
      }),
    });
    
    return await response.json();
  } catch (error) {
    console.error('Order finalization error:', error);
    throw error;
  }
};

// Function to get user orders
export const getUserOrders = async (userId: string): Promise<any> => {
  try {
    const response = await fetch(`${API_URL}/orders/user/${userId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    return await response.json();
  } catch (error) {
    console.error('Get user orders error:', error);
    throw error;
  }
};

// Function to generate exhibition ticket
export const generateExhibitionTicket = async (bookingId: string): Promise<any> => {
  try {
    const response = await fetch(`${API_URL}/tickets/generate/${bookingId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    return await response.json();
  } catch (error) {
    console.error('Ticket generation error:', error);
    throw error;
  }
};
