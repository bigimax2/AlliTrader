// Переключение темы
const themeToggle = document.getElementById('themeToggle');
const htmlElement = document.documentElement;

// Загрузка сохраненной темы при старте
const savedTheme = localStorage.getItem('theme') || 'light';
applyTheme(savedTheme);

// Обработчик переключения темы
if (themeToggle) {
    themeToggle.addEventListener('click', function(e) {
        e.stopPropagation();
        const currentTheme = htmlElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    });
}

// Функция применения темы
function applyTheme(theme) {
    if (theme === 'dark') {
        htmlElement.setAttribute('data-theme', 'dark');
        const themeIconText = document.querySelector('.theme-icon');
        if (themeIconText) themeIconText.textContent = '☀️';
    } else {
        htmlElement.setAttribute('data-theme', 'light');
        const themeIconText = document.querySelector('.theme-icon');
        if (themeIconText) themeIconText.textContent = '🌙';
    }
}

// Переключение бокового меню для десктопа
const menuToggleDesktop = document.getElementById('menuToggleDesktop');
const sidebar = document.getElementById('sidebar');
const mainContent = document.querySelector('.main-content');

if (menuToggleDesktop) {
    menuToggleDesktop.addEventListener('click', function(e) {
        e.stopPropagation();
        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('expanded');
    });
}

// Переключение бокового меню на мобильных
const menuToggleMobile = document.getElementById('menuToggleMobile');

if (menuToggleMobile) {
    menuToggleMobile.addEventListener('click', function(e) {
        e.stopPropagation();
        sidebar.classList.toggle('show');
    });
}

// Закрытие бокового меню при клике на контент на мобильных
mainContent.addEventListener('click', function(e) {
    if (window.innerWidth <= 768 && sidebar.classList.contains('show')) {
        sidebar.classList.remove('show');
    }
});

// Установка активного пункта меню при клике
const navLinks = document.querySelectorAll('.sidebar .nav-link, .navbar-nav .nav-link');

// Восстановление активного пункта на основе текущего URL при загрузке
function setActiveLink() {
    const currentUrl = window.location.pathname;

    navLinks.forEach(link => {
        const linkHref = link.getAttribute('href');

        // Если href совпадает с текущим URL (или является подпутем)
        if (linkHref && (linkHref === currentUrl || currentUrl.startsWith(linkHref))) {
            link.classList.add('active');
        }
    });
}

// Вызываем при загрузке
setActiveLink();

// Добавляем обработчики кликов
navLinks.forEach(link => {
    link.addEventListener('click', function(e) {
        // Убираем класс active со всех ссылок в меню
        navLinks.forEach(l => l.classList.remove('active'));

        // Добавляем класс active текущей ссылке
        this.classList.add('active');

        // Сохраняем активную ссылку в localStorage
        localStorage.setItem('activeLink', this.getAttribute('href'));

        // Для десктопа закрываем боковое меню при клике на мобильных
        if (window.innerWidth <= 768 && sidebar.classList.contains('show')) {
            sidebar.classList.remove('show');
        }
    });
});

// Обработка клика по выпадающему меню
const dropdownItems = document.querySelectorAll('.dropdown-menu .dropdown-item');
dropdownItems.forEach(item => {
    item.addEventListener('click', function(e) {
        // Убираем класс active со всех dropdown-item
        dropdownItems.forEach(i => i.classList.remove('active'));

        // Добавляем класс active текущему элементу
        this.classList.add('active');
    });
});
