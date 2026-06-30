# GitHub Actions CI/CD Setup Guide

## ⚠️ ВАЖНО: Для Windows используйте PowerShell!

## Настройка SSH (простая версия)

### **Где что хранится:**

| Файл | Где находится | Что с ним делать |
|------|--------------|------------------|
| `allitrader_deploy` | `C:\Users\mark2\.ssh\` на вашем ПК | Копируете **полное содержимое** в GitHub Secrets |
| `allitrader_deploy.pub` | `C:\Users\mark2\.ssh\` на вашем ПК | Добавляете на сервер в `~/.ssh/authorized_keys` |
| `authorized_keys` | `~/.ssh/` на сервере | Сюда добавляется публичный ключ |

---

## **Шаг 1: Генерация SSH ключа (на ВАШЕМ компьютере)**

**Откройте PowerShell (не cmd.exe!) и выполните:**

```powershell
# Создайте папку .ssh если её нет:
mkdir "$env:USERPROFILE\.ssh"

# Сгенерируйте ключ (без парольной фразы):
ssh-keygen -t ed25519 -C "allitrader-deploy" -f "$env:USERPROFILE\.ssh\allitrader_deploy" -N ""
```

**Если `ssh-keygen` не найден, укажите полный путь:**

```powershell
C:\Windows\System32\OpenSSH\ssh-keygen.exe -t ed25519 -C "allitrader-deploy" -f "$env:USERPROFILE\.ssh\allitrader_deploy" -N ""
```

**Проверьте, что файлы созданы:**

```powershell
dir "$env:USERPROFILE\.ssh\allitrader_deploy*"
```

Это создаст два файла:
- `C:\Users\mark2\.ssh\allitrader_deploy` - **ПРИВАТНЫЙ** ключ (не показывайте никому!)
- `C:\Users\mark2\.ssh\allitrader_deploy.pub` - **ПУБЛИЧНЫЙ** ключ (можно показывать)

---

## **Шаг 2: Скопируйте приватный ключ для GitHub**

**В PowerShell выполните и скопируйте ВСЁ содержимое:**

```powershell
Get-Content "$env:USERPROFILE\.ssh\allitrader_deploy"
```

**Скопируйте ВСЁ что вы увидите, ВКЛЮЧАЯ:**
- Строку `-----BEGIN OPENSSH PRIVATE KEY-----`
- Все строки с ключом
- Строку `-----END OPENSSH PRIVATE KEY-----`

Это значение будете вставлять в **SSH_PRIVATE_KEY** в GitHub Secrets.

---

## **Шаг 3: Добавьте публичный ключ на сервер**

**В PowerShell скопируйте публичный ключ:**

```powershell
Get-Content "$env:USERPROFILE\.ssh\allitrader_deploy.pub"
```

**На сервере (через SSH):**

```bash
# Подключитесь к серверу
ssh username@server-ip

# Создайте папку .ssh если её нет:
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Добавьте публичный ключ в authorized_keys:
echo "ВСТАВЬТЕ_СЮДА_ПУБЛИЧНЫЙ_КЛЮЧ_ИЗ_ШАГА_2" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**Проверьте, что ключ добавлен:**

```bash
cat ~/.ssh/authorized_keys
```

---

## **Шаг 4: Получите хост ключ для GitHub**

**В PowerShell выполните (замените server-ip на ваш IP):**

```powershell
ssh-keyscan -H your-server-ip
```

**Скопируйте вывод** (начинается с `|1|` и содержит хост ключ).

Это значение будете вставлять в **SSH_KNOWN_HOSTS** в GitHub Secrets.

---

## **Шаг 5: Добавьте секреты в GitHub**

1. Перейдите в ваш репозиторий на GitHub
2. **Settings** → **Секреты и переменные** → **Действия** → **Секреты**
3. Нажмите **"Новый секрет репозитория"**

### Добавьте следующие секреты:

| Имя секрета | Значение | Откуда взять | Важно |
|------------|----------|--------------|-------|
| `SSH_HOST` | IP или домен сервера | Например: `45.33.22.11` | Не кавычки |
| `SSH_USERNAME` | Имя пользователя SSH | `ubuntu`, `deploy`, `root` | Какой у вас |
| `SSH_PRIVATE_KEY` | **Полное содержимое** приватного ключа | Из Шага 2 | ВСЁ содержимое, включая BEGIN/END |
| `SSH_KNOWN_HOSTS` | Вывод `ssh-keyscan` | Из Шага 4 | Всё что вывели |

**⚠️ ВАЖНО:**
- Для **SSH_PRIVATE_KEY** скопируйте **ВСЁ содержимое файла** (от `-----BEGIN...` до `-----END...`)
- **Не добавляйте кавычки** вокруг значений
- Нажимайте **"Добавить секрет"** после каждого

---

## **Шаг 6: Проверьте подключение (локально)**

**В PowerShell попробуйте подключиться:**

```powershell
ssh -i "$env:USERPROFILE\.ssh\allitrader_deploy" username@server-ip
```

Если подключение прошло успешно - всё настроено верно!

---

## **Как это работает (из документации GitHub):**

```
git push → GitHub Actions → SSH на сервер → git pull → pip install → migrate → restart
```

### **Что делает workflow:**

1. ✅ **Checkout** - получает код из репозитория
2. ✅ **Deploy via SSH** - подключается к серверу и выполняет:
   - `git pull origin master` - обновляет код
   - `pip install -r requirements.txt` - устанавливает зависимости
   - `python manage.py migrate` - применяет миграции
   - `python manage.py collectstatic --noinput --clear` - собирает статику
   - `supervisorctl restart allitrader:*` - перезапускает сервисы

### **Как использовать секреты в workflow:**

```yaml
steps:
  - name: Deploy via SSH
    uses: appleboy/ssh-action@v1.1.0
    with:
      host: ${{ secrets.SSH_HOST }}
      username: ${{ secrets.SSH_USERNAME }}
      key: ${{ secrets.SSH_PRIVATE_KEY }}
      known_hosts: ${{ secrets.SSH_KNOWN_HOSTS }}
```

---

## **Типичные ошибки (из документации GitHub):**

| Ошибка | Причина | Решение |
|--------|---------|---------|
| **"Permission denied (publickey)"** | Публичный ключ не добавлен в `authorized_keys` на сервере | Проверьте Шаг 3 |
| **"Host key verification failed"** | Неверно указан `SSH_KNOWN_HOSTS` | Проверьте Шаг 4 |
| **Секрет не подставляется в `if:` условие** | Секреты нельзя использовать в условиях | Сначала присвойте секрет переменной среды |

---

## **Безопасность (из документации GitHub):**

✅ **Секреты хранятся зашифрованно** в GitHub  
✅ **Публичный ключ** добавляется в `authorized_keys` на сервере  
✅ **Доступ к серверу** только через SSH ключ  
✅ **Только ветка `master`** может запустить деплой  
⚠️ **Секреты не передаются в вилки** репозитория  
⚠️ **Маскируйте данные** в логах с помощью `::add-mask::VALUE`

---

## **Дополнительные возможности:**

### **Уведомления в Telegram:**

Добавьте в secrets `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID`, затем добавьте шаг в workflow:

```yaml
- name: Send Telegram notification
  uses: appleboy/telegram-action@v1.0.0
  if: always()
  with:
    to: ${{ secrets.TELEGRAM_CHAT_ID }}
    token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
    message: |
      Deployment status: ${{ job.status }}
      Repo: ${{ github.repository }}
      Branch: ${{ github.ref_name }}
      Commit: ${{ github.sha }}
```

---

## **Полезные ссылки:**

- [Официальная документация GitHub Actions - Использование секретов](https://docs.github.com/ru/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [SSH Keygen Guide](https://www.ssh.com/academy/ssh/keygen)
- [ssh-action](https://github.com/appleboy/ssh-action)
