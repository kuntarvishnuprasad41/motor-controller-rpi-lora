loop:
    if in LISTENING state:
        check for user input (button presses, etc.)
        if user requests ON:
            set command = ON
            switch to TRANSMITTING_REQUEST state
        else if user requests OFF:
            set command = OFF
            switch to TRANSMITTING_REQUEST state
        else if user requests STATUS:
            set command = STATUS_REQUEST
            switch to TRANSMITTING_REQUEST state
       else if user sets timer:
            set command = SET_TIMER
            set timer_duration = user_input
            switch to TRANSMITTING_REQUEST state

        listen for LoRa message //Listen at the same time,
        if message received:
            parse message //Will be a status update.
            if message is a STATUS message:
                update last_received_status and last_received_run_time
                display status to user

        if status_request_timer expired (optional):
            set command = STATUS_REQUEST
            switch to TRANSMITTING_REQUEST state
            reset status_request_timer


    if in TRANSMITTING_REQUEST state:
        construct request message (see Message Format below)
        transmit message
        switch to WAITING_FOR_RESPONSE state
        start request_timer

    if in WAITING_FOR_RESPONSE state:
        listen for LoRa message
        if message received:
            parse message
            if message is a RESPONSE message:
                update last_received_status and last_received_run_time (if applicable)
                display status/response to user
                switch to LISTENING state
        else if request_timer expired:
            // Handle timeout (e.g., display an error to the user)
            switch to LISTENING state