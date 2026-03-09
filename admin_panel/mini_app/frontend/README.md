# Admin Panel Frontend

Frontend приложение для админ-панели Telegram бота знакомств.

## Технологии

- React 18
- React Router
- Vite
- Axios
- Telegram Mini App SDK

## Установка

```bash
npm install
```

## Разработка

```bash
npm run dev
```

Приложение будет доступно по адресу `http://localhost:3000`

## Сборка

```bash
npm run build
```

## Структура проекта

```
src/
├── components/      # Переиспользуемые компоненты
├── pages/          # Страницы приложения
├── contexts/       # React контексты
├── services/       # API сервисы
└── App.jsx         # Главный компонент
```

## Переменные окружения

Создайте файл `.env`:

```
VITE_API_BASE_URL=http://localhost:8000
```
