loop:
    if in LISTENING state:
        listen for LoRa message
        if message received:
            parse message (see Message Format below)
            if message is a COMMAND (ON, OFF, STATUS_REQUEST, SET_TIMER):
                set request_pending = true
                switch to PROCESSING_REQUEST state
            else:
                ignore message (or log it for debugging)

    if in TRANSMITTING_STATUS state:
        construct status message (see Message Format below)
        transmit message
        switch to LISTENING state

    if in PROCESSING_REQUEST state:
        if command is ON:
            turn on relay 1 (motor ON)
            record motor_on_time  (using RTC or persistent counter)
            set motor_run_timer // If Timer is set
            set MOTOR_RUNNING state to True
        else if command is OFF:
            turn off relay 2 (motor OFF)
            update total_run_time (add time since motor_on_time)
            set motor_run_timer to 0
            reset MOTOR_RUNNING to False
        else if command is STATUS_REQUEST:
            // Do nothing, just prepare the response
        else if command is SET_TIMER:
            set motor_run_timer = received_duration
            turn on relay 1 (motor ON)  // Start the motor immediately
            record motor_on_time
            set MOTOR_RUNNING to True

        request_pending = false
        switch to TRANSMITTING_RESPONSE state

    if in TRANSMITTING_RESPONSE state:
        construct response message (see Message Format below)
        transmit message
        switch to LISTENING state

    if scheduled_update_timer expired:
            if MOTOR_RUNNING or MOTOR_ERROR:
                 switch to TRANSMITTING_STATUS state
            reset scheduled_update_timer

    if motor power is lost (detect using a separate input pin): //VERY IMPORTANT
        set MOTOR_ERROR = True
        update total_run_time (add time since motor_on_time)
        IMMEDIATELY switch to TRANSMITTING_STATUS state (send an alert!)
        set MOTOR_RUNNING = False // Motor is no longer running as per command
        set motor_run_timer = 0

   if motor_run_timer expired and MOTOR_RUNNING:
        turn off relay 2 (motor OFF)
        update total_run_time
        set MOTOR_RUNNING = False
        set motor_run_timer = 0
        switch to TRANSMITTING_STATUS state // Notify that timer finished
