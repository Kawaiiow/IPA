import curses
import random
import time

def main(stdscr):
    # Hide cursor
    curses.curs_set(0)
    # Non-blocking keyboard input
    stdscr.nodelay(True)
    # Frame delay in milliseconds (~25 FPS)
    stdscr.timeout(40)

    # Screen dimensions
    sh, sw = stdscr.getmaxyx()

    # Check minimum window size
    if sh < 15 or sw < 50:
        stdscr.addstr(0, 0, "Terminal window too small! Please enlarge and restart.")
        stdscr.refresh()
        time.sleep(2)
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

    while True:
        # Handle key input
        key = stdscr.getch()

        if key in (ord('q'), ord('Q')):
            break
        elif key in (ord('w'), ord('W')):
            left_y = max(1, left_y - 1)
        elif key in (ord('s'), ord('S')):
            left_y = min(sh - paddle_height - 1, left_y + 1)
        elif key == curses.KEY_UP:
            right_y = max(1, right_y - 1)
        elif key == curses.KEY_DOWN:
            right_y = min(sh - paddle_height - 1, right_y + 1)

        # Update ball position
        ball_x += ball_dx
        ball_y += ball_dy

        # Bounce off top and bottom walls
        if ball_y <= 1:
            ball_y = 1
            ball_dy *= -1
        elif ball_y >= sh - 2:
            ball_y = sh - 2
            ball_dy *= -1

        # Left paddle collision (paddle at x = 3)
        if ball_x == 3 and left_y <= ball_y < left_y + paddle_height:
            ball_dx = 1
        # Right paddle collision (paddle at x = sw - 4)
        elif ball_x == sw - 4 and right_y <= ball_y < right_y + paddle_height:
            ball_dx = -1

        # Out-of-bounds (Scoring)
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

        # Draw scores at top
        score_str = f" Player 1: {score_left}  |  Player 2: {score_right} "
        stdscr.addstr(0, max(0, (sw - len(score_str)) // 2), score_str)

        # Draw center line
        for y in range(1, sh - 1):
            stdscr.addch(y, sw // 2, '|')

        # Draw left paddle
        for y in range(left_y, left_y + paddle_height):
            stdscr.addch(y, 3, '#')

        # Draw right paddle
        for y in range(right_y, right_y + paddle_height):
            stdscr.addch(y, sw - 4, '#')

        # Draw ball
        stdscr.addch(ball_y, ball_x, 'O')

        # Draw controls footer
        controls = "W/S: Player 1 | Up/Down: Player 2 | Q: Quit"
        stdscr.addstr(sh - 1, max(0, (sw - len(controls)) // 2), controls)

        stdscr.refresh()

if __name__ == "__main__":
    curses.wrapper(main)