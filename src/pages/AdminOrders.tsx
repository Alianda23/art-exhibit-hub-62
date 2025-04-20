
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { format } from 'date-fns';

// Types for orders
interface Order {
  id: string;
  customer_name: string;
  customer_email: string;
  artwork_title: string;
  created_at: string;
  total_amount: number;
  payment_status: 'pending' | 'completed' | 'failed';
}

const AdminOrders = () => {
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);

  const { data: ordersData, isLoading, error } = useQuery({
    queryKey: ['admin-orders'],
    queryFn: async () => {
      const response = await fetch('/orders', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (!response.ok) {
        throw new Error('Failed to fetch orders');
      }
      return response.json();
    }
  });

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'PP p');
    } catch (error) {
      return dateString;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'pending':
        return 'bg-yellow-500';
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <h1 className="text-2xl font-bold mb-6">Orders Management</h1>
        <div className="flex justify-center items-center h-64">
          <p>Loading orders...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-8 px-4">
        <h1 className="text-2xl font-bold mb-6">Orders Management</h1>
        <div className="flex justify-center items-center h-64">
          <p className="text-red-500">Error loading orders: {(error as Error).message}</p>
        </div>
      </div>
    );
  }

  const orders = ordersData?.orders || [];

  return (
    <div className="container mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold mb-6">Orders Management</h1>
      
      <div className="grid gap-6 md:grid-cols-[2fr_1fr]">
        <Card className="p-4">
          <h2 className="text-xl font-semibold mb-4">All Orders</h2>
          
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order ID</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((order: Order) => (
                  <TableRow key={order.id}>
                    <TableCell className="font-mono">{order.id}</TableCell>
                    <TableCell>{order.customer_name}</TableCell>
                    <TableCell>{formatDate(order.created_at)}</TableCell>
                    <TableCell>KES {order.total_amount.toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(order.payment_status)}>
                        {order.payment_status.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => setSelectedOrder(order)}
                      >
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
        
        <Card className="p-4">
          {selectedOrder ? (
            <div>
              <h2 className="text-xl font-semibold mb-4">Order Details</h2>
              
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <p className="text-sm text-gray-500">Order ID:</p>
                    <p className="font-mono">{selectedOrder.id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Date:</p>
                    <p>{formatDate(selectedOrder.created_at)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Customer:</p>
                    <p className="font-medium">{selectedOrder.customer_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Email:</p>
                    <p>{selectedOrder.customer_email}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Artwork:</p>
                    <p>{selectedOrder.artwork_title}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Amount:</p>
                    <p className="font-medium">KES {selectedOrder.total_amount.toLocaleString()}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm text-gray-500">Status:</p>
                    <Badge className={getStatusColor(selectedOrder.payment_status)}>
                      {selectedOrder.payment_status.toUpperCase()}
                    </Badge>
                  </div>
                </div>
                
                <div className="pt-4 flex justify-end space-x-2">
                  <Button variant="outline" size="sm">
                    Download Invoice
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-64">
              <p className="text-gray-500">Select an order to view details</p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default AdminOrders;
