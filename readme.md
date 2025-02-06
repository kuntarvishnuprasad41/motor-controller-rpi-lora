# LoRa-Controlled 3-Phase Motor System Design

This document outlines the design and communication protocol for a system controlling a 3-phase motor using two Raspberry Pi Zeros with LoRa SX1268 modules. The system addresses the half-duplex nature of LoRa communication and provides features for remote control, status monitoring, and timer-based operation.

## Core Concepts

The system utilizes a combination of **Time-Division Multiplexing (TDM)** and a **Request/Response** pattern to manage communication between the two LoRa modules.

*   **Default State (Receiver):** Both the "Home" (user interface) and "Motor" units primarily operate in receive mode, listening for incoming messages.
*   **Scheduled Motor Updates (TDM):** The Motor unit periodically (every 10 minutes) switches to transmit mode and sends a status update.
*   **On-Demand Requests (Request/Response):** The Home unit transmits commands (ON, OFF, STATUS REQUEST, SET_TIMER) and waits for a response from the Motor unit.
*   **Prioritization:** Motor status updates due to power loss or errors have immediate priority.

## System Components

*   **Home Unit (User Interface):**
    *   Raspberry Pi Zero
    *   LoRa SX1268 Module
    *   User Input (buttons, etc.)
    *   Display (optional, for showing status)
*   **Motor Unit (at the motor):**
    *   Raspberry Pi Zero
    *   LoRa SX1268 Module
    *   Two Relays (one for ON, one for OFF)
    *   Power Loss Detection Circuit (connected to a GPIO pin)
    *   Real-Time Clock (RTC) Module (recommended)

## Communication Protocol and Logic

### 1. Motor Unit

*   **States:**
    *   `LISTENING`: Default state. Listening for LoRa messages.
    *   `TRANSMITTING_STATUS`: Sending scheduled or error status updates.
    *   `PROCESSING_REQUEST`: Handling a request from the Home unit.
    *   `TRANSMITTING_RESPONSE`: Sending a response after processing.
    *   `MOTOR_RUNNING`: Tracks whether the motor should be on.
    *   `MOTOR_ERROR`: Tracks power loss or other errors.

*   **Variables:**
    *   `motor_on_time`: Timestamp of the last motor start (persistently stored).
    *   `total_run_time`: Accumulated motor run time (persistently stored).
    *   `scheduled_update_timer`: Timer for 10-minute status updates.
    *   `request_pending`: Flag indicating an active request.
    *   `motor_run_timer`: Timer for duration-based motor operation.

*   **Loop Logic (Pseudocode):**
```
loop:
if in LISTENING state:
listen for LoRa message
if message received:
parse message
if message is a COMMAND:
set request_pending = true
switch to PROCESSING_REQUEST state

if in TRANSMITTING_STATUS state:
    construct status message
    transmit message
    switch to LISTENING state

if in PROCESSING_REQUEST state:
    if command is ON:
        turn on relay 1
        record motor_on_time
        set motor_run_timer (if applicable)
        set MOTOR_RUNNING = True
    else if command is OFF:
        turn off relay 2
        update total_run_time
        set motor_run_timer = 0
        set MOTOR_RUNNING = False
    else if command is STATUS_REQUEST:
        // Prepare response
    else if command is SET_TIMER:
        set motor_run_timer
        turn on relay 1
        record motor_on_time
        set MOTOR_RUNNING = True

    request_pending = false
    switch to TRANSMITTING_RESPONSE state

if in TRANSMITTING_RESPONSE state:
    construct response message
    transmit message
    switch to LISTENING state

if scheduled_update_timer expired:
    if MOTOR_RUNNING or MOTOR_ERROR:
        switch to TRANSMITTING_STATUS state
    reset scheduled_update_timer

if motor power is lost:
    set MOTOR_ERROR = True
    update total_run_time
    IMMEDIATELY switch to TRANSMITTING_STATUS state (send alert)
    set MOTOR_RUNNING = False
    set motor_run_timer = 0

if motor_run_timer expired and MOTOR_RUNNING:
    turn off relay 2
    update total_run_time
    set MOTOR_RUNNING = False
    set motor_run_timer = 0
    switch to TRANSMITTING_STATUS state
```

### 2. Home Unit

*   **States:**
    *   `LISTENING`: Default state.  Waiting for user input or receiving status updates.
    *   `TRANSMITTING_REQUEST`: Sending a command.
    *   `WAITING_FOR_RESPONSE`: Awaiting a response from the Motor unit.

*   **Variables:**
    *   `last_received_status`: Last received motor status.
    *   `last_received_run_time`: Last received total run time.
    *   `request_timer`: Timeout for waiting for a response.
    *   `status_request_timer`: Optional timer for periodic status requests.

*   **Loop Logic (Pseudocode):**

```

loop:
if in LISTENING state:
check for user input
if user requests ON/OFF/STATUS/SET_TIMER:
set command
switch to TRANSMITTING_REQUEST state

listen for LoRa message
    if message received (STATUS update):
        update last_received_status and last_received_run_time
        display status

    if status_request_timer expired (optional):
        set command = STATUS_REQUEST
        switch to TRANSMITTING_REQUEST state
        reset status_request_timer

if in TRANSMITTING_REQUEST state:
    construct request message
    transmit message
    switch to WAITING_FOR_RESPONSE state
    start request_timer

if in WAITING_FOR_RESPONSE state:
    listen for LoRa message
    if message received (RESPONSE):
        update status/run time
        display information
        switch to LISTENING state
    else if request_timer expired:
        // Handle timeout
        switch to LISTENING state
```


### 3. Message Format

*   **Request Messages (Home -> Motor):**  `[MESSAGE_TYPE, DATA]`
    *   `MESSAGE_TYPE` (1 byte):
        *   `0x01`: ON
        *   `0x02`: OFF
        *   `0x03`: STATUS_REQUEST
        *   `0x04`: SET_TIMER
    *   `DATA`: Timer duration (for `SET_TIMER`)

*   **Status/Response Messages (Motor -> Home):** `[MESSAGE_TYPE, MOTOR_STATUS, RUN_TIME_MSB, RUN_TIME_LSB, ERROR_CODE]`
    *   `MESSAGE_TYPE` (1 byte):
        *   `0x10`: STATUS UPDATE
    *   `MOTOR_STATUS` (1 byte):
        *   `0x00`: OFF
        *   `0x01`: ON
        *   `0xFF`: ERROR
    *   `RUN_TIME_MSB`, `RUN_TIME_LSB` (2 bytes): Total run time (e.g., in seconds).
    *   `ERROR_CODE` (1 byte):
        *    `0x00` : No Error
        *    `0x01` : Power Failure

## Key Considerations

*   **Error Handling:** Implement retries and acknowledgments (if needed) for critical commands.
*   **Power Management (Motor Unit):** Utilize sleep modes for the Pi and LoRa module to conserve power.
*   **Real-Time Clock (RTC):** An RTC module is highly recommended for accurate timekeeping.
*   **Persistent Storage:** Store `total_run_time` and `motor_on_time` in a file to handle power outages.
*   **Security:** Consider encryption if unauthorized control is a concern.
*   **Collision Avoidance:** Add a small random delay before scheduled transmissions to minimize collisions.
*   **Library Adaptation:** Modify the chosen LoRa library to implement the state machine and message formats.
*   **Thorough Testing:**  Test all use cases and failure scenarios extensively.

This design document provides a comprehensive framework for the LoRa-controlled motor system.  Careful implementation and testing are essential for a successful and reliable solution.