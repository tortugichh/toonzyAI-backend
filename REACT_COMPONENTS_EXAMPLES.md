# 🚀 React Components Examples для ToonzyAI API

## Готовые компоненты для быстрой интеграции

### 1. 🔐 AuthProvider - Контекст аутентификации

```tsx
// src/contexts/AuthContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  register: (username: string, email: string, password: string) => Promise<void>;
  isLoading: boolean;
  refreshToken: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('access_token'));
  const [isLoading, setIsLoading] = useState(true);

  const apiRequest = async (url: string, options: RequestInit = {}) => {
    const response = await fetch(`/api/v1${url}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
      },
    });

    if (!response.ok) {
      if (response.status === 401 && token) {
        const refreshed = await refreshToken();
        if (refreshed) {
          // Retry with new token
          return fetch(`/api/v1${url}`, {
            ...options,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              ...options.headers,
            },
          });
        }
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response;
  };

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        throw new Error('Invalid credentials');
      }

      const tokens = await response.json();
      localStorage.setItem('access_token', tokens.access_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);
      setToken(tokens.access_token);
      
      // Получаем информацию о пользователе
      await fetchUser();
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (username: string, email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Registration failed');
      }

      // После успешной регистрации автоматически логинимся
      await login(username, password);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setToken(null);
    setUser(null);
  };

  const refreshToken = async (): Promise<boolean> => {
    const refreshTokenValue = localStorage.getItem('refresh_token');
    if (!refreshTokenValue) return false;

    try {
      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshTokenValue }),
      });

      if (response.ok) {
        const tokens = await response.json();
        localStorage.setItem('access_token', tokens.access_token);
        localStorage.setItem('refresh_token', tokens.refresh_token);
        setToken(tokens.access_token);
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }

    logout();
    return false;
  };

  const fetchUser = async () => {
    if (!token) return;

    try {
      const response = await apiRequest('/auth/me');
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      }
    } catch (error) {
      console.error('Failed to fetch user:', error);
      logout();
    }
  };

  useEffect(() => {
    if (token) {
      fetchUser();
    } else {
      setIsLoading(false);
    }
  }, [token]);

  return (
    <AuthContext.Provider
      value={{ user, token, login, logout, register, isLoading, refreshToken }}
    >
      {children}
    </AuthContext.Provider>
  );
};
```

### 2. 🎨 AvatarCreator - Создание аватаров

```tsx
// src/components/AvatarCreator.tsx
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface Avatar {
  avatar_id: string;
  image_url: string;
  prompt: string;
  status: string;
  user_id: string;
  created_at: string;
}

export const AvatarCreator: React.FC<{ onAvatarCreated?: (avatar: Avatar) => void }> = ({
  onAvatarCreated
}) => {
  const { token } = useAuth();
  const [prompt, setPrompt] = useState('');
  const [avatar, setAvatar] = useState<Avatar | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createAvatar = async () => {
    if (!prompt.trim()) {
      setError('Пожалуйста, введите описание аватара');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/avatars/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        throw new Error('Не удалось создать аватар');
      }

      const result = await response.json();
      setAvatar(result);
      setPrompt('');
      onAvatarCreated?.(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold mb-4">Создать аватар</h2>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Описание аватара
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Например: Cute cartoon cat with blue eyes wearing a red hat"
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={3}
            disabled={loading}
          />
        </div>

        {error && (
          <div className="text-red-600 text-sm bg-red-50 p-2 rounded">
            {error}
          </div>
        )}

        <button
          onClick={createAvatar}
          disabled={loading || !prompt.trim()}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <div className="flex items-center justify-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              <span>Создается...</span>
            </div>
          ) : (
            'Создать аватар'
          )}
        </button>
      </div>

      {avatar && (
        <div className="mt-6 text-center">
          <h3 className="text-lg font-semibold mb-2">Аватар создан!</h3>
          <img
            src={avatar.image_url}
            alt="Generated Avatar"
            className="mx-auto rounded-lg shadow-md"
            style={{ width: 256, height: 256 }}
          />
          <p className="text-sm text-gray-600 mt-2">{avatar.prompt}</p>
        </div>
      )}
    </div>
  );
};
```

### 3. 📋 AvatarList - Список аватаров

```tsx
// src/components/AvatarList.tsx
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface Avatar {
  avatar_id: string;
  image_url: string;
  prompt: string;
  status: string;
  user_id: string;
  created_at: string;
}

interface AvatarListResponse {
  avatars: Avatar[];
  total: number;
  page: number;
  per_page: number;
}

export const AvatarList: React.FC<{ onAvatarSelect?: (avatar: Avatar) => void }> = ({
  onAvatarSelect
}) => {
  const { token } = useAuth();
  const [avatars, setAvatars] = useState<Avatar[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const perPage = 12;

  const fetchAvatars = async (pageNum: number = 1) => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/v1/avatars/?page=${pageNum}&per_page=${perPage}`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );

      if (!response.ok) {
        throw new Error('Не удалось загрузить аватары');
      }

      const data: AvatarListResponse = await response.json();
      setAvatars(data.avatars);
      setTotal(data.total);
      setPage(data.page);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка');
    } finally {
      setLoading(false);
    }
  };

  const deleteAvatar = async (avatarId: string) => {
    if (!confirm('Вы уверены, что хотите удалить этот аватар?')) return;

    try {
      const response = await fetch(`/api/v1/avatars/${avatarId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        setAvatars(avatars.filter(avatar => avatar.avatar_id !== avatarId));
        setTotal(total - 1);
      }
    } catch (err) {
      console.error('Failed to delete avatar:', err);
    }
  };

  useEffect(() => {
    fetchAvatars(page);
  }, [page]);

  if (loading && avatars.length === 0) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center text-red-600 p-4">
        <p>{error}</p>
        <button 
          onClick={() => fetchAvatars(page)}
          className="mt-2 text-blue-600 hover:underline"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Мои аватары</h2>
        <span className="text-sm text-gray-600">Всего: {total}</span>
      </div>

      {avatars.length === 0 ? (
        <div className="text-center text-gray-600 py-8">
          <p>У вас пока нет аватаров</p>
          <p className="text-sm">Создайте свой первый аватар!</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {avatars.map((avatar) => (
              <div
                key={avatar.avatar_id}
                className="border rounded-lg overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => onAvatarSelect?.(avatar)}
              >
                <img
                  src={avatar.image_url}
                  alt={avatar.prompt}
                  className="w-full h-32 object-cover"
                />
                <div className="p-2">
                  <p className="text-xs text-gray-600 truncate" title={avatar.prompt}>
                    {avatar.prompt}
                  </p>
                  <div className="flex justify-between items-center mt-2">
                    <span className="text-xs text-gray-500">
                      {new Date(avatar.created_at).toLocaleDateString()}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteAvatar(avatar.avatar_id);
                      }}
                      className="text-red-500 hover:text-red-700 text-xs"
                    >
                      Удалить
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex justify-center items-center space-x-2 mt-6">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                Назад
              </button>
              <span className="text-sm">
                Страница {page} из {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                Вперед
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};
```

### 4. 🎬 AnimationStudio - Студия анимации

```tsx
// src/components/AnimationStudio.tsx
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface AnimationSegment {
  id: string;
  segment_number: number;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  segment_prompt: string | null;
  start_frame_url: string;
  generated_video_url: string | null;
  video_url: string | null;
  created_at: string;
  updated_at: string;
}

interface AnimationProject {
  id: string;
  user_id: string;
  source_avatar_id: string;
  total_segments: number;
  animation_prompt: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'assembling';
  final_video_url: string | null;
  video_url: string | null;
  created_at: string;
  updated_at: string;
  segments: AnimationSegment[];
}

export const AnimationStudio: React.FC<{ avatarId: string }> = ({ avatarId }) => {
  const { token } = useAuth();
  const [project, setProject] = useState<AnimationProject | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [segmentPrompts, setSegmentPrompts] = useState<{ [key: number]: string }>({});

  const createProject = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/animations/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_avatar_id: avatarId,
          total_segments: 5,
          animation_prompt: "Character performing various dynamic actions"
        }),
      });

      if (!response.ok) {
        throw new Error('Не удалось создать проект анимации');
      }

      const result = await response.json();
      setProject(result);
      startPolling(result.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка');
    } finally {
      setLoading(false);
    }
  };

  const startPolling = (projectId: string) => {
    const poll = async () => {
      try {
        const response = await fetch(`/api/v1/animations/${projectId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
          const data = await response.json();
          setProject(data);

          // Продолжаем polling если есть активные процессы
          const hasActive = data.segments.some((s: AnimationSegment) => 
            s.status === 'pending' || s.status === 'in_progress'
          ) || data.status === 'assembling';

          if (hasActive) {
            setTimeout(poll, 5000);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
        setTimeout(poll, 10000); // Retry after error
      }
    };

    poll();
  };

  const updateSegmentPrompt = async (segmentNumber: number, prompt: string) => {
    if (!project) return;

    try {
      const response = await fetch(
        `/api/v1/animations/${project.id}/segments/${segmentNumber}/prompt`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ segment_prompt: prompt }),
        }
      );

      if (response.ok) {
        // Обновляем локальное состояние
        setProject(prev => prev ? {
          ...prev,
          segments: prev.segments.map(segment =>
            segment.segment_number === segmentNumber
              ? { ...segment, segment_prompt: prompt }
              : segment
          )
        } : null);
      }
    } catch (error) {
      console.error('Failed to update prompt:', error);
    }
  };

  const generateSegment = async (segmentNumber: number) => {
    if (!project) return;

    try {
      const response = await fetch(
        `/api/v1/animations/${project.id}/segments/${segmentNumber}/generate`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.ok) {
        startPolling(project.id);
      }
    } catch (error) {
      console.error('Failed to generate segment:', error);
    }
  };

  const assembleVideo = async () => {
    if (!project) return;

    try {
      const response = await fetch(`/api/v1/animations/${project.id}/assemble`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        startPolling(project.id);
      }
    } catch (error) {
      console.error('Failed to assemble video:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100';
      case 'in_progress': return 'text-blue-600 bg-blue-100';
      case 'pending': return 'text-yellow-600 bg-yellow-100';
      case 'failed': return 'text-red-600 bg-red-100';
      case 'assembling': return 'text-purple-600 bg-purple-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed': return 'Готово';
      case 'in_progress': return 'Генерируется...';
      case 'pending': return 'Ожидает';
      case 'failed': return 'Ошибка';
      case 'assembling': return 'Собирается...';
      default: return status;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold mb-4">Студия анимации</h2>

      {!project ? (
        <div className="text-center">
          <p className="text-gray-600 mb-4">
            Создайте новый проект анимации для этого аватара
          </p>
          <button
            onClick={createProject}
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Создается...' : 'Создать проект'}
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Информация о проекте */}
          <div className="border rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-semibold">Проект анимации</h3>
              <span className={`px-2 py-1 rounded text-sm ${getStatusColor(project.status)}`}>
                {getStatusText(project.status)}
              </span>
            </div>
            <p className="text-sm text-gray-600">{project.animation_prompt}</p>
            <p className="text-xs text-gray-500 mt-1">
              Сегментов: {project.segments.length}/{project.total_segments}
            </p>
          </div>

          {/* Сегменты */}
          {project.segments.length > 0 && (
            <div className="grid gap-4">
              <h4 className="font-semibold">Сегменты анимации</h4>
              {project.segments.map((segment) => (
                <div key={segment.id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-center mb-2">
                    <h5 className="font-medium">Сегмент {segment.segment_number}</h5>
                    <span className={`px-2 py-1 rounded text-sm ${getStatusColor(segment.status)}`}>
                      {getStatusText(segment.status)}
                    </span>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Промпт для сегмента
                      </label>
                      <input
                        type="text"
                        value={segmentPrompts[segment.segment_number] || segment.segment_prompt || ''}
                        onChange={(e) => setSegmentPrompts({
                          ...segmentPrompts,
                          [segment.segment_number]: e.target.value
                        })}
                        placeholder="Опишите действие для этого сегмента..."
                        className="w-full p-2 border border-gray-300 rounded text-sm"
                      />
                      <button
                        onClick={() => updateSegmentPrompt(
                          segment.segment_number,
                          segmentPrompts[segment.segment_number] || ''
                        )}
                        className="mt-1 text-xs text-blue-600 hover:underline"
                      >
                        Сохранить промпт
                      </button>
                    </div>

                    <div className="flex space-x-2">
                      {segment.status === 'pending' && (
                        <button
                          onClick={() => generateSegment(segment.segment_number)}
                          className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
                        >
                          Генерировать
                        </button>
                      )}

                      {segment.status === 'completed' && segment.video_url && (
                        <video
                          controls
                          className="w-full max-w-sm rounded"
                          style={{ height: '200px' }}
                        >
                          <source src={segment.video_url} type="video/mp4" />
                        </video>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Финальное видео */}
          {project.segments.some(s => s.status === 'completed') && (
            <div className="border rounded-lg p-4">
              <h4 className="font-semibold mb-2">Финальная сборка</h4>
              
              {!project.final_video_url ? (
                <button
                  onClick={assembleVideo}
                  disabled={project.status === 'assembling'}
                  className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 disabled:opacity-50"
                >
                  {project.status === 'assembling' ? 'Собирается...' : 'Собрать финальное видео'}
                </button>
              ) : (
                <div>
                  <p className="text-green-600 mb-2">✅ Финальное видео готово!</p>
                  <video
                    controls
                    className="w-full max-w-md rounded"
                    style={{ height: '300px' }}
                  >
                    <source src={project.video_url!} type="video/mp4" />
                  </video>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="mt-4 text-red-600 text-sm bg-red-50 p-3 rounded">
          {error}
        </div>
      )}
    </div>
  );
};
```

### 5. 🔐 ProtectedRoute - Защищенные маршруты

```tsx
// src/components/ProtectedRoute.tsx
import React from 'react';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  fallback 
}) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!user) {
    return fallback || (
      <div className="text-center p-8">
        <h2 className="text-xl font-semibold mb-4">Требуется авторизация</h2>
        <p className="text-gray-600">Пожалуйста, войдите в систему для продолжения</p>
      </div>
    );
  }

  return <>{children}</>;
};
```

### 6. 🏠 Dashboard - Главная страница

```tsx
// src/components/Dashboard.tsx
import React, { useState } from 'react';
import { AvatarCreator } from './AvatarCreator';
import { AvatarList } from './AvatarList';
import { AnimationStudio } from './AnimationStudio';
import { useAuth } from '../contexts/AuthContext';

interface Avatar {
  avatar_id: string;
  image_url: string;
  prompt: string;
  status: string;
  user_id: string;
  created_at: string;
}

export const Dashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const [selectedAvatar, setSelectedAvatar] = useState<Avatar | null>(null);
  const [activeTab, setActiveTab] = useState<'create' | 'list' | 'animate'>('create');

  const handleAvatarCreated = (avatar: Avatar) => {
    setActiveTab('list');
  };

  const handleAvatarSelect = (avatar: Avatar) => {
    setSelectedAvatar(avatar);
    setActiveTab('animate');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <h1 className="text-xl font-bold text-gray-900">ToonzyAI Studio</h1>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                Привет, {user?.username}!
              </span>
              <button
                onClick={logout}
                className="text-sm text-red-600 hover:text-red-700"
              >
                Выйти
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('create')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'create'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Создать аватар
            </button>
            <button
              onClick={() => setActiveTab('list')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'list'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Мои аватары
            </button>
            {selectedAvatar && (
              <button
                onClick={() => setActiveTab('animate')}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'animate'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Анимация
              </button>
            )}
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'create' && (
          <AvatarCreator onAvatarCreated={handleAvatarCreated} />
        )}
        
        {activeTab === 'list' && (
          <AvatarList onAvatarSelect={handleAvatarSelect} />
        )}
        
        {activeTab === 'animate' && selectedAvatar && (
          <div>
            <div className="mb-4 p-4 bg-blue-50 rounded-lg">
              <h3 className="font-semibold">Выбранный аватар:</h3>
              <div className="flex items-center space-x-4 mt-2">
                <img
                  src={selectedAvatar.image_url}
                  alt={selectedAvatar.prompt}
                  className="w-16 h-16 rounded object-cover"
                />
                <div>
                  <p className="text-sm">{selectedAvatar.prompt}</p>
                  <p className="text-xs text-gray-500">
                    {new Date(selectedAvatar.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedAvatar(null)}
                  className="text-sm text-blue-600 hover:underline"
                >
                  Выбрать другой
                </button>
              </div>
            </div>
            <AnimationStudio avatarId={selectedAvatar.avatar_id} />
          </div>
        )}
      </main>
    </div>
  );
};
```

### 7. 📱 App - Главный компонент приложения

```tsx
// src/App.tsx
import React from 'react';
import { AuthProvider } from './contexts/AuthContext';
import { LoginForm } from './components/LoginForm';
import { Dashboard } from './components/Dashboard';
import { ProtectedRoute } from './components/ProtectedRoute';

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <ProtectedRoute fallback={<LoginForm />}>
          <Dashboard />
        </ProtectedRoute>
      </div>
    </AuthProvider>
  );
}

export default App;
```

---

## 🎯 Использование

1. **Оберните приложение в `AuthProvider`**
2. **Используйте `ProtectedRoute` для защищенных страниц**
3. **Подключите компоненты в нужной последовательности**
4. **Настройте CSS (примеры используют Tailwind CSS)**

Эти компоненты предоставляют полный функционал для работы с ToonzyAI API! 