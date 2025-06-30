# 🚀 ToonzyAI API - Краткое руководство для фронтенда

## 🔐 Быстрый старт

### 1. **Регистрация пользователя**
```javascript
const response = await fetch('http://localhost:8000/api/v1/auth/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'your_username',
    email: 'your@email.com',
    password: 'your_password'
  })
});
const user = await response.json();
```

### 2. **Логин и получение токена**
```javascript
const response = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'your_username',
    password: 'your_password'
  })
});
const tokenData = await response.json();
const accessToken = tokenData.access_token;

// Сохраните токен для последующих запросов
localStorage.setItem('access_token', accessToken);
```

### 3. **Использование защищенных эндпойнтов**
```javascript
const token = localStorage.getItem('access_token');

const response = await fetch('http://localhost:8000/api/v1/animations/', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  }
});
const animations = await response.json();
```

## 📍 **Правильные URL эндпойнтов**

### Системные (без токена)
- ✅ `GET /health` - проверка работоспособности
- ✅ `GET /docs` - документация Swagger

### Аутентификация
- ✅ `POST /api/v1/auth/register` - регистрация
- ✅ `POST /api/v1/auth/login` - логин
- ✅ `POST /api/v1/auth/refresh` - обновление токена

### Защищенные эндпойнты (требуют токен)
- ✅ `GET /api/v1/auth/me` - профиль пользователя
- ✅ `GET /api/v1/avatars/` - список аватаров
- ✅ `POST /api/v1/avatars/` - создание аватара
- ✅ `GET /api/v1/animations/` - список анимаций
- ✅ `POST /api/v1/animations/` - создание анимации

## ⚠️ **Частые ошибки**

| Код | Причина | Решение |
|-----|---------|---------|
| `404` | Неправильный URL | Проверьте URL из списка выше |
| `401` | Нет токена авторизации | Добавьте `Authorization: Bearer {token}` |
| `403` | Токен истек | Обновите токен через `/auth/refresh` |
| `422` | Неверные данные | Проверьте формат запроса |

## 🔄 **Обработка ошибок**
```javascript
async function apiRequest(url, options = {}) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (response.status === 401) {
    // Токен истек - перенаправить на логин
    localStorage.removeItem('access_token');
    window.location.href = '/login';
    return;
  }

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'API Error');
  }

  return response.json();
}
```

## 🎯 **Полный пример: создание аватара**
```javascript
async function createAvatar(prompt) {
  try {
    const avatar = await apiRequest('http://localhost:8000/api/v1/avatars/', {
      method: 'POST',
      body: JSON.stringify({ prompt })
    });
    
    console.log('Аватар создан:', avatar);
    return avatar;
  } catch (error) {
    console.error('Ошибка создания аватара:', error);
    throw error;
  }
}

// Использование
createAvatar('Beautiful anime character with blue hair')
  .then(avatar => {
    // Отобразить аватар в UI
    console.log('Avatar URL:', avatar.image_url);
  })
  .catch(error => {
    // Показать ошибку пользователю
    alert('Ошибка: ' + error.message);
  });
```

## 🔧 **Настройка CORS для продакшена**

Если возникают CORS ошибки, обновите `main.py`:
```python
allow_origins=[
    "http://localhost:3000",  # React dev
    "https://your-domain.com",  # Ваш домен
]
```

## 📚 **Дополнительная документация**

- **Swagger UI**: `http://localhost:8000/docs`
- **Полная документация**: `API_DOCUMENTATION.md` 