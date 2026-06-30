#!/bin/bash
# Скрипт для генерации SSH ключа и настройки доступа к серверу

echo "=== Генерация SSH ключа для деплоя ==="

# Генерация ключа
ssh-keygen -t ed25519 -C "allitrader-deploy" -f ~/.ssh/allitrader_deploy

echo ""
echo "=== Инструкция по настройке GitHub ==="
echo "1. Скопируйте содержимое приватного ключа:"
echo "   cat ~/.ssh/allitrader_deploy"
echo ""
echo "2. Скопируйте содержимое публичного ключа:"
echo "   cat ~/.ssh/allitrader_deploy.pub"
echo ""
echo "3. Добавьте публичный ключ на сервер:"
echo "   ssh-copy-id -i ~/.ssh/allitrader_deploy.pub user@server-ip"
echo "   ИЛИ вручную добавьте в ~/.ssh/authorized_keys на сервере"
echo ""
echo "4. Добавьте секреты в GitHub:"
echo "   - SSH_HOST: IP адрес сервера"
echo "   - SSH_USERNAME: имя пользователя (ubuntu, deploy, root)"
echo "   - SSH_PRIVATE_KEY: содержимое ~/.ssh/allitrader_deploy"
echo "   - SSH_KNOWN_HOSTS: ssh-keyscan -H server-ip"
