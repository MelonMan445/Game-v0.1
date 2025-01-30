import pygame
import random
import math
from collections import *

# Initialize pygame
pygame.init()

# Screen settings
infoObject = pygame.display.Info()
WIDTH, HEIGHT = infoObject.current_w, infoObject.current_h
HALF_WIDTH = WIDTH // 2
HALF_HEIGHT = HEIGHT // 2
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
clock = pygame.time.Clock()

# Mouse state
mouse_locked = True
pygame.mouse.set_visible(not mouse_locked)
pygame.event.set_grab(mouse_locked)  # Lock mouse to window

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
EDGE_COLOR = (255, 255, 0)
NEON_GREEN = (57, 255, 20)
CROSSHAIR_COLOR = (255, 0, 0)

# Mouse sensitivity
MOUSE_SENSITIVITY = 0.002
VERTICAL_MOUSE_SENSITIVITY = 0.002

# Map settings

def generate_map():
    size = random.randint(15, 30)
    MAP = [[1] * size for _ in range(size)]
    
    # Create open space inside
    for i in range(1, size - 1):
        for j in range(1, size - 1):
            MAP[i][j] = 0
    
    # Place more random walls while ensuring connectivity
    num_walls = random.randint(size, size * 3)  # Increased wall count
    for _ in range(num_walls):
        x, y = random.randint(1, size - 2), random.randint(1, size - 2)
        if MAP[x][y] == 0:
            MAP[x][y] = 1
            if not is_fully_accessible(MAP):
                MAP[x][y] = 0  # Undo if it blocks paths
    
    # Place spawn point (2) in a random open location
    while True:
        sx, sy = random.randint(1, size - 2), random.randint(1, size - 2)
        if MAP[sx][sy] == 0:
            MAP[sx][sy] = 2
            break
    
    return MAP

def is_fully_accessible(MAP):
    """Check if all open spaces (0s) are accessible."""
    size = len(MAP)
    visited = [[False] * size for _ in range(size)]
    
    # Find the first open space
    for i in range(1, size - 1):
        for j in range(1, size - 1):
            if MAP[i][j] == 0:
                start = (i, j)
                break
    
    # BFS to count reachable open spaces
    queue = deque([start])
    visited[start[0]][start[1]] = True
    reachable = 1
    total_open = sum(row.count(0) for row in MAP)
    
    while queue:
        x, y = queue.popleft()
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 1 <= nx < size - 1 and 1 <= ny < size - 1:
                if MAP[nx][ny] == 0 and not visited[nx][ny]:
                    visited[nx][ny] = True
                    queue.append((nx, ny))
                    reachable += 1
    
    return reachable == total_open

MAP = generate_map()

TILE_SIZE = 100

# Mini-map settings
MINI_MAP_SCALE = 6
MINI_TILE_SIZE = TILE_SIZE // MINI_MAP_SCALE
MINI_MAP_X = WIDTH - (len(MAP[0]) * MINI_TILE_SIZE) - 10
MINI_MAP_Y = 10

# Find player spawn point
for y, row in enumerate(MAP):
    for x, cell in enumerate(row):
        if cell == 2:
            player_x = x * TILE_SIZE + TILE_SIZE // 2
            player_y = y * TILE_SIZE + TILE_SIZE // 2
            break

# Player settings
player_angle = 0
player_pitch = 0
FOV = math.pi / 3
RAY_COUNT = 120
MAX_DEPTH = 800
SPEED = 3
PITCH_LIMIT = math.pi / 3

# Paintball mark structure
PaintMark = namedtuple('PaintMark', ['x', 'y', 'z', 'angle'])
paint_marks = []

def toggle_mouse_lock():
    """Toggle mouse lock state."""
    global mouse_locked
    mouse_locked = not mouse_locked
    pygame.mouse.set_visible(not mouse_locked)
    pygame.event.set_grab(mouse_locked)

def is_outer_wall(x, y):
    """Check if a wall tile is on the outer edge."""
    if MAP[y][x] == 1:
        neighbors = [
            MAP[y - 1][x] if y > 0 else 0,  # Top
            MAP[y + 1][x] if y < len(MAP) - 1 else 0,  # Bottom
            MAP[y][x - 1] if x > 0 else 0,  # Left
            MAP[y][x + 1] if x < len(MAP[0]) - 1 else 0,  # Right
        ]
        return 0 in neighbors
    return False

def cast_rays():
    """Casts rays and detects walls with proper edge detection."""
    ray_angle = player_angle - FOV / 2
    delta_angle = FOV / RAY_COUNT
    wall_slices = []

    for ray in range(RAY_COUNT):
        sin_a = math.sin(ray_angle)
        cos_a = math.cos(ray_angle)

        for depth in range(1, MAX_DEPTH):
            ray_x = player_x + depth * cos_a
            ray_y = player_y + depth * sin_a
            tile_x = int(ray_x // TILE_SIZE)
            tile_y = int(ray_y // TILE_SIZE)

            if 0 <= tile_x < len(MAP[0]) and 0 <= tile_y < len(MAP):
                if MAP[tile_y][tile_x] == 1:
                    corrected_depth = depth * math.cos(player_angle - ray_angle)
                    wall_height = min(int(50000 / (corrected_depth + 0.0001)), HEIGHT)
                    pitch_offset = int(player_pitch * HEIGHT)
                    wall_slices.append((ray, wall_height, is_outer_wall(tile_x, tile_y), pitch_offset))
                    break
        ray_angle += delta_angle

    return wall_slices

def cast_ray_from_screen_point(screen_x, screen_y):
    """Cast a ray from the player through a specific screen point."""
    ray_angle = player_angle - FOV / 2 + (screen_x / WIDTH) * FOV
    vertical_angle = player_pitch + (HALF_HEIGHT - screen_y) / HEIGHT

    sin_a = math.sin(ray_angle)
    cos_a = math.cos(ray_angle)
    sin_v = math.sin(vertical_angle)
    cos_v = math.cos(vertical_angle)

    for depth in range(1, MAX_DEPTH):
        ray_x = player_x + depth * cos_a * cos_v
        ray_y = player_y + depth * sin_a * cos_v
        ray_z = depth * sin_v
        
        tile_x = int(ray_x // TILE_SIZE)
        tile_y = int(ray_y // TILE_SIZE)

        if 0 <= tile_x < len(MAP[0]) and 0 <= tile_y < len(MAP):
            if MAP[tile_y][tile_x] == 1:
                return ray_x, ray_y, ray_z, ray_angle
    return None

def shoot_paintball():
    """Handle paintball shooting."""
    hit = cast_ray_from_screen_point(HALF_WIDTH, HALF_HEIGHT)
    if hit:
        x, y, z, angle = hit
        paint_marks.append(PaintMark(x, y, z, angle))

def is_point_visible(x, y):
    """Check if a point is visible by casting a ray to it."""
    dx = x - player_x
    dy = y - player_y
    distance_to_point = math.sqrt(dx*dx + dy*dy)
    
    # Get angle to point
    angle_to_point = math.atan2(dy, dx)
    
    # Cast ray to point
    sin_a = math.sin(angle_to_point)
    cos_a = math.cos(angle_to_point)
    
    for depth in range(1, int(distance_to_point)):
        ray_x = player_x + depth * cos_a
        ray_y = player_y + depth * sin_a
        tile_x = int(ray_x // TILE_SIZE)
        tile_y = int(ray_y // TILE_SIZE)
        
        # Check if we hit a wall before reaching the point
        if 0 <= tile_x < len(MAP[0]) and 0 <= tile_y < len(MAP):
            if MAP[tile_y][tile_x] == 1:
                return False
    return True

def draw_paint_marks(wall_slices):
    """Draw all paint marks in 3D space with proper depth checking."""
    for mark in paint_marks:
        dx = mark.x - player_x
        dy = mark.y - player_y
        
        distance = math.sqrt(dx*dx + dy*dy)
        mark_angle = math.atan2(dy, dx)
        
        angle_diff = mark_angle - player_angle
        while angle_diff > math.pi: angle_diff -= 2 * math.pi
        while angle_diff < -math.pi: angle_diff += 2 * math.pi
        
        # Check if mark is in field of view and visible
        if -FOV/2 <= angle_diff <= FOV/2 and is_point_visible(mark.x, mark.y):
            screen_x = HALF_WIDTH + (angle_diff / FOV) * WIDTH
            wall_height = min(int(50000 / (distance + 0.0001)), HEIGHT)
            horizon = HALF_HEIGHT + int(player_pitch * HEIGHT)
            
            vertical_offset = int(mark.z / distance * HEIGHT)
            screen_y = horizon - vertical_offset
            
            pygame.draw.circle(screen, NEON_GREEN, (int(screen_x), int(screen_y)), 3)

def draw_crosshair():
    """Draw crosshair in the center of the screen."""
    if mouse_locked:
        size = 20
        thickness = 2
        pygame.draw.line(screen, CROSSHAIR_COLOR, (HALF_WIDTH - size, HALF_HEIGHT), 
                        (HALF_WIDTH + size, HALF_HEIGHT), thickness)
        pygame.draw.line(screen, CROSSHAIR_COLOR, (HALF_WIDTH, HALF_HEIGHT - size), 
                        (HALF_WIDTH, HALF_HEIGHT + size), thickness)
        
        pygame.draw.circle(screen, NEON_GREEN, (HALF_WIDTH, HALF_HEIGHT), 2)

def draw_3d(wall_slices):
    """Draws walls with proper vertical look implementation."""
    screen.fill(BLACK)
    horizon = HALF_HEIGHT + int(player_pitch * HEIGHT)
    pygame.draw.rect(screen, DARK_GRAY, (0, horizon, WIDTH, HEIGHT - horizon))
    pygame.draw.rect(screen, GRAY, (0, 0, WIDTH, horizon))

    for ray, wall_height, is_edge, pitch_offset in wall_slices:
        wall_top = horizon - wall_height // 2
        wall_bottom = horizon + wall_height // 2
        x_pos = ray * (WIDTH // RAY_COUNT)

        pygame.draw.rect(screen, WHITE, (x_pos, wall_top, WIDTH // RAY_COUNT + 1, wall_height))
        
        if is_edge:
            pygame.draw.rect(screen, EDGE_COLOR, (x_pos, wall_top, WIDTH // RAY_COUNT + 1, 2))
            pygame.draw.rect(screen, EDGE_COLOR, (x_pos, wall_bottom - 2, WIDTH // RAY_COUNT + 1, 2))
    
    draw_paint_marks(wall_slices)
    draw_crosshair()

def draw_minimap():
    """Draws a small top-down view of the map in the top-right corner."""
    for y, row in enumerate(MAP):
        for x, cell in enumerate(row):
            color = WHITE if cell == 1 else DARK_GRAY
            pygame.draw.rect(screen, color, (MINI_MAP_X + x * MINI_TILE_SIZE, 
                                          MINI_MAP_Y + y * MINI_TILE_SIZE, 
                                          MINI_TILE_SIZE, MINI_TILE_SIZE))

    mini_player_x = MINI_MAP_X + (player_x / TILE_SIZE) * MINI_TILE_SIZE
    mini_player_y = MINI_MAP_Y + (player_y / TILE_SIZE) * MINI_TILE_SIZE
    pygame.draw.circle(screen, (255, 0, 0), (int(mini_player_x), int(mini_player_y)), 3)

def handle_mouse_look():
    """Handles mouse looking."""
    global player_angle, player_pitch
    
    if mouse_locked:
        # Get relative mouse movement
        mouse_x, mouse_y = pygame.mouse.get_rel()
        
        # Horizontal mouse movement affects player angle
        player_angle += mouse_x * MOUSE_SENSITIVITY
        
        # Vertical mouse movement affects pitch
        player_pitch -= mouse_y * VERTICAL_MOUSE_SENSITIVITY
        
        # Clamp pitch to prevent over-rotation
        player_pitch = max(-PITCH_LIMIT, min(PITCH_LIMIT, player_pitch))
    else:
        pygame.mouse.get_rel()  # Clear mouse movement when unlocked

def move_player():
    """Handles player movement."""
    global player_x, player_y
    
    if not mouse_locked:
        return
        
    keys = pygame.key.get_pressed()

    # Calculate forward and right vectors based on player angle
    forward_x = math.cos(player_angle)
    forward_y = math.sin(player_angle)
    right_x = math.cos(player_angle + math.pi/2)
    right_y = math.sin(player_angle + math.pi/2)

    new_x, new_y = player_x, player_y

    if keys[pygame.K_w]:  # Forward
        new_x += SPEED * forward_x
        new_y += SPEED * forward_y

    if keys[pygame.K_s]:  # Backward
        new_x -= SPEED * forward_x
        new_y -= SPEED * forward_y

    if keys[pygame.K_a]:  # Strafe left
        new_x -= SPEED * right_x
        new_y -= SPEED * right_y

    if keys[pygame.K_d]:  # Strafe right
        new_x += SPEED * right_x
        new_y += SPEED * right_y

    # Check for collisions
    tile_x, tile_y = int(new_x // TILE_SIZE), int(new_y // TILE_SIZE)
    if MAP[tile_y][tile_x] == 0 or MAP[tile_y][tile_x] == 2:
        player_x, player_y = new_x, new_y

# Main game loop
running = True
pygame.mouse.get_rel()  # Clear initial mouse movement
while running:
    clock.tick(60)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                toggle_mouse_lock()
            elif event.key == pygame.K_SPACE and mouse_locked:
                shoot_paintball()
        elif event.type == pygame.MOUSEBUTTONDOWN and not mouse_locked:
            toggle_mouse_lock()

    handle_mouse_look()
    move_player()
    wall_slices = cast_rays()
    draw_3d(wall_slices)
    draw_minimap()
    pygame.display.flip()

pygame.quit()