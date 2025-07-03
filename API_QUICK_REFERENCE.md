# 📚 ToonzyAI API Quick Reference

## 🚀 Base URL
```
http://localhost:8000/api/v1
```

## 🔐 Authentication
```bash
# Login
POST /auth/login
{
  "username": "string",
  "password": "string"
}

# Response
{
  "access_token": "jwt_token",
  "refresh_token": "jwt_token",
  "token_type": "bearer",
  "expires_in": 900
}
```

## 🎨 Avatars

### Create Avatar
```bash
POST /avatars/
Authorization: Bearer <token>
{
  "prompt": "A cute cartoon cat"
}
```

### Get Avatars
```bash
GET /avatars/?page=1&per_page=10
Authorization: Bearer <token>
```

### Get Avatar Image
```bash
GET /avatars/{avatar_id}/image
Authorization: Bearer <token>
# Returns PNG image
```

## 🎬 Animations

### Create Project
```bash
POST /animations/
Authorization: Bearer <token>
{
  "source_avatar_id": "uuid",
  "total_segments": 5,
  "animation_prompt": "Character doing actions"
}
```

### Get Project Status
```bash
GET /animations/{project_id}
Authorization: Bearer <token>
# Returns project with segments array
```

### Update Segment Prompt
```bash
PUT /animations/{project_id}/segments/{segment_number}/prompt
Authorization: Bearer <token>
{
  "segment_prompt": "Cat jumping over fence"
}
```

### Generate Segment
```bash
POST /animations/{project_id}/segments/{segment_number}/generate
Authorization: Bearer <token>
{}
```

### Get Segment Video
```bash
GET /animations/{project_id}/segments/{segment_number}/video
Authorization: Bearer <token>
# Returns MP4 video
```

### Assemble Final Video
```bash
POST /animations/{project_id}/assemble
Authorization: Bearer <token>
```

### Get Final Video
```bash
GET /animations/{project_id}/video
Authorization: Bearer <token>
# Returns assembled MP4 video
```

## 📊 Status Values

### Animation Status
- `pending` - Ожидает
- `in_progress` - Генерируется  
- `completed` - Готово
- `failed` - Ошибка
- `assembling` - Собирается

## 🚨 Common Errors

- `401` - Invalid/expired token → Use refresh endpoint
- `404` - Resource not found or no access
- `500` - Server error → Retry later

## ⚡ Workflow

1. **Login** → Get tokens
2. **Create Avatar** → Get avatar_id
3. **Create Animation Project** → Get project_id
4. **Wait for segments creation** (polling)
5. **Update segment prompts** (optional)
6. **Generate segments** → Monitor status
7. **Assemble final video**
8. **Download result**

## 🔄 Polling Example

```javascript
const pollProject = async (projectId) => {
  const response = await fetch(`/api/v1/animations/${projectId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const project = await response.json();
  
  // Check if need to continue polling
  const hasActive = project.segments.some(s => 
    s.status === 'pending' || s.status === 'in_progress'
  );
  
  if (hasActive) {
    setTimeout(() => pollProject(projectId), 5000);
  }
};
```

## 📖 Full Documentation
- **BACKEND_API_DOCUMENTATION.md** - Полная документация
- **REACT_COMPONENTS_EXAMPLES.md** - React компоненты
- **Swagger UI:** http://localhost:8000/docs 