#!/usr/bin/env python3
import sys
import math

BG = ' '          # белое поле
BLUE = '#'        # "синий" цвет полос (ASCII)
STAR = '*'        # звезда

def make_star(size, one=STAR, zero=BG):
    """Возвращает список строк со звездой Давида (ASCII)."""
    S = max(7, size)
    if S % 2 == 0:
        S += 1

    Q1 = math.floor(S / 4) + (S % 2)
    long_line = S * 2 - 1
    tall_line = S + Q1
    carry = 1

    out = []
    for i in range(tall_line):
        line = []
        for j in range(long_line):
            hit = (
                    (i == Q1) or                               # верхняя длинная линия
                    (i == j + Q1) or                           # левая '\'
                    (i + Q1 == tall_line - carry) or           # нижняя длинная линия
                    (i + j == Q1 + long_line - carry) or       # правая '/'
                    (i + j == S - carry) or                    # левая '/'
                    (i + S == j + carry)                       # правая '\'
            )
            line.append(one if hit else zero)
        out.append(''.join(line))
    return out

def draw_flag(N=21, bg=' ', blue='#', star='*'):
    H = max(15, N)
    W = max(31, H * 3)
    if W % 2 == 0:
        W += 1

    t = max(1, H // 8)          # толщина полос
    top_start = t
    bot_start = H - 2 * t

    canvas = [[bg for _ in range(W)] for _ in range(H)]

    # Полосы
    for r in range(top_start, min(top_start + t, H)):
        for c in range(W):
            canvas[r][c] = blue
    for r in range(max(bot_start, 0), min(bot_start + t, H)):
        for c in range(W):
            canvas[r][c] = blue

    # Белое окно между полосами
    white_top = top_start + t
    white_bottom = bot_start
    pad = max(1, H // 20)        # отступ от полос до звезды (можешь увеличить)

    usable_h = max(7, (white_bottom - white_top) - 2 * pad)
    star_size = usable_h         # пробуем взять максимум, который влезет

    star_lines = make_star(star_size, one=star, zero=bg)
    sh, sw = len(star_lines), len(star_lines[0])

    # Если вдруг всё равно не влезло — ужимаем
    while sh > (white_bottom - white_top - 2 * pad) and star_size > 7:
        star_size -= 2
        star_lines = make_star(star_size, one=star, zero=bg)
        sh, sw = len(star_lines), len(star_lines[0])

    # Позиция: центр по ширине, центр по белому окну (а не по всему флагу)
    r0 = white_top + pad + ((white_bottom - white_top - 2 * pad - sh) // 2)
    c0 = (W - sw) // 2

    # Наложение
    for rr in range(sh):
        for cc in range(sw):
            ch = star_lines[rr][cc]
            if ch != bg:
                canvas[r0 + rr][c0 + cc] = ch

    for row in canvas:
        print(''.join(row))

def main():
    try:
        N = int(sys.argv[1]) if len(sys.argv) > 1 else 21
    except ValueError:
        N = 21
    draw_flag(N)

if __name__ == "__main__":
    main()
