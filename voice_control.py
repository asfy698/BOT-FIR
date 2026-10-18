import controller
import RPi.GPIO as GPIO 
import time
## --- Keyboard Input Setup ---

def process_command(command):
    """Checks the typed command against known keywords and calls motor functions."""
    
    # Standardize the command for easy comparison
    command = command.lower().strip()
    
    # The commands are designed to match the original voice commands' intent
    if "forward" in command or "move forward" in command:
        print("Command recognized: Moving Forward.")
        controller.motors_forward()
        # The original code used a fixed time.sleep(2) and stop after the command, 
        # but for keyboard control, you might want to stop when the user types 'stop'.
        # For this example, I'll keep the momentary action to match the original flow
        # but you might remove the sleep/stop in a continuous keyboard control scheme.
        time.sleep(2) 
        controller.motors_stop()
    elif "backward" in command or "move backward" in command:
        print("Command recognized: Moving Backward.")
        controller.motors_backward()
        time.sleep(2)
        controller.motors_stop()
    elif "left" in command or "turn left" in command:
        print("Command recognized: Turning Left.")
        controller.motors_turning_L()
        time.sleep(1.5) 
        controller.motors_stop()
    elif "right" in command or "turn right" in command:
        print("Command recognized: Turning Right.")
        controller.motors_turning_R()
        time.sleep(1.5)
        controller.motors_stop()
    elif "stop" in command or "halt" in command:
        print("Command recognized: Stopping Motors.")
        controller.motors_stop()
    elif "exit" in command or "quit" in command:
        # Special command to break the loop
        return True
    else:
        print(f"Command '{command}' not recognized. Try 'forward', 'backward', 'left', 'right', 'stop', or 'exit'.")
    
    return False

def listen_for_commands():
    """Continuously listens for keyboard input for commands."""
    print("--- Keyboard Control System Ready ---")
    print("Type 'move forward', 'move backward', 'turn left', 'turn right', 'stop', or 'exit' and press Enter.")
    
    try:
        while True:
            # Prompt the user for input
            typed_command = input("\nEnter Command: ")
            
            # Process the input command
            should_exit = process_command(typed_command)
            
            if should_exit:
                break
                
    except KeyboardInterrupt:
        print("\nExiting keyboard control (Ctrl+C pressed).")
    except EOFError:
        print("\nExiting keyboard control (EOF/Ctrl+D pressed).")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        # Ensure motors are stopped and GPIO pins are cleaned up on exit
        print("Cleaning up GPIO...")
        controller.motors_stop() # Ensure motors are explicitly stopped one last time
        GPIO.cleanup() 
        print("Cleanup complete. Program terminated.")

if __name__ == "__main__":
    # Ensure motors are stopped before starting the listening loop (handled in cleanup now, but good practice)
    controller.motors_stop()
    listen_for_commands() 
