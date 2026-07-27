import curses
import random
import time
from pynput import keyboard

# Global set to track currently pressed keys
pressed_keys = set()

def on_press(key):
    try:
        if hasattr(key, 'char') and key.char:
            pressed_keys.add(key.char.lower())
        else:
            pressed_keys.add(key)
    except AttributeError:
        pass

def on_release(key):
    try:
        if hasattr(key, 'char') and key.char:
            pressed_keys.discard(key.char.lower())
        else:
            pressed_keys.discard(key)
    except AttributeError:
        pass

def main(stdscr):
    # Hide cursor
    curses.curs_set(0)
    stdscr.nodelay(True)

    # Start non-blocking keyboard listener
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    sh, sw = stdscr.getmaxyx()

    if sh < 15 or sw < 50:
        stdscr.addstr(0, 0, "Terminal window too small! Please enlarge and restart.")
        stdscr.refresh()
        time.sleep(2)
        listener.stop()
        return

    # Game configuration
    paddle_height = 4
    left_y = sh // 2 - paddle_height // 2
    right_y = sh // 2 - paddle_height // 2

    ball_x = sw // 2
    ball_y = sh // 2
    ball_dx = random.choice([-1, 1])
    ball_dy = random.choice([-1, 1])

    score_left = 0
    score_right = 0

    # Main Game Loop (~30 FPS)
    frame_delay = 0.035

    try:
        while True:
            # Handle Quit
            if 'q' in pressed_keys:
                break

            # Continuous movement checks
            if 'w' in pressed_keys:
                left_y = max(1, left_y - 1)
            if 's' in pressed_keys:
                left_y = min(sh - paddle_height - 1, left_y + 1)

            if keyboard.Key.up in pressed_keys:
                right_y = max(1, right_y - 1)
            if keyboard.Key.down in pressed_keys:
                right_y = min(sh - paddle_height - 1, right_y + 1)

            # Update ball position
            ball_x += ball_dx
            ball_y += ball_dy

            # Wall bounces
            if ball_y <= 1:
                ball_y = 1
                ball_dy *= -1
            elif ball_y >= sh - 2:
                ball_y = sh - 2
                ball_dy *= -1

            # Left paddle collision
            if ball_x == 3 and left_y <= ball_y < left_y + paddle_height:
                ball_dx = 1
            # Right paddle collision
            elif ball_x == sw - 4 and right_y <= ball_y < right_y + paddle_height:
                ball_dx = -1

            # Scoring
            if ball_x <= 1:
                score_right += 1
                ball_x, ball_y = sw // 2, sh // 2
                ball_dx, ball_dy = 1, random.choice([-1, 1])
            elif ball_x >= sw - 2:
                score_left += 1
                ball_x, ball_y = sw // 2, sh // 2
                ball_dx, ball_dy = -1, random.choice([-1, 1])

            # Render Frame
            stdscr.erase()

            # Header / Score
            score_str = f" Player 1: {score_left}  |  Player 2: {score_right} "
            stdscr.addstr(0, max(0, (sw - len(score_str)) // 2), score_str)

            # Center line
            for y in range(1, sh - 1):
                stdscr.addch(y, sw // 2, '|')

            # Left paddle
            for y in range(left_y, left_y + paddle_height):
                stdscr.addch(y, 3, '#')

            # Right paddle
            for y in range(right_y, right_y + paddle_height):
                stdscr.addch(y, sw - 4, '#')

            # Ball
            stdscr.addch(ball_y, ball_x, 'O')

            # Controls footer
            controls = "Hold W/S: Player 1 | Hold Up/Down: Player 2 | Q: Quit"
            stdscr.addstr(sh - 1, max(0, (sw - len(controls)) // 2), controls)

            stdscr.refresh()
            time.sleep(frame_delay)

    finally:
        listener.stop()

if __name__ == "__main__":
    curses.wrapper(main)