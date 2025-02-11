import { useState, useEffect } from "react";
import "./App.css"; // You can create an App.css for styling

function App() {
  const [wsIp, setWsIp] = useState("192.168.100.16"); // Default IP
  const [currentAddress, setCurrentAddressValue] = useState("");
  const [targetAddress, setTargetAddressValue] = useState(30);
  const [statusMessage, setStatusMessage] = useState(
    "Waiting for current address to be set."
  );
  const [receivedMessages, setReceivedMessages] = useState([]);
  const [ws, setWs] = useState(null);

  useEffect(() => {
    if (!wsIp) return;
    const wsProtocol =
      window.location.protocol === "https:" ? "wss://" : "ws://";
    const websocket = new WebSocket(`${wsIp}:3000`); // Adjust port as needed

    websocket.onopen = () => {
      console.log("WebSocket connected");
      setStatusMessage("WebSocket connected.");
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "status" || message.type === "error") {
        setStatusMessage(message.message);
      } else if (message.type === "received_data") {
        try {
          const receivedData = JSON.parse(
            message.data.substring(message.data.indexOf("{"))
          ); // Extract JSON part
          if (receivedData && receivedData.reply) {
            setReceivedMessages((prevMessages) => [
              ...prevMessages,
              message.data,
            ]);
          } else {
            console.log(
              "Received data without 'reply', not displaying:",
              message.data
            );
          }
        } catch (e) {
          console.error(
            "Error parsing received data as JSON:",
            e,
            message.data
          );
        }
      }
    };

    websocket.onclose = () => {
      console.log("WebSocket disconnected");
      setStatusMessage("WebSocket disconnected.");
    };

    websocket.onerror = (error) => {
      console.error("WebSocket error:", error);
      setStatusMessage("WebSocket error.");
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [wsIp]); // Depend on wsIp to reconnect when it changes

  const handleSetCurrentAddress = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({ type: "set_current_address", address: currentAddress })
      );
    } else {
      setStatusMessage("WebSocket not connected.");
    }
  };

  const handleSendCommand = (command) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      if (
        !isNaN(targetAddress) &&
        targetAddress >= 0 &&
        targetAddress <= 65535
      ) {
        ws.send(
          JSON.stringify({ type: "set_target_address", address: targetAddress })
        );
        ws.send(JSON.stringify({ type: "command", command: command }));
      } else {
        alert("Invalid target address.");
      }
    } else {
      setStatusMessage("WebSocket not connected.");
    }
  };

  return (
    <div className="App">
      <h1>LoRa Home Controller</h1>

      <div>
        <label htmlFor="wsIp">WebSocket Server IP:</label>
        <input
          type="text"
          id="wsIp"
          value={wsIp}
          onChange={(e) => setWsIp(e.target.value)}
        />
      </div>

      <div>
        <label htmlFor="currentAddress">Current Node Address (0-65535):</label>
        <input
          type="number"
          id="currentAddress"
          min="0"
          max="65535"
          value={currentAddress}
          onChange={(e) => setCurrentAddressValue(e.target.value)}
        />
        <button onClick={handleSetCurrentAddress}>Set Address</button>
      </div>

      <div>
        <label htmlFor="targetAddress">Target Node Address (0-65535):</label>
        <input
          type="number"
          id="targetAddress"
          min="0"
          max="65535"
          value={targetAddress}
          onChange={(e) => setTargetAddressValue(parseInt(e.target.value))}
        />
      </div>

      <div>
        <button onClick={() => handleSendCommand("ON")}>Motor ON</button>
        <button onClick={() => handleSendCommand("OFF")}>Motor OFF</button>
        <button onClick={() => handleSendCommand("STATUS")}>
          Motor STATUS
        </button>
      </div>

      <div id="status-display">Status: {statusMessage}</div>
      <div id="receive-display">
        Received messages:
        <ul>
          {receivedMessages.map((msg, index) => (
            <li key={index}>{msg}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default App;
