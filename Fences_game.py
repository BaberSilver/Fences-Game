import math
import pygame
import threading
from collections import deque


empty = 0
blue  = 1
red   = 2


C_BG         = (245, 240, 230)
C_DOT        = ( 40,  40,  40)
C_EDGE_empty = (200, 195, 185)
C_blue       = ( 30, 100, 220)
C_red        = (210,  40,  40)
C_HOVER      = (160, 200, 255)
C_TEXT       = ( 30,  30,  30)
C_WIN_blue   = ( 20,  80, 180)
C_WIN_red    = (180,  20,  20)
C_PANEL      = (255, 255, 255)
C_BORDER     = (180, 175, 165)


MARGIN       = 60
DOT_R        = 7
EDGE_W       = 5
EDGE_HIT     = 12
PANEL_H      = 110


class State:
    def __init__(self, N):
        self.N = N
        self.h = [[empty] * (N - 1) for _ in range(N)]
        self.v = [[empty] * N       for _ in range(N - 1)]
        self.memo_key = None

    def get_key(self):
        if self.memo_key is None:
            self.memo_key = (
                tuple(tuple(row) for row in self.h),
                tuple(tuple(row) for row in self.v)
            )
        return self.memo_key

    def copy(self):
        s = State(self.N)
        s.h = [row[:] for row in self.h]
        s.v = [row[:] for row in self.v]
        return s

    def moves(self):
        m = []
        for r in range(self.N):
            for c in range(self.N - 1):
                if self.h[r][c] == empty: m.append(('h', r, c))
        for r in range(self.N - 1):
            for c in range(self.N):
                if self.v[r][c] == empty: m.append(('v', r, c))
        return m

    def play(self, move, player):
        s = self.copy()
        k, r, c = move
        if k == 'h': s.h[r][c] = player
        else:        s.v[r][c] = player
        return s

    def win(self, p):
        N   = self.N
        vis = [[False] * N for _ in range(N)]
        q   = deque()
        if p == blue:
            for r in range(N): q.append((r, 0)); vis[r][0] = True
            goal = lambda r, c: c == N - 1
        else:
            for c in range(N): q.append((0, c)); vis[0][c] = True
            goal = lambda r, c: r == N - 1
        while q:
            r, c = q.popleft()
            if goal(r, c): return True
            if c+1 < N and self.h[r][c]   == p and not vis[r][c+1]:   vis[r][c+1]   = True; q.append((r, c+1))
            if c-1 >= 0 and self.h[r][c-1] == p and not vis[r][c-1]:   vis[r][c-1]   = True; q.append((r, c-1))
            if r+1 < N and self.v[r][c]   == p and not vis[r+1][c]:   vis[r+1][c]   = True; q.append((r+1, c))
            if r-1 >= 0 and self.v[r-1][c] == p and not vis[r-1][c]:   vis[r-1][c]   = True; q.append((r-1, c))
        return False


transposition_table = {}

def evaluate(state):
    key = state.get_key()
    if key in transposition_table: return transposition_table[key]

    if state.win(red):  return  1000
    if state.win(blue): return -1000

    def bfs_dist(player):
        N    = state.N
        q    = deque()
        dist = [[-1] * N for _ in range(N)]
        if player == blue:
            for r in range(N): q.append((r, 0)); dist[r][0] = 0
            goal = lambda r, c: c == N - 1
        else:
            for c in range(N): q.append((0, c)); dist[0][c] = 0
            goal = lambda r, c: r == N - 1
        while q:
            r, c = q.popleft()
            if goal(r, c): return dist[r][c]
            for dr, dc, k, kr, kc in [(0,1,'h',r,c),(0,-1,'h',r,c-1),(1,0,'v',r,c),(-1,0,'v',r-1,c)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < N and 0 <= nc < N and dist[nr][nc] == -1:
                    val = state.h[kr][kc] if k == 'h' else state.v[kr][kc]
                    if val != (red if player == blue else blue):
                        dist[nr][nc] = dist[r][c] + (1 if val == empty else 0)
                        if val == empty: q.append((nr, nc))
                        else:            q.appendleft((nr, nc))
        return 100

    score = bfs_dist(blue) - bfs_dist(red)
    transposition_table[key] = score
    return score


def minimax(state, depth, alpha, beta, maximizing):
    if depth == 0 or state.win(blue) or state.win(red):
        return evaluate(state), None

    moves = state.moves()
    moves.sort(key=lambda m: abs(m[1] - state.N / 2) + abs(m[2] - state.N / 2))

    best_move = None
    if maximizing:
        val = -math.inf
        for m in moves:
            res, _ = minimax(state.play(m, red), depth-1, alpha, beta, False)
            if res > val: val, best_move = res, m
            alpha = max(alpha, val)
            if beta <= alpha: break
        return val, best_move
    else:
        val = math.inf
        for m in moves:
            res, _ = minimax(state.play(m, blue), depth-1, alpha, beta, True)
            if res < val: val, best_move = res, m
            beta = min(beta, val)
            if beta <= alpha: break
        return val, best_move


class FencesGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Fences")

        self.state      = None
        self.N          = None
        self.depth      = None
        self.cell       = None         
        self.win_w      = None
        self.win_h      = None
        self.screen     = None
        self.font_lg    = pygame.font.SysFont("Segoe UI", 22, bold=True)
        self.font_md    = pygame.font.SysFont("Segoe UI", 18)
        self.font_sm    = pygame.font.SysFont("Segoe UI", 14)
        self.turn       = blue
        self.hover_move = None         
        self.status     = ""
        self.game_over  = False
        self.cpu_busy   = False
        self.cpu_result = None        

        self.show_menu()


    def show_menu(self):
        menu_w, menu_h = 480, 420
        screen = pygame.display.set_mode((menu_w, menu_h))
        clock  = pygame.time.Clock()

        sizes  = [("Small  –  3 × 3",  3),
                  ("Medium –  5 × 5",  5),
                  ("Large  – 10 × 10", 10)]
        diffs  = [("Easy",  "easy"),
                  ("Hard",  "hard")]

        sel_size = 0
        sel_diff = 0

        btn_w, btn_h = 300, 44
        bx = (menu_w - btn_w) // 2

        def draw():
            screen.fill(C_BG)

            t = self.font_lg.render("FENCES", True, C_TEXT)
            screen.blit(t, t.get_rect(center=(menu_w//2, 42)))

            t2 = self.font_sm.render("blue (you) = Left → Right      red (cpu) = Top → Bottom", True, (100,100,100))
            screen.blit(t2, t2.get_rect(center=(menu_w//2, 70)))


            t3 = self.font_md.render("Board Size", True, C_TEXT)
            screen.blit(t3, (bx, 100))
            for i, (label, _) in enumerate(sizes):
                y   = 128 + i * 54
                col = C_blue if i == sel_size else C_BORDER
                pygame.draw.rect(screen, col, (bx, y, btn_w, btn_h), border_radius=8)
                pygame.draw.rect(screen, C_TEXT, (bx, y, btn_w, btn_h), 2, border_radius=8)
                tl  = self.font_md.render(label, True, C_PANEL if i == sel_size else C_TEXT)
                screen.blit(tl, tl.get_rect(center=(bx + btn_w//2, y + btn_h//2)))


            t4 = self.font_md.render("Difficulty", True, C_TEXT)
            screen.blit(t4, (bx, 298))
            for i, (label, _) in enumerate(diffs):
                y   = 326 + i * 0
                x   = bx + i * (btn_w // 2 + 6)
                w   = btn_w // 2 - 3
                col = C_red if i == sel_diff else C_BORDER
                pygame.draw.rect(screen, col, (x, 326, w, btn_h), border_radius=8)
                pygame.draw.rect(screen, C_TEXT, (x, 326, w, btn_h), 2, border_radius=8)
                tl  = self.font_md.render(label, True, C_PANEL if i == sel_diff else C_TEXT)
                screen.blit(tl, tl.get_rect(center=(x + w//2, 326 + btn_h//2)))


            pygame.draw.rect(screen, (50, 160, 80), (bx, 386, btn_w, btn_h), border_radius=8)
            pt = self.font_lg.render("▶  Play", True, C_PANEL)
            screen.blit(pt, pt.get_rect(center=(bx + btn_w//2, 386 + btn_h//2)))

            pygame.display.flip()

        running = True
        while running:
            draw()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); raise SystemExit
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = ev.pos

                    for i in range(len(sizes)):
                        y = 128 + i * 54
                        if bx <= mx <= bx + btn_w and y <= my <= y + btn_h:
                            sel_size = i

                    for i in range(len(diffs)):
                        x = bx + i * (btn_w // 2 + 6)
                        w = btn_w // 2 - 3
                        if x <= mx <= x + w and 326 <= my <= 326 + btn_h:
                            sel_diff = i

                    if bx <= mx <= bx + btn_w and 386 <= my <= 386 + btn_h:
                        running = False
            clock.tick(60)

        N          = sizes[sel_size][1]
        difficulty = diffs[sel_diff][1]
        self.start_game(N, difficulty)


    def start_game(self, N, difficulty):
        global transposition_table
        transposition_table = {}

        self.N     = N
        self.state = State(N)
        self.depth = 6 if N == 3 else 4 if N == 5 else 2
        self.turn  = blue
        self.game_over  = False
        self.cpu_busy   = False
        self.cpu_result = None
        self.hover_move = None
        self.status = "Your turn  –  click an edge to place a blue fence"


        max_board = 620
        self.cell  = max_board // (N - 1) if N > 1 else max_board
        board_px   = self.cell * (N - 1)
        self.win_w = board_px + 2 * MARGIN
        self.win_h = board_px + 2 * MARGIN + PANEL_H
        self.screen = pygame.display.set_mode((self.win_w, self.win_h))
        self.run()


    def dot_xy(self, r, c):
        x = MARGIN + c * self.cell
        y = MARGIN + r * self.cell
        return x, y


    def edge_at(self, mx, my):
        N = self.N
        best_d, best_mv = EDGE_HIT + 1, None

        for r in range(N):
            for c in range(N - 1):
                x1, y1 = self.dot_xy(r, c)
                x2, _  = self.dot_xy(r, c + 1)
                cx, cy = (x1 + x2) // 2, y1
                d = math.hypot(mx - cx, my - cy)
                if d < best_d and abs(mx - cx) < self.cell // 2 - 2 and abs(my - cy) < EDGE_HIT:
                    best_d, best_mv = d, ('h', r, c)

        for r in range(N - 1):
            for c in range(N):
                x1, y1 = self.dot_xy(r, c)
                _,  y2 = self.dot_xy(r + 1, c)
                cx, cy = x1, (y1 + y2) // 2
                d = math.hypot(mx - cx, my - cy)
                if d < best_d and abs(my - cy) < self.cell // 2 - 2 and abs(mx - cx) < EDGE_HIT:
                    best_d, best_mv = d, ('v', r, c)
        return best_mv


    def draw(self):
        self.screen.fill(C_BG)
        N  = self.N
        st = self.state


        lbl_blue = self.font_sm.render("◄ blue: Left → Right ►", True, C_blue)
        lbl_red  = self.font_sm.render("▲  red: Top → Bottom  ▼", True, C_red)
        self.screen.blit(lbl_blue, lbl_blue.get_rect(center=(self.win_w // 2, MARGIN // 2)))
        self.screen.blit(lbl_red,  lbl_red.get_rect(center=(self.win_w // 2, MARGIN * 3 // 4)))


        for r in range(N):
            for c in range(N - 1):
                x1, y1 = self.dot_xy(r, c)
                x2, y2 = self.dot_xy(r, c + 1)
                pygame.draw.line(self.screen, C_EDGE_empty, (x1, y1), (x2, y2), 2)
        for r in range(N - 1):
            for c in range(N):
                x1, y1 = self.dot_xy(r, c)
                x2, y2 = self.dot_xy(r + 1, c)
                pygame.draw.line(self.screen, C_EDGE_empty, (x1, y1), (x2, y2), 2)


        if self.hover_move and not self.game_over and self.turn == blue:
            k, r, c = self.hover_move
            if k == 'h' and st.h[r][c] == empty:
                x1, y1 = self.dot_xy(r, c)
                x2, y2 = self.dot_xy(r, c + 1)
                pygame.draw.line(self.screen, C_HOVER, (x1, y1), (x2, y2), EDGE_W + 2)
            elif k == 'v' and st.v[r][c] == empty:
                x1, y1 = self.dot_xy(r, c)
                x2, y2 = self.dot_xy(r + 1, c)
                pygame.draw.line(self.screen, C_HOVER, (x1, y1), (x2, y2), EDGE_W + 2)


        for r in range(N):
            for c in range(N - 1):
                val = st.h[r][c]
                if val != empty:
                    x1, y1 = self.dot_xy(r, c)
                    x2, y2 = self.dot_xy(r, c + 1)
                    col = C_blue if val == blue else C_red
                    pygame.draw.line(self.screen, col, (x1, y1), (x2, y2), EDGE_W)
        for r in range(N - 1):
            for c in range(N):
                val = st.v[r][c]
                if val != empty:
                    x1, y1 = self.dot_xy(r, c)
                    x2, y2 = self.dot_xy(r + 1, c)
                    col = C_blue if val == blue else C_red
                    pygame.draw.line(self.screen, col, (x1, y1), (x2, y2), EDGE_W)


        for r in range(N):
            for c in range(N):
                x, y = self.dot_xy(r, c)
                pygame.draw.circle(self.screen, C_DOT, (x, y), DOT_R)


        for i in range(N):

            x, _ = self.dot_xy(0, i)
            t = self.font_sm.render(str(i), True, (120, 120, 120))
            self.screen.blit(t, t.get_rect(center=(x, MARGIN - 18)))

            _, y = self.dot_xy(i, 0)
            t = self.font_sm.render(str(i), True, (120, 120, 120))
            self.screen.blit(t, t.get_rect(center=(MARGIN - 18, y)))


        panel_y = self.win_h - PANEL_H
        pygame.draw.rect(self.screen, C_PANEL, (0, panel_y, self.win_w, PANEL_H))
        pygame.draw.line(self.screen, C_BORDER, (0, panel_y), (self.win_w, panel_y), 2)


        if not self.game_over:
            whose   = "YOUR TURN  (blue)" if self.turn == blue else "CPU THINKING…  (red)"
            col_ind = C_blue if self.turn == blue else C_red
            pygame.draw.circle(self.screen, col_ind, (30, panel_y + 22), 10)
            t = self.font_md.render(whose, True, col_ind)
            self.screen.blit(t, (50, panel_y + 13))
        else:

            if self.state.win(blue):
                msg, col = "blue PLAYER WINS!", C_WIN_blue
            elif self.state.win(red):
                msg, col = "red PLAYER WINS!", C_WIN_red
            else:
                msg, col = "DRAW!", C_TEXT
            t = self.font_lg.render(msg, True, col)
            self.screen.blit(t, t.get_rect(center=(self.win_w // 2, panel_y + 22)))
            t2 = self.font_sm.render("Press  R  to restart   |   Q  to quit", True, (130, 130, 130))
            self.screen.blit(t2, t2.get_rect(center=(self.win_w // 2, panel_y + 52)))

        # status line
        st_col = (100, 100, 100) if not self.game_over else C_TEXT
        ts = self.font_sm.render(self.status, True, st_col)
        self.screen.blit(ts, ts.get_rect(center=(self.win_w // 2, panel_y + 70)))



        pygame.display.flip()

    def cpu_think(self):
        _, move = minimax(self.state, self.depth, -math.inf, math.inf, True)
        self.cpu_result = move

    def apply_cpu_move(self):
        move = self.cpu_result
        self.cpu_result = None
        self.cpu_busy   = False
        if move is None:
            self.status = "CPU has no moves!"
            return
        k, r, c = move
        direction = "horizontal" if k == 'h' else "vertical"
        self.status = f"CPU played  {k} {r} {c}  ({direction})"
        self.state  = self.state.play(move, red)
        if self.state.win(red):
            self.game_over = True
            self.status    = "red Player Wins!"
            return
        if not self.state.moves():
            self.game_over = True
            self.status    = "Draw!"
            return
        self.turn   = blue
        self.status = "Your turn  –  click an edge to place a blue fence"

    def run(self):
        clock = pygame.time.Clock()
        while True:
            if self.cpu_busy and self.cpu_result is not None:
                self.apply_cpu_move()

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); raise SystemExit

                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_q:
                        pygame.quit(); raise SystemExit
                    if ev.key == pygame.K_r:
                        self.show_menu(); return

                if ev.type == pygame.MOUSEMOTION and not self.cpu_busy:
                    mv = self.edge_at(*ev.pos)
                    self.hover_move = mv

                if (ev.type == pygame.MOUSEBUTTONDOWN
                        and self.turn == blue
                        and not self.game_over
                        and not self.cpu_busy):
                    mv = self.edge_at(*ev.pos)
                    if mv:
                        k, r, c = mv
                        valid = (k == 'h' and self.state.h[r][c] == empty) or \
                                (k == 'v' and self.state.v[r][c] == empty)
                        if valid:
                            self.state = self.state.play(mv, blue)
                            self.hover_move = None
                            if self.state.win(blue):
                                self.game_over = True
                                self.status    = "blue Player Wins!"
                            elif not self.state.moves():
                                self.game_over = True
                                self.status    = "Draw!"
                            else:
                                self.turn      = red
                                self.cpu_busy  = True
                                self.status    = "CPU thinking…"
                                t = threading.Thread(target=self.cpu_think, daemon=True)
                                t.start()

            self.draw()
            clock.tick(60)


if __name__ == "__main__":
    FencesGame()
