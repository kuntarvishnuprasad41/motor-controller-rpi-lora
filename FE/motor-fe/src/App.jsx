// src/App.js
import   { useState, useEffect, useRef } from "react";
import "./App.css";

function App() {
  const [receivedData, setReceivedData] = useState([]);
  const [targetAddress, setTargetAddress] = useState(30); // Default target address
  const ws = useRef(null);

  useEffect(() => {
    ws.current = new WebSocket("ws://192.168.100.16:8080"); // Connect to WebSocket server

    ws.current.onopen = () => {
      console.log("Connected to WebSocket server");
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setReceivedData((prevData) => [...prevData, data]);
    };

    ws.current.onclose = () => {
      console.log("Disconnected from WebSocket server");
    };

    return () => {
      ws.current.close();
    };
  }, []);

  const sendCommand = (command) => {
    if (ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ command, targetAddress }));
    } else {
      console.warn("WebSocket not connected.");
    }
  };
  const handleTargetAddressChange = (event) => {
    setTargetAddress(parseInt(event.target.value, 10));
  };

  return (
    <div className="App">
      <h1>LoRa Control Panel</h1>

      <div>
        <label htmlFor="targetAddress">Target Address:</label>
        <input
          type="number"
          id="targetAddress"
          value={targetAddress}
          onChange={handleTargetAddressChange}
          min="0"
          max="65535"
        />
      </div>

      <div>
        <button onClick={() => sendCommand("ON")}>Motor ON</button>
        <button onClick={() => sendCommand("OFF")}>Motor OFF</button>
        <button onClick={() => sendCommand("STATUS")}>Motor STATUS</button>
      </div>

      <h2>Received Data:</h2>
      <ul>
        {receivedData.map((item, index) => (
          <li key={index}>
            [{item.time}] {item.message}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;
