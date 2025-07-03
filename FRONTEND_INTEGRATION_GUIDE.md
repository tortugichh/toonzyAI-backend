# 🎬 ToonzyAI Frontend Integration Guide

Полное руководство по интеграции фронтенда с API системы анимации ToonzyAI.

## 📋 Оглавление

1. [Быстрый старт](#быстрый-старт)
2. [Аутентификация](#аутентификация)
3. [Основные API операции](#основные-api-операции)
4. [React Hooks](#react-hooks)
5. [React компоненты](#react-компоненты)
6. [Обработка ошибок](#обработка-ошибок)
7. [TypeScript типы](#typescript-типы)
8. [CSS стили](#css-стили)
9. [Полный пример приложения](#полный-пример-приложения)

## 🚀 Быстрый старт

### Базовая настройка API клиента

```javascript
// api.js
const API_BASE_URL = 'http://localhost:8000/api/v1';

class ToonzyAPI {
  constructor() {
    this.baseURL = API_BASE_URL;
    this.token = localStorage.getItem('auth_token');
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token && { 'Authorization': `Bearer ${this.token}` }),
      ...options.headers
    };

    const response = await fetch(url, { ...options, headers });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'API Error');
    }
    
    return response.json();
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('auth_token');
  }
}

export const api = new ToonzyAPI();
```

## 🔐 Аутентификация

### Регистрация и авторизация

```javascript
// auth.js
export async function registerUser(userData) {
  try {
    const response = await api.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email: userData.email,
        password: userData.password,
        name: userData.name
      })
    });
    
    return response;
  } catch (error) {
    console.error('Registration failed:', error.message);
    throw error;
  }
}

export async function loginUser(credentials) {
  try {
    const formData = new FormData();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);
    
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      throw new Error('Login failed');
    }
    
    const data = await response.json();
    api.setToken(data.access_token);
    
    return data;
  } catch (error) {
    console.error('Login failed:', error.message);
    throw error;
  }
}

export async function getCurrentUser() {
  return api.request('/auth/me');
}
```

### React Auth Provider

```jsx
// useAuth.js
import { useState, useEffect, createContext, useContext } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      api.setToken(token);
      getCurrentUser()
        .then(setUser)
        .catch(() => {
          api.clearToken();
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (credentials) => {
    const data = await loginUser(credentials);
    setUser(data.user);
    return data;
  };

  const logout = () => {
    api.clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

## 🎭 Основные API операции

### Аватары

```javascript
// avatars.js
export async function createAvatar(avatarData) {
  return api.request('/avatars', {
    method: 'POST',
    body: JSON.stringify({
      prompt: avatarData.prompt,
      age: avatarData.age,
      gender: avatarData.gender
    })
  });
}

export async function getAvatars() {
  return api.request('/avatars');
}

export async function getAvatar(avatarId) {
  return api.request(`/avatars/${avatarId}`);
}
```

### Анимационные проекты

```javascript
// animations.js
export async function createAnimationProject(projectData) {
  return api.request('/animations', {
    method: 'POST',
    body: JSON.stringify({
      title: projectData.title,
      source_avatar_id: projectData.avatarId,
      total_segments: projectData.totalSegments,
      animation_prompt: projectData.prompt
    })
  });
}

export async function getAnimationProjects() {
  return api.request('/animations');
}

export async function getAnimationProject(projectId) {
  return api.request(`/animations/${projectId}`);
}
```

### 🎯 Управление сегментами

```javascript
// segments.js

// Установить пользовательский промпт для сегмента
export async function setSegmentPrompt(projectId, segmentNumber, prompt) {
  return api.request(`/animations/${projectId}/segments/${segmentNumber}/prompt`, {
    method: 'PUT',
    body: JSON.stringify({
      segment_prompt: prompt
    })
  });
}

// Получить информацию о сегменте
export async function getSegment(projectId, segmentNumber) {
  return api.request(`/animations/${projectId}/segments/${segmentNumber}`);
}

// Запустить генерацию видео для сегмента
export async function generateSegment(projectId, segmentNumber) {
  return api.request(`/animations/${projectId}/segments/${segmentNumber}/generate`, {
    method: 'POST'
  });
}

// Получить статус генерации
export async function getGenerationStatus(taskId) {
  return api.request(`/tasks/${taskId}/status`);
}
```

## 🎣 React Hooks

### Hook для работы с сегментами

```jsx
// useSegments.js
import { useState, useEffect } from 'react';

export function useSegments(projectId) {
  const [segments, setSegments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (projectId) {
      loadProject();
    }
  }, [projectId]);

  const loadProject = async () => {
    try {
      const project = await getAnimationProject(projectId);
      setSegments(project.segments);
    } catch (error) {
      console.error('Failed to load segments:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateSegmentPrompt = async (segmentNumber, prompt) => {
    try {
      await setSegmentPrompt(projectId, segmentNumber, prompt);
      
      // Обновляем локальное состояние
      setSegments(prev => 
        prev.map(segment => 
          segment.segment_number === segmentNumber 
            ? { ...segment, segment_prompt: prompt, prompt_source: 'custom' }
            : segment
        )
      );
    } catch (error) {
      console.error('Failed to update segment prompt:', error);
      throw error;
    }
  };

  const generateSegmentVideo = async (segmentNumber) => {
    try {
      const task = await generateSegment(projectId, segmentNumber);
      
      // Обновляем статус сегмента
      setSegments(prev =>
        prev.map(segment =>
          segment.segment_number === segmentNumber
            ? { ...segment, status: 'IN_PROGRESS', task_id: task.task_id }
            : segment
        )
      );

      return task;
    } catch (error) {
      console.error('Failed to generate segment:', error);
      throw error;
    }
  };

  return {
    segments,
    loading,
    updateSegmentPrompt,
    generateSegmentVideo,
    refresh: loadProject
  };
}
```

### Hook для отслеживания прогресса

```jsx
// useTaskProgress.js
import { useState, useEffect, useRef } from 'react';

export function useTaskProgress(taskId, onComplete) {
  const [status, setStatus] = useState('PENDING');
  const [progress, setProgress] = useState(0);
  const intervalRef = useRef();

  useEffect(() => {
    if (!taskId) return;

    const checkStatus = async () => {
      try {
        const result = await getGenerationStatus(taskId);
        setStatus(result.status);
        setProgress(result.progress || 0);

        if (result.status === 'COMPLETED' || result.status === 'FAILED') {
          clearInterval(intervalRef.current);
          onComplete?.(result);
        }
      } catch (error) {
        console.error('Failed to check task status:', error);
      }
    };

    // Проверяем каждые 3 секунды
    intervalRef.current = setInterval(checkStatus, 3000);
    checkStatus(); // Первая проверка сразу

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [taskId, onComplete]);

  return { status, progress };
}
```

## 🎬 React компоненты

### Компонент редактора сегмента

```jsx
// SegmentEditor.jsx
import React, { useState } from 'react';
import { useTaskProgress } from './useTaskProgress';

export function SegmentEditor({ projectId, segment, onUpdate }) {
  const [prompt, setPrompt] = useState(segment.segment_prompt || '');
  const [isEditing, setIsEditing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const { status: taskStatus } = useTaskProgress(
    segment.task_id, 
    (result) => {
      onUpdate();
      setIsGenerating(false);
    }
  );

  const handleSavePrompt = async () => {
    try {
      await setSegmentPrompt(projectId, segment.segment_number, prompt);
      setIsEditing(false);
      onUpdate();
    } catch (error) {
      alert('Ошибка сохранения промпта: ' + error.message);
    }
  };

  const handleGenerate = async () => {
    try {
      setIsGenerating(true);
      await generateSegment(projectId, segment.segment_number);
      onUpdate();
    } catch (error) {
      alert('Ошибка запуска генерации: ' + error.message);
      setIsGenerating(false);
    }
  };

  const getStatusIcon = () => {
    switch (segment.status) {
      case 'COMPLETED': return '✅';
      case 'IN_PROGRESS': return '⏳';
      case 'FAILED': return '❌';
      default: return '⏸️';
    }
  };

  return (
    <div className="segment-editor">
      <div className="segment-header">
        <h3>Сегмент {segment.segment_number} {getStatusIcon()}</h3>
        <span className="prompt-source">
          {segment.prompt_source === 'custom' ? '🎯 Пользовательский' : '📝 По умолчанию'}
        </span>
      </div>

      <div className="prompt-section">
        {isEditing ? (
          <div>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Опишите что должно происходить в этом сегменте..."
              rows={3}
              className="prompt-input"
            />
            <div className="prompt-actions">
              <button onClick={handleSavePrompt} className="btn-save">
                Сохранить
              </button>
              <button onClick={() => setIsEditing(false)} className="btn-cancel">
                Отмена
              </button>
            </div>
          </div>
        ) : (
          <div>
            <p className="prompt-display">
              {segment.segment_prompt || segment.animation_prompt || 'Промпт не задан'}
            </p>
            <button onClick={() => setIsEditing(true)} className="btn-edit">
              ✏️ Редактировать промпт
            </button>
          </div>
        )}
      </div>

      <div className="generation-section">
        <button 
          onClick={handleGenerate}
          disabled={isGenerating || segment.status === 'IN_PROGRESS'}
          className="btn-generate"
        >
          {isGenerating ? 'Генерация...' : '🎬 Генерировать видео'}
        </button>
        
        {segment.generated_video_url && (
          <div className="video-preview">
            <video 
              src={segment.generated_video_url} 
              controls 
              className="segment-video"
            />
          </div>
        )}
      </div>
    </div>
  );
}
```

### Главный компонент проекта

```jsx
// AnimationProject.jsx
import React from 'react';
import { useSegments } from './useSegments';
import { SegmentEditor } from './SegmentEditor';

export function AnimationProject({ projectId, onBack }) {
  const { segments, loading, refresh } = useSegments(projectId);

  if (loading) {
    return <div className="loading">Загрузка проекта...</div>;
  }

  return (
    <div className="animation-project">
      <div className="project-header">
        <button onClick={onBack} className="btn-back">← Назад</button>
        <h2>Редактор анимационного проекта</h2>
      </div>
      
      <div className="segments-list">
        {segments.map(segment => (
          <SegmentEditor 
            key={segment.id}
            projectId={projectId}
            segment={segment}
            onUpdate={refresh}
          />
        ))}
      </div>
    </div>
  );
}
```

### Компонент создания проекта

```jsx
// CreateProject.jsx
import React, { useState, useEffect } from 'react';

export function CreateProject({ onProjectCreated }) {
  const [avatars, setAvatars] = useState([]);
  const [formData, setFormData] = useState({
    title: '',
    avatarId: '',
    totalSegments: 3,
    prompt: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    loadAvatars();
  }, []);

  const loadAvatars = async () => {
    try {
      const avatarList = await getAvatars();
      setAvatars(avatarList);
    } catch (error) {
      console.error('Failed to load avatars:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      const project = await createAnimationProject(formData);
      onProjectCreated(project);
    } catch (error) {
      alert('Ошибка создания проекта: ' + error.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="create-project-form">
      <h2>Создать новый проект</h2>
      
      <div className="form-group">
        <label>Название проекта</label>
        <input
          type="text"
          value={formData.title}
          onChange={(e) => setFormData({...formData, title: e.target.value})}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="form-group">
        <label>Выберите аватар</label>
        <select
          value={formData.avatarId}
          onChange={(e) => setFormData({...formData, avatarId: e.target.value})}
          required
          disabled={isSubmitting}
        >
          <option value="">Выберите аватар</option>
          {avatars.map(avatar => (
            <option key={avatar.id} value={avatar.id}>
              {avatar.prompt} ({avatar.gender}, {avatar.age} лет)
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>Количество сегментов</label>
        <input
          type="number"
          min="1"
          max="10"
          value={formData.totalSegments}
          onChange={(e) => setFormData({...formData, totalSegments: parseInt(e.target.value)})}
          disabled={isSubmitting}
        />
      </div>

      <div className="form-group">
        <label>Общий промпт для анимации</label>
        <textarea
          value={formData.prompt}
          onChange={(e) => setFormData({...formData, prompt: e.target.value})}
          placeholder="Опишите общую концепцию анимации..."
          rows={3}
          disabled={isSubmitting}
        />
      </div>

      <button type="submit" className="btn-create" disabled={isSubmitting}>
        {isSubmitting ? 'Создание...' : 'Создать проект'}
      </button>
    </form>
  );
}
```

## ⚠️ Обработка ошибок

### Централизованная обработка

```javascript
// errorHandler.js
export class APIError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export async function handleAPIRequest(requestFn) {
  try {
    return await requestFn();
  } catch (error) {
    if (error.status === 401) {
      window.location.href = '/login';
      return;
    }
    
    if (error.status === 403) {
      throw new APIError('Доступ запрещен', 403, 'FORBIDDEN');
    }
    
    if (error.status === 422) {
      throw new APIError('Неверные данные', 422, 'VALIDATION_ERROR');
    }
    
    if (error.status >= 500) {
      throw new APIError('Ошибка сервера', error.status, 'SERVER_ERROR');
    }
    
    throw error;
  }
}

// 🔧 URL утилиты (НЕ НУЖНО - ИСПРАВЛЕНО В API)
// Раньше требовалась ручная конвертация gs:// URLs:
/*
function convertGcsUrl(gcsUrl) {
  if (gcsUrl && gcsUrl.startsWith('gs://')) {
    const parts = gcsUrl.substring(5).split('/', 1);
    const bucket = parts[0];
    const path = gcsUrl.substring(5 + bucket.length + 1);
    return `https://storage.googleapis.com/${bucket}/${path}`;
  }
  return gcsUrl;
}
*/
// ✅ Теперь API автоматически возвращает правильные HTTPS URLs!
```

### Error Boundary

```jsx
// ErrorBoundary.jsx
import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback">
          <h2>Что-то пошло не так</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => window.location.reload()}>
            Перезагрузить страницу
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

## 📱 TypeScript типы

```typescript
// types.ts
export interface User {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface Avatar {
  id: string;
  prompt: string;
  age: number;
  gender: 'male' | 'female';
  image_url?: string;
  created_at: string;
}

export interface AnimationProject {
  id: string;
  user_id: string;
  title?: string;
  source_avatar_id: string;
  total_segments: number;
  animation_prompt: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  final_video_url?: string;
  segments: AnimationSegment[];
  created_at: string;
  updated_at: string;
}

export interface AnimationSegment {
  id: string;
  animation_project_id: string;
  segment_number: number;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  segment_prompt?: string;
  prompt_source: 'default' | 'custom';
  start_frame_url?: string;
  generated_video_url?: string;
  task_id?: string;
  created_at: string;
  updated_at: string;
}

export interface GenerationTask {
  task_id: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  progress: number;
  result?: any;
  error?: string;
}
```

## 🎨 CSS стили

```css
/* styles.css */
.animation-project {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.project-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.btn-back {
  background: #6c757d;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.segment-editor {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.segment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.prompt-source {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  background: #f0f0f0;
  color: #666;
}

.prompt-input {
  width: 100%;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 8px;
  font-family: inherit;
  resize: vertical;
  font-size: 14px;
}

.prompt-display {
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
  margin-bottom: 8px;
  min-height: 40px;
}

.btn-generate {
  background: #007bff;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 8px;
  font-size: 14px;
  transition: background-color 0.2s;
}

.btn-generate:hover:not(:disabled) {
  background: #0056b3;
}

.btn-generate:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-save {
  background: #28a745;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  margin-right: 8px;
}

.btn-cancel {
  background: #6c757d;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
}

.btn-edit {
  background: #ffc107;
  color: #212529;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
}

.segment-video {
  width: 100%;
  max-width: 400px;
  margin-top: 12px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
  font-size: 18px;
}

.create-project-form {
  max-width: 500px;
  margin: 0 auto;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-weight: 500;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 14px;
}

.btn-create {
  width: 100%;
  background: #007bff;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  margin-top: 16px;
}

.btn-create:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.error-fallback {
  text-align: center;
  padding: 40px;
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 8px;
  margin: 20px;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-logout {
  background: #dc3545;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
}

.welcome-screen {
  text-align: center;
  padding: 60px 20px;
}

.btn-create-project {
  background: #007bff;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  margin-top: 20px;
}
```

## 🚦 Полный пример приложения

```jsx
// App.jsx
import React, { useState } from 'react';
import { AuthProvider, useAuth } from './useAuth';
import { AnimationProject } from './AnimationProject';
import { CreateProject } from './CreateProject';
import { ErrorBoundary } from './ErrorBoundary';

function Dashboard() {
  const { user, logout } = useAuth();
  const [currentProject, setCurrentProject] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  if (!user) {
    return <div>Загрузка...</div>;
  }

  return (
    <div className="dashboard">
      <header className="app-header">
        <h1>🎬 ToonzyAI Studio</h1>
        <div className="user-info">
          <span>Привет, {user.name}!</span>
          <button onClick={logout} className="btn-logout">Выйти</button>
        </div>
      </header>

      <main className="main-content">
        {!currentProject && !showCreateForm && (
          <div className="welcome-screen">
            <h2>Добро пожаловать в ToonzyAI!</h2>
            <p>Создавайте анимации с уникальными промптами для каждого сегмента</p>
            <button 
              onClick={() => setShowCreateForm(true)}
              className="btn-create-project"
            >
              🎭 Создать новый проект
            </button>
          </div>
        )}

        {showCreateForm && (
          <CreateProject 
            onProjectCreated={(project) => {
              setCurrentProject(project);
              setShowCreateForm(false);
            }}
          />
        )}

        {currentProject && (
          <AnimationProject 
            projectId={currentProject.id} 
            onBack={() => setCurrentProject(null)}
          />
        )}
      </main>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Dashboard />
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
```

## 🎯 Ключевые особенности

### Пользовательские промпты для сегментов
- ✅ Каждый сегмент может иметь свой уникальный промпт
- ✅ Fallback на общий промпт проекта если не задан
- ✅ Визуальное отличие пользовательских и дефолтных промптов

### Генерация видео
- ✅ Асинхронная генерация через Celery
- ✅ Отслеживание прогресса через polling
- ✅ Обработка ошибок и retry логика

### Последовательность сегментов
- ✅ Каждый сегмент использует последний кадр предыдущего
- ✅ Автоматическая проверка зависимостей

### UX/UI особенности
- ✅ Интуитивное редактирование промптов inline
- ✅ Статусы с иконками для быстрого понимания
- ✅ Превью видео прямо в интерфейсе
- ✅ Error boundary для отлова ошибок
- ✅ Loading состояния для лучшего UX

### 🔧 URL обработка (РЕШЕНО)
- ✅ **Автоматическая конвертация** `gs://` URLs в публичные HTTPS URLs
- ✅ **Браузер-совместимые** ссылки на видео и изображения
- ✅ **Нет ошибок** `net::ERR_UNKNOWN_URL_SCHEME`
- ✅ **Прямой доступ** к медиа файлам из браузера

---

**💡 Совет:** Используйте этот гайд как основу и адаптируйте компоненты под ваш дизайн-систему и требования UX. Система полностью готова к работе! 