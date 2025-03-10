import React, { useEffect, useState } from 'react';
import api from '../services/api';

const Dashboard = () => {
  const [devices, setDevices] = useState([]);

  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const response = await api.get('/devices');
        setDevices(response.data);
      } catch (error) {
        console.error('Failed to fetch devices:', error);
      }
    };
    fetchDevices();
  }, []);

  return (
    <div>
      <h1>Managed Devices</h1>
      <ul>
        {devices.map(device => (
          <li key={device.id}>
            {device.name} - {device.ip}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Dashboard;