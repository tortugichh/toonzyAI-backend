# Content Filtering Guide - Google Veo 2.0

## Overview

Google's Veo 2.0 model includes built-in Responsible AI (RAI) content filtering that automatically blocks content deemed inappropriate or unsafe. When content is filtered, you'll see errors like:

```
❌ Content was filtered by Google's AI safety system
```

## Common Filtering Triggers

### 1. **Violence & Weapons**
- Fighting, combat, weapons
- Blood, injury, medical procedures
- Military or war content

### 2. **Adult Content**
- Suggestive poses or clothing
- Romantic/intimate scenarios
- Age-inappropriate content

### 3. **Dangerous Activities**
- Extreme sports without safety gear
- Reckless driving or stunts
- Self-harm or risky behavior

### 4. **Controversial Topics**
- Political figures or events
- Religious imagery
- Copyrighted characters

### 5. **Technical Issues**
- Overly complex prompts
- Contradictory instructions
- Unrealistic physics

## Safe Prompt Guidelines

### ✅ Use These Patterns

```
# Nature & Landscapes
"A peaceful mountain landscape at sunrise"
"Gentle waves on a sandy beach"

# Animals & Wildlife
"A friendly dog playing in a park"
"Colorful birds flying through trees"

# Abstract & Artistic
"Colorful geometric shapes floating in space"
"Watercolor paint mixing on canvas"

# Technology & Objects
"A smartphone on a clean desk"
"Books stacked on a wooden table"

# People (General)
"A person walking through a library"
"Someone reading a book in a cafe"
```

### ❌ Avoid These Patterns

```
# Violence/Weapons
"Sword fighting scene"
"Explosion in the distance"

# Adult/Suggestive
"Romantic dinner date"
"Person in swimwear"

# Dangerous Activities
"Motorcycle racing at high speed"
"Person climbing without safety gear"

# Copyrighted Content
"Mickey Mouse character"
"Marvel superhero action"
```

## Troubleshooting Steps

### 1. **Simplify Your Prompt**
```bash
# Instead of:
"Epic battle scene with warriors fighting dragons in a burning castle"

# Try:
"Medieval castle on a hill during sunset"
```

### 2. **Remove Specific People/Characters**
```bash
# Instead of:
"Superman flying over New York City"

# Try:
"A figure in a red cape flying over a cityscape"
```

### 3. **Focus on Objects/Scenes**
```bash
# Instead of:
"Person doing extreme skateboard tricks"

# Try:
"Empty skateboard rolling down a hill"
```

### 4. **Test with Generic Content**
```bash
# Safe test prompts:
"A cat sitting on a windowsill"
"Rain drops on green leaves"
"A cup of coffee on a table"
```

## Error Handling in Your App

When content filtering occurs, the error message will include:
- **Filtered Count**: Number of outputs blocked
- **Filtered Reasons**: Specific policy violations (if provided)

### Example Error Response
```json
{
  "@type": "type.googleapis.com/google.cloud.aiplatform.v1.GenerateVideoResponse",
  "raiMediaFilteredCount": 1,
  "raiMediaFilteredReasons": ["VIOLENCE", "UNSAFE_CONTENT"]
}
```

### Handle in Frontend
```javascript
// Check for filtering errors
if (error.message.includes("filtered by Google's AI safety system")) {
  showUserMessage("Content was blocked for safety. Please try a different prompt.");
}
```

## Best Practices

### 1. **Prompt Validation**
- Pre-validate prompts against known filtering patterns
- Provide suggested alternatives for blocked content
- Use positive, descriptive language

### 2. **User Education**
- Explain content policies to users
- Provide example prompts that work well
- Show filtering reasons when available

### 3. **Fallback Strategies**
- Offer prompt suggestions when content is filtered
- Allow users to modify and retry prompts
- Implement retry logic with modified prompts

## Testing Your Prompts

Use this simple test to check if your prompts will be filtered:

```bash
# Test with curl
curl -X POST "http://localhost:8000/animation/projects/{project_id}/segments/{segment_number}/generate" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"segment_prompt": "Your test prompt here"}'
```

Monitor the Celery logs for filtering messages:
```bash
docker compose logs -f toonzyai-celery
```

## Getting Help

If you believe your content was incorrectly filtered:
1. Try rephrasing the prompt
2. Remove specific details that might trigger filters
3. Test with simpler, more general descriptions
4. Check Google's Vertex AI content policies for updates

Remember: Content filtering is designed to keep the platform safe and compliant with policies. Working within these guidelines ensures reliable video generation. 