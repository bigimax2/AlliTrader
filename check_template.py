import re
import sys

with open('observer_assets_single/templates/render_traders.html', 'r', encoding='utf-8') as f:
    content = f.read()
    
# Подсчет тегов
open_with = len(re.findall(r'\{%\s*with\s+', content))
close_with = len(re.findall(r'\{%\s*endwith\s*%\}', content))
open_if = len(re.findall(r'\{%\s*if\s+', content))
close_if = len(re.findall(r'\{%\s*endif\s*%\}', content))
open_for = len(re.findall(r'\{%\s*for\s+', content))
close_for = len(re.findall(r'\{%\s*endfor\s*%\}', content))
open_block = len(re.findall(r'\{%\s*block\s+', content))
close_block = len(re.findall(r'\{%\s*endblock\s*%\}', content))
open_get = len(re.findall(r'\{%\s*load\s+', content))

total_open = open_with + open_if + open_for + open_block + open_get
total_close = close_with + close_if + close_for + close_block

print(f'{{% with %}}: open={open_with}, close={close_with}, diff={open_with - close_with}')
print(f'{{% if %}}: open={open_if}, close={close_if}, diff={open_if - close_if}')
print(f'{{% for %}}: open={open_for}, close={close_for}, diff={open_for - close_for}')
print(f'{{% block %}}: open={open_block}, close={close_block}, diff={open_block - close_block}')
print(f'{{% load %}}: count={open_get}')
print(f'Total open: {total_open}, Total close: {total_close}, diff={total_open - total_close}')

if open_with == close_with and open_if == close_if and open_for == close_for and open_block == close_block:
    print('[OK] All tags are properly closed!')
else:
    print('[ERROR] Tag count mismatch!')
    sys.exit(1)
