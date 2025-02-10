const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

app.use(express.static(path.join(__dirname, 'public')));

wss.on('connection', ws => {
    console.log('Client connected');

    ws.on('message', message => {
        console.log('[WebSocket Server] Received message:', message.toString()); // Log message on server
        try {
            const msg = JSON.parse(message.toString());
            if (msg.type === 'test') {
                console.log('[WebSocket Server] Test message received, sending reply.');
                ws.send(JSON.stringify({ type: 'test_reply', message: 'Hello from server!' }));
            }
        } catch (e) {
            console.error('Error parsing message:', e);
        }
    });

    ws.on('close', () => {
        console.log('Client disconnected');
    });

    ws.on('error', error => {
        console.error('WebSocket error:', error);
    });
});


app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'test_index.html')); // Serve test_index.html
});


const PORT = 3000;
server.listen(PORT, () => {
    console.log(`Server started on http://192.168.100.16:${PORT}`);
});