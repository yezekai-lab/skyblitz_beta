"""给素材去掉纯色背景，换成透明通道。

AI 生成的素材常常是"画在白底上"的 PNG —— 直接丢进游戏会带一个白方块。
这个工具把背景真正挖成透明。

用法：

    python strip_background.py images/ship.png images/bullet.png
    python strip_background.py images/xxx.png --backup      # 先留一份备份
    python strip_background.py images/xxx.png --dry-run     # 只看结果，不改文件

原理：从图片四条边出发做洪水填充，把"和背景一样亮、而且连成一片"的像素
变透明；边缘那一圈抗锯齿的像素给一个渐变的 alpha，避免留下白毛边。

为什么不能简单地"把所有接近白色的像素都变透明"：
那样会把精灵内部的高光也一起挖掉，变成一个个透明的洞。
所以必须"从外面渗进去"，只处理连通到边界的那一片。

⚠️ 请在图片缩放完成之后再跑这个工具（在小图上处理边缘更干净，
而且在缩图之前的超大原图上跑，纯 Python 会很慢）。
原图请务必留好。
"""

import argparse
import os
import sys

import pygame

# 亮度（三通道最小值）高于 FULL 的像素，视为背景
BG_FULL = 245
# 亮度低于 SOLID 的像素，视为精灵本体
BG_SOLID = 220


def is_background_like(pixel):
    """三个通道都很亮 = 接近白/浅灰 = 可能是背景。"""
    return min(pixel[0], pixel[1], pixel[2]) >= BG_SOLID


def alpha_for(pixel):
    """边缘渐变：越亮越透明。这样抗锯齿的那一圈不会留下白色毛边。"""
    brightness = min(pixel[0], pixel[1], pixel[2])
    if brightness >= BG_FULL:
        return 0
    if brightness <= BG_SOLID:
        return 255
    ratio = (BG_FULL - brightness) / (BG_FULL - BG_SOLID)
    return int(ratio * 255)


def strip_background(surface):
    """返回一个带透明背景的新 Surface。

    `surface` 必须支持 get_at/set_at（32 位）。用 `convert_alpha()` 转一下最保险。
    """
    width, height = surface.get_size()
    work = pygame.Surface((width, height), pygame.SRCALPHA)
    work.blit(surface, (0, 0))

    # 洪水填充：从四条边所有"背景样"的像素出发，向四邻扩散
    queue = []
    visited = [[False] * width for _ in range(height)]

    for x in range(width):
        for y in (0, height - 1):
            if is_background_like(work.get_at((x, y))):
                queue.append((x, y))
                visited[y][x] = True
    for y in range(height):
        for x in (0, width - 1):
            if not visited[y][x] and is_background_like(work.get_at((x, y))):
                queue.append((x, y))
                visited[y][x] = True

    head = 0
    while head < len(queue):
        x, y = queue[head]
        head += 1
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and not visited[ny][nx]:
                if is_background_like(work.get_at((nx, ny))):
                    visited[ny][nx] = True
                    queue.append((nx, ny))

    for x, y in queue:
        r, g, b, a = work.get_at((x, y))
        work.set_at((x, y), (r, g, b, alpha_for((r, g, b, a))))
    return work, len(queue)


def report(surface, name):
    w, h = surface.get_size()
    corners = [
        tuple(surface.get_at(p))[3]
        for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))
    ]
    print(
        f"    {name}: 四角 alpha = {corners}  {'✅ 透明' if set(corners) == {0} else '❌ 仍有不透明角'}"
    )


def main():
    parser = argparse.ArgumentParser(description="把素材的背景挖成透明")
    parser.add_argument("files", nargs="+", help="要处理的 PNG 文件")
    parser.add_argument("--backup", action="store_true", help="处理前留一份 .bak.png")
    parser.add_argument("--dry-run", action="store_true", help="不写回文件")
    args = parser.parse_args()

    pygame.init()
    pygame.display.set_mode((10, 10))

    for path in args.files:
        if not os.path.exists(path):
            print(f"⚠️  找不到 {path}，跳过")
            continue
        print(f"-- {path}")
        original = pygame.image.load(path).convert_alpha()
        stripped, count = strip_background(original)
        total = stripped.get_width() * stripped.get_height()
        print(f"    挖掉 {count} 个背景像素（占 {count / total:.1%}）")
        report(stripped, "处理后")

        if args.dry_run:
            continue
        if args.backup:
            backup = os.path.splitext(path)[0] + ".bak.png"
            pygame.image.save(original, backup)
            print(f"    备份 -> {backup}")
        pygame.image.save(stripped, path)
        print(f"    已写回 {path}")

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
