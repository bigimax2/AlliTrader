with open('observer_assets_single/templates/render_traders.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check current state
print('Before fix:')
for i in [239, 240, 241, 242, 243, 244]:
    line = lines[i]
    stripped = line.lstrip()
    spaces = len(line) - len(stripped)
    print(f'Line {i+1}: {spaces} spaces - {stripped[:60]}...')

# Fix line 241 (index 240) and 244 (index 243) - remove 4 spaces
if lines[240].startswith('                                                                        '):  # 72 spaces
    lines[240] = lines[240][4:]
if lines[243].startswith('                                                                        '):  # 72 spaces
    lines[243] = lines[243][4:]

# Write back
with open('observer_assets_single/templates/render_traders.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done')
