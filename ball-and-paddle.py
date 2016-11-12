#!/usr/bin/env python3

# Copyright (c) 2016 Akuli
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""A crazy ball and paddle game that will blow your mind.

Keys:

W, arrow up, space, Enter   Start the game
A, arrow left               Move the paddle left
D, arrow right              Move the paddle right
H                           Show high scores
F1                          Show this help message
F2                          Start a new game
Q                           Quit
"""

from __future__ import division, print_function, unicode_literals

import contextlib
import io
import math
import os
import random
import shutil
import sys
import time

import easygui
import pygame

# We can't use an assertion here because -O and -OO disable assertions.
if __doc__ is None:
    sys.exit("%s: don't use Python's -OO switch" % sys.argv[0])

if sys.version_info < (3, 3):
    _NoFile = IOError
else:
    _NoFile = FileNotFoundError


def sin(angle):
    """Trigonometric sin with degrees."""
    return math.sin(math.radians(angle))


def cos(angle):
    """Trigonometric cosin with degrees."""
    return math.cos(math.radians(angle))


def time_to_hide(starttime):
    """A helper function for blinking things."""
    return (time.time() - starttime) % 1 < 0.5


class Ball:

    def __init__(self, paddle, ball_list):
        """Initialize the ball.

        Sometimes a new ball is added to the ball list.
        """
        self.paddle = paddle
        self.ball_list = ball_list
        self.radius = 10
        self.x = 400            # Centered.
        self.y = 565            # On the paddle.
        self.angle = 180        # Moving up.
        self.crazy_speed = False
        self.crazy_angle = False
        self._create_time = time.time()
        self._blinking = False
        self.on_the_paddle = False

    def _do_random(self):
        """Change the ball's settings randomly."""
        # Decide how crazy the ball will be.
        self.crazy_angle = random.choice([True, False])
        self.crazy_speed = random.choice([True, False])
        self.radius = random.choice([10, 50])
        self._blinking = random.choice([True, False, False])

        if random.choice([True, False]):
            ball = Ball(paddle=self.paddle, ball_list=self.ball_list)
            self.ball_list.append(ball)

    def draw(self, surface):
        """Draw the ball on the surface."""
        if self._blinking and time_to_hide(self._create_time):
            # Time to hide.
            return

        # White circle.
        pygame.draw.circle(surface, (255, 255, 255),
                           [int(self.x), int(self.y)], self.radius)
        # Black border.
        pygame.draw.circle(surface, (0, 0, 0),
                           [int(self.x), int(self.y)], self.radius, 1)

    def move(self):
        """Move the ball and change its settings."""
        if not self.on_the_paddle:
            # Change the angle.
            if self.crazy_angle:
                self.angle += random.randint(-20, 20)
            else:
                self.angle += random.randint(-2, 2)

            # Move the ball.
            if self.crazy_speed:
                the_range = (-10, 40)
            else:
                the_range = (10, 15)
            self.x += sin(self.angle) * random.randint(*the_range)
            self.y += cos(self.angle) * random.randint(*the_range)

    def _on_hit(self, side, paddlespot=None):
        """This is ran when the ball hits to the wall or the paddle.

        The side can be w, a, s or d. The paddlespot is needed only when
        the ball hits the paddle, and it should be the distance between
        the ball's center and the paddle's center.
        """
        if side == 'a':     # Left wall.
            # Bounce from the wall.
            self.angle = -self.angle

            # Make sure that 0 <= angle < 360.
            self.angle %= 360

            # Make sure that the ball is not going into a wall.
            if 180 <= self.angle <= 270:
                self.angle = 177
            elif 270 <= self.angle < 360 or self.angle == 0:
                self.angle = 3

            # Move the ball so that it touches the wall.
            self.x = self.radius

        if side == 'd':     # Right wall.
            self.angle = -self.angle
            self.angle %= 360
            if self.angle <= 90:
                self.angle = 357
            elif 90 <= self.angle <= 180:
                self.angle = 183
            self.x = 800 - self.radius

        if side == 'w':     # Top wall.
            self.angle = 180 - self.angle
            self.angle %= 360
            if 90 <= self.angle <= 180:
                self.angle = 87
            elif 180 <= self.angle <= 270:
                self.angle = 273
            self.y = self.radius

        if side == 's':     # Paddle.
            self.angle += random.randint(-10, 10)
            self.angle = 180 - self.angle
            self.angle -= paddlespot  # Ball goes off to a side.
            self.angle %= 360
            self._do_random()

            # Ball is moved after possibly changing the radius.
            self.y = 575 - self.radius

    def hitcheck(self):
        """Check if the ball hits the paddle or an wall and handle it.

        Call self._on_hit when needed.
        """
        if self.x < self.radius:  # Left wall.
            self._on_hit('a')
        if self.x > 800 - self.radius:  # Right wall.
            self._on_hit('d')
        if self.y < self.radius:  # Top wall.
            self._on_hit('w')
        if self.y > 575 - self.radius:  # Paddle.
            # Distance from the paddle's center to the ball's center.
            paddlespot = self.x - self.paddle.x

            # Width of an imaginary big paddle to make sure that it's
            # easy to bump the ball with the edge of the paddle.
            bigpaddle = self.radius * 2 + 100

            if -bigpaddle/2 < paddlespot < bigpaddle/2:
                # Now we are sure that the ball hits the paddle.
                self.paddle.do_random()
                self._on_hit('s', paddlespot)


class Paddle:

    def __init__(self):
        """Initialize the paddle."""
        self.x = 400        # Centered.
        self.direction = 0  # -1 is left, 1 is right, 0 is not moving.
        self._flip = False  # Turn right to left and left to right.
        self._create_time = time.time()
        self._blinking = False

    def do_random(self):
        """Decide the paddle's direction."""
        self._flip = random.choice([True, False])
        # The paddle is unlikely to blink, but it happens sometimes.
        self._blinking = random.random() < 0.2

    def draw(self, surface):
        """Draw the paddle on surface."""
        if self._blinking and time_to_hide(self._create_time):
            # Time to hide.
            return

        pygame.draw.rect(surface, (0, 255, 0), [self.x-50, 575, 100, 12])

    def move(self):
        """Move the paddle."""
        if self._flip:
            self.x -= self.direction * 15
        else:
            self.x += self.direction * 15

        # The paddle must stay on the screen.
        if self.x < 50:
            self.x = 50
        if self.x > 750:
            self.x = 750


def format_time(seconds):
    hundredths = int(seconds * 100)
    seconds, hundredths = hundredths // 100, hundredths % 100
    minutes, seconds = seconds // 60, seconds % 60
    return '%02d:%02d:%02d' % (minutes, seconds, hundredths)


class Clock:

    def __init__(self, frequency):
        """Initialize the clock."""
        self.time = 0
        self._font = pygame.font.Font(None, 40)  # 40px oletusfontti.
        self._running = False
        self._frequency = frequency
        self._clock = pygame.time.Clock()

    def start(self):
        """The ball is launched."""
        if self._running:
            # The player pressed a launching key but the ball is
            # already moving.
            return
        self._running = True
        self.time = 0

    def stop(self):
        """All balls have went below the paddle."""
        self._running = False

    def wait(self):
        """Wait until the previous wait happened a long enough time ago.

        Add 1/frequency to self.time when it's been at least 1/frequency
        seconds since the previous wait.
        """
        if self._running:
            self.time += 1 / self._frequency
        self._clock.tick(self._frequency)

    def draw(self, surface):
        """Draw a clock to the upper left corner of surface."""
        text = self._font.render(format_time(self.time), True, (255, 255, 255))
        surface.blit(text, (0, 0))


@contextlib.contextmanager
def backup(orig):
    """Back up a file temporarily.

    The file must exist.
    """
    assert os.path.isfile(orig), "%s isn't file, it can't be backed up" % orig

    beginning, end = os.path.splitext(orig)
    while os.path.exists(beginning + end):
        beginning += '.bak'
    copy = beginning + end

    with io.open(orig, 'r') as src:
        with io.open(copy, 'w') as dst:
            shutil.copyfileobj(src, dst)

    try:
        yield
    except Exception:
        with io.open(copy, 'r') as src:
            with io.open(orig, 'w') as dst:
                shutil.copyfileobj(src, dst)

    # This is not in the finally part because this isn't meant to be ran
    # if restoring from the backup fails.
    os.remove(copy)


class HighScoreCounter:

    def __init__(self, filename):
        self._filename = filename
        self._scores = []   # 2-tuples of times in seconds and names.

    def _fix(self):
        self._scores.sort()       # Worst (shortest) time first.
        self._scores.reverse()    # Best (longest) time first.
        del self._scores[3:]      # Remove everything except 3 high scores.

    def read(self):
        self._scores[:] = []
        try:
            with io.open(self._filename, 'r') as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue
                    seconds, name = line.split('\t', 1)
                    self._scores.append((float(seconds), name))
        except _NoFile:
            # No high scores yet, let's create an empty file so that
            # backing up the scores for writing will succeed.
            with io.open(self._filename, 'w'):
                pass
        self._fix()

    def _write(self):
        with backup(self._filename):
            with io.open(self._filename, 'w') as f:
                for seconds, name in self._scores:
                    print('%.4f\t%s' % (seconds, name), file=f)

    def add_result(self, seconds):
        """Add a new high score."""
        if len(self._scores) == 3:
            # There are already three high scores. Maybe we don't need
            # to add this score at all?
            if seconds < self._scores[-1][0]:
                # The time is shorter than the worst time so there's no
                # need to add this.
                return

        name = easygui.enterbox("Enter your name:", title="High score")
        if name is None:
            # The user cancelled.
            return

        self._scores.append((seconds, name.strip() or "???"))
        self._fix()
        self._write()
        self.show_scores()

    def show_scores(self):
        if self._scores:
            text = '\n'.join(format_time(seconds) + '\t' + name
                             for seconds, name in self._scores)
        else:
            text = "There are no high scores yet."
        easygui.msgbox(text, title="High scores")


def main():
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode([800, 600])
    pygame.display.set_caption("Ball and paddle")

    clock = Clock(60)
    scorecounter = HighScoreCounter('scores.txt')
    scorecounter.read()

    while True:
        paddle = Paddle()
        balls = []
        first_ball = Ball(paddle=paddle, ball_list=balls)
        first_ball.on_the_paddle = True
        balls.append(first_ball)

        while balls:
            # Limit the speed of the game and update the clock.
            clock.wait()

            paddle.move()
            for ball in balls:
                ball.move()

            if balls[0].on_the_paddle:
                # We need to get the ball centered on the paddle.
                balls[0].x = paddle.x

            for ball in balls[:]:
                if ball.y > 600+ball.radius:
                    balls.remove(ball)

            # Draw everything.
            screen.fill(0)
            clock.draw(screen)
            paddle.draw(screen)
            for ball in balls:
                ball.draw(screen)
            pygame.display.flip()

            # Check for events and stop game when needed.
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key in {pygame.K_LEFT, pygame.K_a}:
                        paddle.direction = -1
                    if event.key in {pygame.K_RIGHT, pygame.K_d}:
                        paddle.direction = 1
                    if event.key in {pygame.K_SPACE, pygame.K_RETURN,
                                     pygame.K_UP, pygame.K_w}:
                        # Launch.
                        if balls[0].on_the_paddle:
                            clock.start()
                            balls[0].on_the_paddle = False
                    if event.key == pygame.K_h:
                        scorecounter.show_scores()
                    if event.key == pygame.K_F1:
                        easygui.codebox(title="Ball and paddle", text=__doc__)
                    if event.key == pygame.K_F2:
                        # Start a new game by quitting this loop.
                        balls[:] = []
                    if event.key == pygame.K_q:
                        pygame.quit()
                        sys.exit()

                if event.type == pygame.KEYUP:
                    if event.key in {pygame.K_LEFT, pygame.K_a}:
                        if paddle.direction == -1:
                            paddle.direction = 0
                    if event.key in {pygame.K_RIGHT, pygame.K_d}:
                        if paddle.direction == 1:
                            paddle.direction = 0

                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            for ball in balls:
                ball.hitcheck()

        clock.stop()
        scorecounter.add_result(clock.time)


if __name__ == '__main__':
    main()
