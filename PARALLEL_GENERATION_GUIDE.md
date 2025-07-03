# Parallel Video Generation Guide 🚀

## Overview

The ToonzyAI backend now supports **parallel generation of all video segments simultaneously**! This dramatically speeds up the video creation process and gives users complete control over their animations.

## Key Features

### ✨ **Parallel Processing**
- Generate **ALL segments at the same time**
- No more waiting for segment 1 to finish before starting segment 2
- **Independent generation** - each segment uses the original avatar

### 🎯 **Batch Operations**
- Set prompts for **all segments at once**
- Generate **all segments with one API call**
- **Consistent starting frame** for all segments

### ⚡ **Speed Improvements**
- **5x faster** for 5-segment videos (parallel vs sequential)
- **Predictable timing** - all segments finish around the same time
- **Better resource utilization** across Celery workers

## New Workflow

### 1. **Create Animation Project**
```bash
POST /api/v1/animations/
{
  "source_avatar_id": "avatar-uuid",
  "total_segments": 5,
  "animation_prompt": "General animation description"
}
```

### 2. **Set Prompts for All Segments** ✨ NEW
```bash
PUT /api/v1/animations/{project_id}/segments/prompts
{
  "prompts": [
    {
      "segment_number": 1,
      "segment_prompt": "A cat sitting peacefully on a windowsill"
    },
    {
      "segment_number": 2,
      "segment_prompt": "The cat stretching and yawning"
    },
    {
      "segment_number": 3,
      "segment_prompt": "The cat jumping down from the window"
    },
    {
      "segment_number": 4,
      "segment_prompt": "The cat walking across the room"
    },
    {
      "segment_number": 5,
      "segment_prompt": "The cat curling up in a sunny spot"
    }
  ]
}
```

### 3. **Generate All Segments in Parallel** 🚀 NEW
```bash
POST /api/v1/animations/{project_id}/segments/generate-all
{
  "force_regenerate": false
}
```

### 4. **Monitor Progress**
```bash
GET /api/v1/animations/{project_id}
```

### 5. **Assemble Final Video**
```bash
POST /api/v1/animations/{project_id}/assemble
```

## API Endpoints

### Batch Prompt Setting

**`PUT /api/v1/animations/{project_id}/segments/prompts`**

Sets prompts for multiple segments at once.

**Request Body:**
```json
{
  "prompts": [
    {
      "segment_number": 1,
      "segment_prompt": "Segment 1 description"
    },
    {
      "segment_number": 2,
      "segment_prompt": "Segment 2 description"
    }
  ]
}
```

**Response:**
```json
{
  "message": "Successfully updated prompts for 2 segments",
  "project_id": "project-uuid",
  "updated_segments": [
    {
      "segment_number": 1,
      "prompt": "Segment 1 description",
      "status": "pending"
    }
  ],
  "next_step": "Use /generate-all endpoint to start parallel generation"
}
```

### Parallel Generation

**`POST /api/v1/animations/{project_id}/segments/generate-all`**

Starts generation of all segments simultaneously.

**Request Body:**
```json
{
  "force_regenerate": false  // Optional: regenerate completed segments
}
```

**Response:**
```json
{
  "message": "🚀 Started parallel generation for 5 segments!",
  "project_id": "project-uuid",
  "total_segments": 5,
  "segments_started": 5,
  "task_ids": ["task1", "task2", "task3", "task4", "task5"],
  "estimated_completion_time": "3-5 minutes per segment (all running in parallel)",
  "status": "generating"
}
```

## React/Frontend Integration

### useParallelGeneration Hook
```tsx
import { useState, useCallback } from 'react';

export const useParallelGeneration = () => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState<Record<number, number>>({});

  const setAllPrompts = useCallback(async (projectId: string, prompts: Array<{segment_number: number, segment_prompt: string}>) => {
    const response = await fetch(`/api/v1/animations/${projectId}/segments/prompts`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ prompts })
    });
    
    if (!response.ok) throw new Error('Failed to set prompts');
    return response.json();
  }, []);

  const generateAllSegments = useCallback(async (projectId: string, forceRegenerate = false) => {
    setIsGenerating(true);
    
    try {
      const response = await fetch(`/api/v1/animations/${projectId}/segments/generate-all`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ force_regenerate: forceRegenerate })
      });
      
      if (!response.ok) throw new Error('Failed to start generation');
      
      const result = await response.json();
      
      // Start polling for progress
      pollProgress(projectId);
      
      return result;
    } catch (error) {
      setIsGenerating(false);
      throw error;
    }
  }, []);

  const pollProgress = useCallback(async (projectId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/v1/animations/${projectId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        const project = await response.json();
        
        // Update progress for each segment
        const newProgress: Record<number, number> = {};
        let allCompleted = true;
        
        project.segments.forEach((segment: any) => {
          newProgress[segment.segment_number] = segment.progress || 0;
          if (segment.status !== 'completed') {
            allCompleted = false;
          }
        });
        
        setProgress(newProgress);
        
        if (allCompleted) {
          setIsGenerating(false);
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Failed to poll progress:', error);
      }
    }, 5000); // Poll every 5 seconds
  }, []);

  return {
    isGenerating,
    progress,
    setAllPrompts,
    generateAllSegments
  };
};
```

### Parallel Generation Component
```tsx
import React, { useState } from 'react';
import { useParallelGeneration } from './hooks/useParallelGeneration';

interface SegmentPrompt {
  segment_number: number;
  segment_prompt: string;
}

interface ParallelGenerationStudioProps {
  projectId: string;
  totalSegments: number;
}

export const ParallelGenerationStudio: React.FC<ParallelGenerationStudioProps> = ({
  projectId,
  totalSegments
}) => {
  const [prompts, setPrompts] = useState<SegmentPrompt[]>(
    Array.from({ length: totalSegments }, (_, i) => ({
      segment_number: i + 1,
      segment_prompt: ''
    }))
  );

  const {
    isGenerating,
    progress,
    setAllPrompts,
    generateAllSegments
  } = useParallelGeneration();

  const handlePromptChange = (segmentNumber: number, prompt: string) => {
    setPrompts(prev => prev.map(p => 
      p.segment_number === segmentNumber 
        ? { ...p, segment_prompt: prompt }
        : p
    ));
  };

  const handleSetAllPrompts = async () => {
    try {
      await setAllPrompts(projectId, prompts);
      alert('All prompts set successfully!');
    } catch (error) {
      alert('Failed to set prompts');
    }
  };

  const handleGenerateAll = async () => {
    try {
      await generateAllSegments(projectId);
      alert('Started parallel generation for all segments!');
    } catch (error) {
      alert('Failed to start generation');
    }
  };

  const allPromptsSet = prompts.every(p => p.segment_prompt.trim().length > 10);

  return (
    <div className="parallel-generation-studio">
      <h2>🚀 Parallel Video Generation</h2>
      
      {/* Prompt Setting Section */}
      <div className="prompts-section">
        <h3>1. Set Prompts for All Segments</h3>
        {prompts.map(prompt => (
          <div key={prompt.segment_number} className="segment-prompt">
            <label>Segment {prompt.segment_number}:</label>
            <textarea
              value={prompt.segment_prompt}
              onChange={(e) => handlePromptChange(prompt.segment_number, e.target.value)}
              placeholder={`Describe what happens in segment ${prompt.segment_number}...`}
              rows={3}
              className="w-full p-2 border rounded"
            />
          </div>
        ))}
        
        <button
          onClick={handleSetAllPrompts}
          disabled={!allPromptsSet}
          className="btn-primary"
        >
          💾 Set All Prompts
        </button>
      </div>

      {/* Generation Section */}
      <div className="generation-section">
        <h3>2. Generate All Segments in Parallel</h3>
        <button
          onClick={handleGenerateAll}
          disabled={!allPromptsSet || isGenerating}
          className="btn-success"
        >
          {isGenerating ? '🔄 Generating...' : '🚀 Generate All Segments'}
        </button>
      </div>

      {/* Progress Section */}
      {isGenerating && (
        <div className="progress-section">
          <h3>3. Generation Progress</h3>
          {Object.entries(progress).map(([segmentNumber, progressValue]) => (
            <div key={segmentNumber} className="segment-progress">
              <label>Segment {segmentNumber}:</label>
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ width: `${progressValue}%` }}
                />
              </div>
              <span>{progressValue}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

## Technical Implementation

### Independent Generation
```python
# OLD: Sequential generation with dependencies
async def _get_start_frame_url(segment_number):
    if segment_number == 1:
        return avatar_url
    else:
        # Wait for previous segment to complete
        return await extract_last_frame_from_previous_segment()

# NEW: Parallel generation with avatar as base
async def _get_start_frame_url(segment_number):
    # All segments use the same avatar as starting frame
    return await get_avatar_url_for_segment(segment_number)
```

### Celery Task Parallelization
```python
# Generate all segments in parallel
for segment in segments_to_generate:
    task = generate_segment_task.delay(project_id, segment.segment_number)
    task_ids.append(task.id)
```

## Advantages

### 🚀 **Speed**
- **5x faster** for typical 5-segment videos
- All segments complete around the same time
- Better utilization of available processing power

### 🎯 **User Control**
- Set all prompts before generation
- Clear overview of entire animation
- Easy to modify individual segments

### 🔄 **Reliability**
- No dependency chain failures
- Each segment is independent
- Failed segments don't block others

### 📊 **Monitoring**
- Real-time progress for all segments
- Clear status for each part
- Easy to identify issues

## Migration from Sequential

If you have existing code using the old sequential generation:

### Old Way:
```bash
# Generate segments one by one
POST /api/v1/animations/{project_id}/segments/1/generate
# Wait for completion...
POST /api/v1/animations/{project_id}/segments/2/generate
# Wait for completion...
```

### New Way:
```bash
# Set all prompts at once
PUT /api/v1/animations/{project_id}/segments/prompts

# Generate all segments in parallel
POST /api/v1/animations/{project_id}/segments/generate-all
```

## Best Practices

### 1. **Content Safety**
- Follow the [Content Filtering Guide](./CONTENT_FILTERING_GUIDE.md)
- Use safe prompts to avoid Google Veo filtering
- Test prompts individually if needed

### 2. **Prompt Quality**
- Make each segment prompt **descriptive and specific**
- Ensure prompts are **10-500 characters**
- Avoid contradictory or complex instructions

### 3. **Monitoring**
- Poll project status every **5-10 seconds**
- Handle individual segment failures gracefully
- Show progress for user feedback

### 4. **Error Handling**
```tsx
try {
  await generateAllSegments(projectId);
} catch (error) {
  if (error.message.includes('prompts')) {
    // Handle missing prompts
  } else if (error.message.includes('filtered')) {
    // Handle content filtering
  } else {
    // Handle other errors
  }
}
```

## Performance Considerations

### Resource Usage
- **CPU**: Higher initial load, but faster completion
- **Memory**: Parallel processes use more RAM
- **Google Veo**: Multiple concurrent requests (within limits)

### Optimization Tips
- **Celery Workers**: Ensure sufficient worker processes
- **Database**: Connection pooling for concurrent access
- **GCS**: Parallel uploads don't impact performance

## Conclusion

The parallel generation system transforms video creation from a slow, sequential process into a fast, efficient workflow. Users can now create complex animations in a fraction of the time while maintaining full creative control.

🚀 **Ready to use parallel generation in production!** 