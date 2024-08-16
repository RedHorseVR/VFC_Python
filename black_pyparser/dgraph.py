import pygame
import math
import random

pygame.init()
WIDTH, HEIGHT = 1000, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dynamic Graph Network")
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 100, 0)
YELLOW = (255, 255, 0)
NUM_NODES = 20
NODE_RADIUS = 25
CONNECTION_PROBABILITY = 0.30
IDEAL_DISTANCE = NODE_RADIUS * NUM_NODES
MIN_VELOCITY = 0.1
font = pygame.font.Font(None, 24)


class Node:

    def __init__(self, x, y, label):

        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.label = label

    def update(self):

        if abs(self.vx) < MIN_VELOCITY:

            self.vx = 0

        if abs(self.vy) < MIN_VELOCITY:

            self.vy = 0

        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.9
        self.vy *= 0.9
        self.x = max(NODE_RADIUS, min(WIDTH - NODE_RADIUS, self.x))
        self.y = max(NODE_RADIUS, min(HEIGHT - NODE_RADIUS, self.y))

    def draw(self, screen):

        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), NODE_RADIUS)
        label_surface = font.render(self.label, True, WHITE)
        label_rect = label_surface.get_rect(center=(int(self.x), int(self.y)))
        screen.blit(label_surface, label_rect)


def draw_arrow(screen, start, end, color, size=10):

    pygame.draw.line(screen, color, start, end, 2)
    angle = math.atan2(start[1] - end[1], start[0] - end[0])
    end_x = end[0] + size * math.cos(angle)
    end_y = end[1] + size * math.sin(angle)
    pygame.draw.line(
        screen,
        color,
        end,
        (
            end_x + size * math.cos(angle + math.pi / 6),
            end_y + size * math.sin(angle + math.pi / 6),
        ),
        2,
    )
    pygame.draw.line(
        screen,
        color,
        end,
        (
            end_x + size * math.cos(angle - math.pi / 6),
            end_y + size * math.sin(angle - math.pi / 6),
        ),
        2,
    )


def generate_graph():

    global nodes, connections
    nodes = [
        Node(
            random.randint(NODE_RADIUS, WIDTH - NODE_RADIUS),
            random.randint(NODE_RADIUS, HEIGHT - NODE_RADIUS),
            chr(65 + i),
        )
        for i in range(NUM_NODES)
    ]
    connections = []
    for i in range(NUM_NODES):
        for j in range(i + 1, NUM_NODES):
            if random.random() < CONNECTION_PROBABILITY:

                connections.append((i, j))
                connections.append((j, i))


def save_cyphers():

    with open("cyphers.txt", "w") as f:

        edge_labels = []
        for i, node in enumerate(nodes):
            for conn in connections:
                if conn[0] == i:

                    start_node = nodes[conn[0]]
                    end_node = nodes[conn[1]]
                    edge_labels.append(f"{start_node.label}2{end_node.label}")
                    f.write(f"{start_node.label} -> {end_node.label}\n")


def main():

    global dragging, drag_node
    running = True
    dragging = False
    drag_node = None
    clock = pygame.time.Clock()
    generate_graph()
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:

                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:

                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    for node in nodes:
                        if math.hypot(node.x - mouse_x, node.y - mouse_y) < NODE_RADIUS:

                            dragging = True
                            drag_node = node
                            break

                    if 10 <= mouse_x <= 140 and 10 <= mouse_y <= 50:

                        generate_graph()
                    elif 170 <= mouse_x <= 300 and 10 <= mouse_y <= 50:
                        save_cyphers()

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:

                    dragging = False
                    drag_node = None

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:

                    generate_graph()
                elif event.key == pygame.K_s:
                    save_cyphers()

        if dragging and drag_node:

            mouse_x, mouse_y = pygame.mouse.get_pos()
            drag_node.x = mouse_x
            drag_node.y = mouse_y
            drag_node.vx = 0
            drag_node.vy = 0

        for i, node in enumerate(nodes):
            dx = WIDTH / 2 - node.x
            dy = HEIGHT / 2 - node.y
            distance = math.hypot(dx, dy)
            node.vx += dx / distance * 0.1
            node.vy += dy / distance * 0.1
            for other in nodes[i + 1 :]:
                dx = other.x - node.x
                dy = other.y - node.y
                distance = math.hypot(dx, dy)
                if distance < IDEAL_DISTANCE:

                    force = (1 - distance / IDEAL_DISTANCE) ** 2 * 0.5
                    node.vx -= dx / distance * force
                    node.vy -= dy / distance * force
                    other.vx += dx / distance * force
                    other.vy += dy / distance * force

        for conn in connections:
            node1, node2 = nodes[conn[0]], nodes[conn[1]]
            dx = node2.x - node1.x
            dy = node2.y - node1.y
            distance = math.hypot(dx, dy)
            force = (distance - IDEAL_DISTANCE / 2) * 0.001
            node1.vx += dx / distance * force
            node1.vy += dy / distance * force
            node2.vx -= dx / distance * force
            node2.vy -= dy / distance * force

        for node in nodes:
            node.update()

        screen.fill(BLACK)
        pygame.draw.rect(screen, WHITE, (10, 10, 150, 40))
        pygame.draw.rect(screen, WHITE, (170, 10, 160, 40))
        regenerate_text = font.render("  Regenerate - 'R'  ", True, BLACK)
        save_cyphers_text = font.render("  Save Cyphers - 'S'  ", True, BLACK)
        screen.blit(regenerate_text, (10, 20))
        screen.blit(save_cyphers_text, (170, 20))
        edge_labels = {}
        for conn in connections:
            start_node, end_node = nodes[conn[0]], nodes[conn[1]]
            start = (int(start_node.x), int(start_node.y))
            end = (int(end_node.x), int(end_node.y))
            dx, dy = end[0] - start[0], end[1] - start[1]
            length = math.hypot(dx, dy)
            if length == 0:

                continue

            dx, dy = dx / length, dy / length
            start = (int(start[0] + dx * NODE_RADIUS), int(start[1] + dy * NODE_RADIUS))
            end = (int(end[0] - dx * NODE_RADIUS), int(end[1] - dy * NODE_RADIUS))
            draw_arrow(screen, start, end, WHITE)
            mid_x = (start[0] + end[0]) // 2
            mid_y = (start[1] + end[1]) // 2
            edge_key = tuple(sorted([start_node.label, end_node.label]))
            if edge_key not in edge_labels:

                edge_labels[edge_key] = set()

            edge_labels[edge_key].add(f"{start_node.label}2{end_node.label}")

        for edge_key, labels in edge_labels.items():
            label_text = ",".join(sorted(labels))
            label_surface = font.render(label_text, True, YELLOW)
            mid_x = sum(nodes[ord(node) - 65].x for node in edge_key) / 2
            mid_y = sum(nodes[ord(node) - 65].y for node in edge_key) / 2
            label_rect = label_surface.get_rect(center=(mid_x, mid_y))
            screen.blit(label_surface, label_rect)

        for node in nodes:
            node.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":

    main()

#  Export  Date: 05:21:53 PM - 08:Aug:2024.
