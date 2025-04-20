
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { formatPrice } from '@/utils/formatters';
import { useToast } from '@/hooks/use-toast';
import { initiateSTKPush, checkTransactionStatus, finalizeOrder } from '@/utils/mpesa';
import { DollarSign, Loader2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

type PendingOrder = {
  type: 'artwork' | 'exhibition';
  itemId: string;
  title: string;
  totalAmount: number;
  name: string;
  email: string;
  phone?: string;
  deliveryAddress?: string;
  slots?: number;
  pricePerSlot?: number;
  price?: number;
  deliveryFee?: number;
};

const Payment = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { currentUser } = useAuth();
  const [order, setOrder] = useState<PendingOrder | null>(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState<'pending' | 'processing' | 'success' | 'failed'>('pending');
  const [checkoutRequestId, setCheckoutRequestId] = useState('');
  const [checkingStatus, setCheckingStatus] = useState(false);
  const [statusCheckAttempts, setStatusCheckAttempts] = useState(0);

  useEffect(() => {
    // Get order details from localStorage
    const pendingOrder = localStorage.getItem('pendingOrder');
    if (!pendingOrder) {
      navigate('/');
      return;
    }

    try {
      const orderData = JSON.parse(pendingOrder) as PendingOrder;
      setOrder(orderData);
      setPhoneNumber(orderData.phone || '');
    } catch (error) {
      console.error('Error parsing order data:', error);
      navigate('/');
    }
  }, [navigate]);

  // Effect to check payment status
  useEffect(() => {
    let statusCheckInterval: number | null = null;
    
    const checkStatus = async () => {
      if (!checkoutRequestId || paymentStatus !== 'processing' || checkingStatus) {
        return;
      }
      
      setCheckingStatus(true);
      
      try {
        const statusResponse = await checkTransactionStatus(checkoutRequestId);
        
        if (statusResponse.ResultCode === "0") {
          // Payment successful
          clearInterval(statusCheckInterval as number);
          
          // Update payment status
          setPaymentStatus('success');
          
          // Finalize the order in the backend
          if (order && currentUser) {
            const orderData = {
              ...order,
              userId: currentUser.id,
              phoneNumber,
              checkoutRequestId,
              paymentStatus: 'completed'
            };
            
            // Call API to save order/booking to database
            const finalizeResponse = await finalizeOrder(
              checkoutRequestId,
              order.type,
              orderData
            );
            
            if (finalizeResponse.success) {
              // Navigate to success page with order details
              navigate(`/payment-success?type=${order.type}&id=${finalizeResponse.orderId}&title=${encodeURIComponent(order.title)}`);
            } else {
              throw new Error("Failed to finalize order");
            }
          }
        } else if (statusResponse.errorCode === "500.001.1001") {
          // Transaction still in process, continue checking
          setStatusCheckAttempts(prev => prev + 1);
          
          // After 10 attempts (about 50 seconds), give up
          if (statusCheckAttempts >= 10) {
            clearInterval(statusCheckInterval as number);
            setPaymentStatus('failed');
            toast({
              title: "Payment timeout",
              description: "We couldn't confirm your payment. Please try again or contact support.",
              variant: "destructive"
            });
          }
        } else {
          // Payment failed or cancelled
          clearInterval(statusCheckInterval as number);
          setPaymentStatus('failed');
          toast({
            title: "Payment failed",
            description: statusResponse.ResultDesc || "There was an issue with your payment. Please try again.",
            variant: "destructive"
          });
        }
      } catch (error) {
        console.error('Error checking payment status:', error);
        
        // After 10 attempts, give up
        if (statusCheckAttempts >= 10) {
          clearInterval(statusCheckInterval as number);
          setPaymentStatus('failed');
          toast({
            title: "Error checking payment",
            description: "We couldn't verify your payment status. Please check your M-Pesa messages.",
            variant: "destructive"
          });
        }
      } finally {
        setCheckingStatus(false);
      }
    };
    
    if (checkoutRequestId && paymentStatus === 'processing') {
      // Check status immediately
      checkStatus();
      
      // Then check every 5 seconds
      statusCheckInterval = window.setInterval(checkStatus, 5000);
    }
    
    return () => {
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
      }
    };
  }, [checkoutRequestId, paymentStatus, checkingStatus, statusCheckAttempts, order, currentUser, navigate, phoneNumber, toast]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate phone number
    if (!phoneNumber) {
      toast({
        title: "Error",
        description: "Please enter your phone number for M-Pesa payment",
        variant: "destructive"
      });
      return;
    }
    
    // Simple validation for Kenyan phone numbers
    const phoneRegex = /^(?:\+254|0)([17][0-9]{8})$/;
    if (!phoneRegex.test(phoneNumber)) {
      toast({
        title: "Error",
        description: "Please enter a valid Kenyan phone number (starting with +254, 0, or 07...)",
        variant: "destructive"
      });
      return;
    }
    
    setIsSubmitting(true);
    setPaymentStatus('processing');
    
    try {
      if (!order) {
        throw new Error('Order details not found');
      }
      
      if (!currentUser || !currentUser.id) {
        throw new Error('User not logged in or user ID not found');
      }

      // Generate a reference for this transaction
      const accountReference = order.type === 'artwork' 
        ? `ART-${order.itemId}` 
        : `EXH-${order.itemId}`;

      console.log('Sending payment with the following details:', {
        phoneNumber,
        amount: order.totalAmount,
        orderType: order.type,
        orderId: order.itemId,
        userId: currentUser.id,
        accountReference
      });

      // Call M-Pesa STK Push
      const response = await initiateSTKPush(
        phoneNumber,
        order.totalAmount,
        order.type,
        order.itemId,
        accountReference
      );
      
      if (response.error) {
        throw new Error(response.error);
      }
      
      setCheckoutRequestId(response.CheckoutRequestID);
      setStatusCheckAttempts(0);
      
      toast({
        title: "Payment initiated",
        description: "Please check your phone and enter your M-Pesa PIN to complete the payment",
      });
      
    } catch (error) {
      console.error('Payment error:', error);
      setIsSubmitting(false);
      setPaymentStatus('failed');
      
      toast({
        title: "Payment failed",
        description: error instanceof Error ? error.message : "Failed to process your payment. Please try again.",
        variant: "destructive"
      });
    }
  };

  const handleTryAgain = () => {
    setPaymentStatus('pending');
    setIsSubmitting(false);
    setCheckoutRequestId('');
    setStatusCheckAttempts(0);
  };

  if (!order) {
    return (
      <div className="py-16 px-4 text-center">
        <h1 className="text-2xl font-semibold mb-4">No Order Found</h1>
        <p className="mb-6">Please select an item to purchase first.</p>
        <Button onClick={() => navigate('/')}>
          Back to Home
        </Button>
      </div>
    );
  }

  return (
    <div className="py-12 px-4 md:px-6 bg-secondary min-h-screen">
      <div className="container mx-auto max-w-md">
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="p-6 md:p-8">
            <h1 className="font-serif text-3xl font-bold mb-6 text-center">Payment</h1>
            
            <div className="mb-8">
              <h3 className="font-medium text-lg mb-4">Order Summary</h3>
              <div className="bg-secondary rounded-lg p-4 mb-6">
                <div className="mb-4">
                  <h4 className="font-medium">{order.title}</h4>
                  <p className="text-sm text-gray-600">
                    {order.type === 'artwork' ? 'Artwork Purchase' : 'Exhibition Booking'}
                  </p>
                </div>
                
                <div className="border-t border-gray-200 pt-3">
                  {order.type === 'artwork' && (
                    <>
                      <div className="flex justify-between mb-1">
                        <span>Price:</span>
                        <span>{formatPrice(order.price || 0)}</span>
                      </div>
                      <div className="flex justify-between mb-1">
                        <span>Delivery:</span>
                        <span>{formatPrice(order.deliveryFee || 0)}</span>
                      </div>
                    </>
                  )}
                  
                  {order.type === 'exhibition' && (
                    <div className="flex justify-between mb-1">
                      <span>Tickets:</span>
                      <span>{order.slots} x {formatPrice(order.pricePerSlot || 0)}</span>
                    </div>
                  )}
                  
                  <div className="flex justify-between font-bold text-lg mt-2">
                    <span>Total:</span>
                    <span>{formatPrice(order.totalAmount)}</span>
                  </div>
                </div>
              </div>
              
              {paymentStatus === 'processing' ? (
                <div className="text-center py-8">
                  <Loader2 className="h-12 w-12 animate-spin mx-auto mb-4 text-gold" />
                  <h3 className="font-bold text-lg mb-2">Payment Processing</h3>
                  <p className="mb-2">Please check your phone and enter your M-Pesa PIN.</p>
                  <p className="text-sm text-gray-500">We're waiting for confirmation from M-Pesa...</p>
                </div>
              ) : paymentStatus === 'failed' ? (
                <div className="text-center py-8">
                  <div className="bg-red-100 text-red-800 p-4 rounded-lg mb-4">
                    <h3 className="font-bold text-lg">Payment Failed</h3>
                    <p>Something went wrong with your payment. Please try again.</p>
                  </div>
                  <Button onClick={handleTryAgain} className="mt-4">
                    Try Again
                  </Button>
                </div>
              ) : (
                <div className="mb-6">
                  <h3 className="font-medium text-lg mb-4">M-Pesa Payment</h3>
                  <form onSubmit={handleSubmit}>
                    <div className="space-y-6">
                      <div>
                        <Label htmlFor="phoneNumber">Phone Number (for M-Pesa) *</Label>
                        <Input
                          id="phoneNumber"
                          value={phoneNumber}
                          onChange={(e) => setPhoneNumber(e.target.value)}
                          placeholder="+254..."
                          required
                        />
                        <p className="text-sm text-gray-500 mt-1">
                          Enter the phone number to receive M-Pesa payment request
                        </p>
                      </div>
                      
                      <Button 
                        type="submit" 
                        className="w-full bg-gold hover:bg-gold-dark text-white py-6 text-lg"
                        disabled={isSubmitting}
                      >
                        {isSubmitting ? (
                          <span className="flex items-center justify-center">
                            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                            Processing...
                          </span>
                        ) : (
                          <span className="flex items-center justify-center">
                            <DollarSign className="mr-2 h-5 w-5" />
                            Pay with M-Pesa
                          </span>
                        )}
                      </Button>
                      
                      <p className="text-sm text-gray-500 text-center">
                        You will receive an M-Pesa prompt on your phone to complete payment
                      </p>
                    </div>
                  </form>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Payment;
