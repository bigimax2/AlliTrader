with open('observer_assets_single/templates/render_traders.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find lines around 312-325
print('Lines 312-325:')
for i in range(311, min(325, len(lines))):
    stripped = lines[i].lstrip()
    spaces = len(lines[i]) - len(stripped)
    print(f'{i+1:4d}: [{spaces:2d} spaces] |{stripped[:60]}', end='')
