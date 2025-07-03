import React, { useState } from 'react';

interface AnimationStudioDebuggerProps {
  projectId: string;
}

const AnimationStudioDebugger: React.FC<AnimationStudioDebuggerProps> = ({ projectId }) => {
  const [debugInfo, setDebugInfo] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const getToken = () => {
    // Adjust this based on how your app stores tokens
    return localStorage.getItem('token') || 
           localStorage.getItem('authToken') ||
           sessionStorage.getItem('token') ||
           document.cookie.split(';').find(row => row.startsWith('token='))?.split('=')[1];
  };

  const runConnectionTest = async () => {
    setIsRunning(true);
    setDebugInfo('🔧 Запускаю диагностику...\n');
    
    try {
      const token = getToken();
      
      // Step 1: Check if token exists
      if (!token) {
        setDebugInfo(prev => prev + '❌ Токен аутентификации не найден!\n' +
          'Решение: Войдите в систему заново.\n\n');
        setIsRunning(false);
        return;
      }
      
      setDebugInfo(prev => prev + `✅ Токен найден (длина: ${token.length} символов)\n`);
      
      // Step 2: Test authentication
      setDebugInfo(prev => prev + '🔍 Проверяю аутентификацию...\n');
      
      const authResponse = await fetch('/api/v1/animations/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      setDebugInfo(prev => prev + `📡 Статус аутентификации: ${authResponse.status}\n`);
      
      if (authResponse.status === 401) {
        setDebugInfo(prev => prev + '❌ Токен недействителен или истек!\n' +
          'Решение: Перелогиньтесь в систему.\n\n');
        setIsRunning(false);
        return;
      }
      
      if (authResponse.status !== 200) {
        const errorText = await authResponse.text();
        setDebugInfo(prev => prev + `❌ Ошибка аутентификации: ${errorText}\n\n`);
        setIsRunning(false);
        return;
      }
      
      setDebugInfo(prev => prev + '✅ Аутентификация прошла успешно\n\n');
      
      // Step 3: Check specific animation project
      setDebugInfo(prev => prev + `🔍 Проверяю анимационный проект: ${projectId}\n`);
      
      const projectResponse = await fetch(`/api/v1/animations/${projectId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      setDebugInfo(prev => prev + `📡 Статус проекта: ${projectResponse.status}\n`);
      
      if (projectResponse.status === 404) {
        setDebugInfo(prev => prev + '❌ Анимационный проект не найден в базе данных!\n' +
          'Возможные причины:\n' +
          '• Неверный ID проекта в URL\n' +
          '• Проект был удален\n' +
          '• Проект принадлежит другому пользователю\n\n');
        setIsRunning(false);
        return;
      }
      
      if (projectResponse.status !== 200) {
        const errorText = await projectResponse.text();
        setDebugInfo(prev => prev + `❌ Ошибка получения проекта: ${errorText}\n\n`);
        setIsRunning(false);
        return;
      }
      
      const projectData = await projectResponse.json();
      setDebugInfo(prev => prev + '✅ Анимационный проект найден\n');
      setDebugInfo(prev => prev + `📊 Статус: ${projectData.status}\n`);
      setDebugInfo(prev => prev + `📊 Всего сегментов: ${projectData.total_segments}\n`);
      setDebugInfo(prev => prev + `📊 Найдено сегментов в БД: ${projectData.segments.length}\n\n`);
      
      // Step 4: Check if segments exist
      if (projectData.segments.length === 0) {
        setDebugInfo(prev => prev + '⚠️ ПРОБЛЕМА НАЙДЕНА: Сегменты еще не созданы!\n' +
          'Это означает, что:\n' +
          '• Проект создан, но сегменты генерируются асинхронно\n' +
          '• Возможна ошибка в фоновой задаче создания сегментов\n' +
          '• Нужно подождать несколько секунд и обновить страницу\n\n' +
          'Решения:\n' +
          '1. Подождите 10-30 секунд и обновите страницу\n' +
          '2. Проверьте логи backend на наличие ошибок\n' +
          '3. Убедитесь что Celery worker запущен\n\n');
        setIsRunning(false);
        return;
      }
      
      // Step 5: Test specific segment endpoint
      setDebugInfo(prev => prev + '🔍 Тестирую endpoint обновления промпта сегмента...\n');
      
      const segmentResponse = await fetch(`/api/v1/animations/${projectId}/segments/1/prompt`, {
        method: 'PUT',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ segment_prompt: 'test-prompt-диагностика' })
      });
      
      setDebugInfo(prev => prev + `📡 Статус сегмента: ${segmentResponse.status}\n`);
      
      if (segmentResponse.status === 404) {
        const errorText = await segmentResponse.text();
        setDebugInfo(prev => prev + `❌ Сегмент не найден: ${errorText}\n` +
          'Это означает что endpoint работает, но конкретный сегмент отсутствует в БД.\n\n');
      } else if (segmentResponse.status === 200) {
        setDebugInfo(prev => prev + '✅ Endpoint сегментов работает корректно!\n' +
          'Проблема решена - API полностью функционален.\n\n');
      } else {
        const errorText = await segmentResponse.text();
        setDebugInfo(prev => prev + `⚠️ Неожиданный статус: ${errorText}\n\n`);
      }
      
    } catch (error) {
      setDebugInfo(prev => prev + `❌ Ошибка сети: ${error.message}\n` +
        'Возможные причины:\n' +
        '• Backend сервер не запущен\n' +
        '• Проблемы с proxy в dev server\n' +
        '• CORS ошибки\n\n');
    }
    
    setIsRunning(false);
  };

  const copyDebugInfo = () => {
    navigator.clipboard.writeText(debugInfo);
  };

  const testInConsole = () => {
    const token = getToken();
    const consoleCode = `
// 🔧 Тест API в консоли
const token = '${token}';
const projectId = '${projectId}';

console.log('🔍 Тестирую API...');

// Тест 1: Аутентификация
fetch('/api/v1/animations/', {
  headers: { 'Authorization': \`Bearer \${token}\` }
})
.then(response => {
  console.log('Auth status:', response.status);
  return response.json();
})
.then(data => console.log('Auth data:', data))
.catch(error => console.error('Auth error:', error));

// Тест 2: Конкретный проект
fetch(\`/api/v1/animations/\${projectId}\`, {
  headers: { 'Authorization': \`Bearer \${token}\` }
})
.then(response => {
  console.log('Project status:', response.status);
  return response.json();
})
.then(data => console.log('Project data:', data))
.catch(error => console.error('Project error:', error));

// Тест 3: Сегмент
fetch(\`/api/v1/animations/\${projectId}/segments/1\`, {
  headers: { 'Authorization': \`Bearer \${token}\` }
})
.then(response => {
  console.log('Segment status:', response.status);
  return response.text();
})
.then(text => console.log('Segment response:', text))
.catch(error => console.error('Segment error:', error));
`;
    
    console.log(consoleCode);
    navigator.clipboard.writeText(consoleCode);
    alert('Код скопирован в буфер обмена! Вставьте его в консоль браузера.');
  };

  return (
    <div className="animation-debugger" style={{
      border: '2px solid #orange',
      borderRadius: '8px',
      padding: '16px',
      margin: '16px 0',
      backgroundColor: '#fff3cd',
      fontFamily: 'monospace'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <h3 style={{ margin: 0, color: '#856404' }}>🔧 API Диагностика</h3>
        <button 
          onClick={() => setShowDetails(!showDetails)}
          style={{ 
            background: 'none', 
            border: '1px solid #856404', 
            borderRadius: '4px',
            padding: '4px 8px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          {showDetails ? 'Свернуть' : 'Развернуть'}
        </button>
      </div>
      
      {showDetails && (
        <>
          <div style={{ marginBottom: '12px', fontSize: '14px' }}>
            <strong>Project ID:</strong> {projectId}<br/>
            <strong>Token:</strong> {getToken() ? '✅ Есть' : '❌ Отсутствует'}
          </div>
          
          <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
            <button 
              onClick={runConnectionTest}
              disabled={isRunning}
              style={{
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '4px',
                cursor: isRunning ? 'not-allowed' : 'pointer',
                opacity: isRunning ? 0.6 : 1
              }}
            >
              {isRunning ? '⏳ Тестирую...' : '🔧 Запустить тест'}
            </button>
            
            <button 
              onClick={testInConsole}
              style={{
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              📋 Тест в консоли
            </button>
            
            {debugInfo && (
              <button 
                onClick={copyDebugInfo}
                style={{
                  backgroundColor: '#6c757d',
                  color: 'white',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                📋 Копировать лог
              </button>
            )}
          </div>
          
          {debugInfo && (
            <div style={{
              backgroundColor: '#f8f9fa',
              border: '1px solid #dee2e6',
              borderRadius: '4px',
              padding: '12px',
              fontSize: '12px',
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap',
              maxHeight: '300px',
              overflow: 'auto'
            }}>
              {debugInfo}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AnimationStudioDebugger; 