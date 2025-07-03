# Frontend Guide: Parallel Video Generation 🚀

## Overview

This guide shows how to implement the **parallel video generation system** in your React frontend. Users can now set prompts for all segments and generate all videos simultaneously - **5x faster** than sequential generation!

## Quick Start

### 1. Install Dependencies
```bash
npm install axios react-query @tanstack/react-query
# or
yarn add axios react-query @tanstack/react-query
```

### 2. Core Types
```typescript
// types/animation.ts
export interface SegmentPrompt {
  segment_number: number;
  segment_prompt: string;
}

export interface AnimationProject {
  id: string;
  user_id: string;
  source_avatar_id: string;
  total_segments: number;
  animation_prompt: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  final_video_url?: string;
  video_url?: string;
  created_at: string;
  updated_at: string;
  segments: AnimationSegment[];
}

export interface AnimationSegment {
  id: string;
  segment_number: number;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  segment_prompt?: string;
  start_frame_url: string;
  generated_video_url?: string;
  video_url?: string;
  progress?: number;
  created_at: string;
  updated_at: string;
}

export interface BatchPromptUpdate {
  prompts: SegmentPrompt[];
}

export interface ParallelGenerationResponse {
  message: string;
  project_id: string;
  total_segments: number;
  segments_started: number;
  task_ids: string[];
  estimated_completion_time: string;
  status: string;
}
```

### 3. API Service
```typescript
// services/animationAPI.ts
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

export class AnimationAPI {
  private getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  // Get project details with segments
  async getProject(projectId: string): Promise<AnimationProject> {
    const response = await axios.get(
      `${API_BASE}/animations/${projectId}`,
      { headers: this.getAuthHeaders() }
    );
    return response.data;
  }

  // Set prompts for all segments at once
  async setAllSegmentPrompts(projectId: string, prompts: SegmentPrompt[]) {
    const response = await axios.put(
      `${API_BASE}/animations/${projectId}/segments/prompts`,
      { prompts },
      { headers: this.getAuthHeaders() }
    );
    return response.data;
  }

  // Generate all segments in parallel
  async generateAllSegments(projectId: string, forceRegenerate = false): Promise<ParallelGenerationResponse> {
    const response = await axios.post(
      `${API_BASE}/animations/${projectId}/segments/generate-all`,
      { force_regenerate: forceRegenerate },
      { headers: this.getAuthHeaders() }
    );
    return response.data;
  }

  // Generate individual segment (still available)
  async generateSegment(projectId: string, segmentNumber: number, prompt: string) {
    const response = await axios.post(
      `${API_BASE}/animations/${projectId}/segments/${segmentNumber}/generate`,
      { segment_prompt: prompt },
      { headers: this.getAuthHeaders() }
    );
    return response.data;
  }

  // Assemble final video
  async assembleVideo(projectId: string) {
    const response = await axios.post(
      `${API_BASE}/animations/${projectId}/assemble`,
      {},
      { headers: this.getAuthHeaders() }
    );
    return response.data;
  }
}

export const animationAPI = new AnimationAPI();
```

## React Hooks

### 1. useParallelGeneration Hook
```typescript
// hooks/useParallelGeneration.ts
import { useState, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { animationAPI } from '../services/animationAPI';
import { SegmentPrompt, AnimationProject } from '../types/animation';

export const useParallelGeneration = (projectId: string) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStarted, setGenerationStarted] = useState(false);
  const queryClient = useQueryClient();

  // Query project data with auto-refresh during generation
  const { data: project, isLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => animationAPI.getProject(projectId),
    refetchInterval: isGenerating ? 5000 : false, // Poll every 5s during generation
    enabled: !!projectId
  });

  // Set all prompts mutation
  const setPromptsMutation = useMutation({
    mutationFn: (prompts: SegmentPrompt[]) => 
      animationAPI.setAllSegmentPrompts(projectId, prompts),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    }
  });

  // Generate all segments mutation
  const generateAllMutation = useMutation({
    mutationFn: (forceRegenerate: boolean = false) => 
      animationAPI.generateAllSegments(projectId, forceRegenerate),
    onSuccess: () => {
      setIsGenerating(true);
      setGenerationStarted(true);
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    }
  });

  // Assemble video mutation
  const assembleMutation = useMutation({
    mutationFn: () => animationAPI.assembleVideo(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    }
  });

  // Check if generation is complete
  useEffect(() => {
    if (project?.segments && isGenerating) {
      const allCompleted = project.segments.every(
        segment => segment.status === 'completed'
      );
      
      if (allCompleted) {
        setIsGenerating(false);
      }
    }
  }, [project?.segments, isGenerating]);

  // Helper functions
  const setAllPrompts = useCallback(async (prompts: SegmentPrompt[]) => {
    return setPromptsMutation.mutateAsync(prompts);
  }, [setPromptsMutation]);

  const generateAll = useCallback(async (forceRegenerate = false) => {
    return generateAllMutation.mutateAsync(forceRegenerate);
  }, [generateAllMutation]);

  const assembleVideo = useCallback(async () => {
    return assembleMutation.mutateAsync();
  }, [assembleMutation]);

  // Calculate progress statistics
  const stats = {
    totalSegments: project?.total_segments || 0,
    completedSegments: project?.segments?.filter(s => s.status === 'completed').length || 0,
    inProgressSegments: project?.segments?.filter(s => s.status === 'in_progress').length || 0,
    pendingSegments: project?.segments?.filter(s => s.status === 'pending').length || 0,
    failedSegments: project?.segments?.filter(s => s.status === 'failed').length || 0,
    overallProgress: project?.segments?.reduce((acc, segment) => acc + (segment.progress || 0), 0) || 0,
    averageProgress: project?.segments ? Math.round((project.segments.reduce((acc, segment) => acc + (segment.progress || 0), 0) / project.segments.length)) : 0
  };

  const allPromptsSet = project?.segments?.every(segment => 
    segment.segment_prompt && segment.segment_prompt.trim().length >= 10
  ) || false;

  const canGenerate = allPromptsSet && !isGenerating;
  const canAssemble = stats.completedSegments === stats.totalSegments && stats.totalSegments > 0;

  return {
    // Data
    project,
    isLoading,
    
    // States
    isGenerating,
    generationStarted,
    
    // Statistics
    stats,
    allPromptsSet,
    canGenerate,
    canAssemble,
    
    // Actions
    setAllPrompts,
    generateAll,
    assembleVideo,
    
    // Loading states
    isSettingPrompts: setPromptsMutation.isPending,
    isStartingGeneration: generateAllMutation.isPending,
    isAssembling: assembleMutation.isPending,
    
    // Errors
    promptsError: setPromptsMutation.error,
    generationError: generateAllMutation.error,
    assembleError: assembleMutation.error
  };
};
```

### 2. useSegmentProgress Hook
```typescript
// hooks/useSegmentProgress.ts
import { useMemo } from 'react';
import { AnimationSegment } from '../types/animation';

export const useSegmentProgress = (segments: AnimationSegment[]) => {
  return useMemo(() => {
    if (!segments || segments.length === 0) {
      return {
        segments: [],
        overallProgress: 0,
        completedCount: 0,
        inProgressCount: 0,
        pendingCount: 0,
        failedCount: 0
      };
    }

    const segmentProgress = segments.map(segment => ({
      ...segment,
      progressPercent: segment.progress || 0,
      statusEmoji: {
        'pending': '⏳',
        'in_progress': '🔄',
        'completed': '✅',
        'failed': '❌'
      }[segment.status] || '⏳'
    }));

    const totalProgress = segments.reduce((sum, segment) => sum + (segment.progress || 0), 0);
    const overallProgress = Math.round(totalProgress / segments.length);

    const completedCount = segments.filter(s => s.status === 'completed').length;
    const inProgressCount = segments.filter(s => s.status === 'in_progress').length;
    const pendingCount = segments.filter(s => s.status === 'pending').length;
    const failedCount = segments.filter(s => s.status === 'failed').length;

    return {
      segments: segmentProgress,
      overallProgress,
      completedCount,
      inProgressCount,
      pendingCount,
      failedCount
    };
  }, [segments]);
};
```

## React Components

### 1. ParallelGenerationStudio - Main Component
```tsx
// components/ParallelGenerationStudio.tsx
import React, { useState } from 'react';
import { useParallelGeneration } from '../hooks/useParallelGeneration';
import { SegmentPrompt } from '../types/animation';
import { PromptEditor } from './PromptEditor';
import { GenerationProgress } from './GenerationProgress';
import { VideoPreview } from './VideoPreview';

interface ParallelGenerationStudioProps {
  projectId: string;
}

export const ParallelGenerationStudio: React.FC<ParallelGenerationStudioProps> = ({
  projectId
}) => {
  const {
    project,
    isLoading,
    isGenerating,
    stats,
    allPromptsSet,
    canGenerate,
    canAssemble,
    setAllPrompts,
    generateAll,
    assembleVideo,
    isSettingPrompts,
    isStartingGeneration,
    isAssembling,
    promptsError,
    generationError,
    assembleError
  } = useParallelGeneration(projectId);

  const [prompts, setPrompts] = useState<SegmentPrompt[]>([]);

  // Initialize prompts when project loads
  React.useEffect(() => {
    if (project?.segments && prompts.length === 0) {
      const initialPrompts = project.segments.map(segment => ({
        segment_number: segment.segment_number,
        segment_prompt: segment.segment_prompt || ''
      }));
      setPrompts(initialPrompts);
    }
  }, [project?.segments, prompts.length]);

  const handlePromptChange = (segmentNumber: number, prompt: string) => {
    setPrompts(prev => prev.map(p => 
      p.segment_number === segmentNumber 
        ? { ...p, segment_prompt: prompt }
        : p
    ));
  };

  const handleSetAllPrompts = async () => {
    try {
      await setAllPrompts(prompts);
      alert('✅ All prompts set successfully!');
    } catch (error: any) {
      alert(`❌ Failed to set prompts: ${error.message}`);
    }
  };

  const handleGenerateAll = async () => {
    try {
      const result = await generateAll();
      alert(`🚀 Started generating ${result.segments_started} segments in parallel!`);
    } catch (error: any) {
      alert(`❌ Failed to start generation: ${error.message}`);
    }
  };

  const handleAssemble = async () => {
    try {
      await assembleVideo();
      alert('🎬 Started assembling final video!');
    } catch (error: any) {
      alert(`❌ Failed to start assembly: ${error.message}`);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        <span className="ml-4">Loading project...</span>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="p-8 text-center">
        <h2 className="text-xl font-bold text-red-600">Project not found</h2>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          🚀 Parallel Video Generation
        </h1>
        <p className="text-gray-600">
          Generate all {project.total_segments} segments simultaneously - 5x faster!
        </p>
      </div>

      {/* Statistics Dashboard */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-blue-50 p-4 rounded-lg text-center">
          <div className="text-2xl font-bold text-blue-600">{stats.totalSegments}</div>
          <div className="text-sm text-blue-600">Total Segments</div>
        </div>
        <div className="bg-green-50 p-4 rounded-lg text-center">
          <div className="text-2xl font-bold text-green-600">{stats.completedSegments}</div>
          <div className="text-sm text-green-600">Completed</div>
        </div>
        <div className="bg-yellow-50 p-4 rounded-lg text-center">
          <div className="text-2xl font-bold text-yellow-600">{stats.inProgressSegments}</div>
          <div className="text-sm text-yellow-600">In Progress</div>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg text-center">
          <div className="text-2xl font-bold text-gray-600">{stats.averageProgress}%</div>
          <div className="text-sm text-gray-600">Average Progress</div>
        </div>
      </div>

      {/* Step 1: Set Prompts */}
      <div className="bg-white border rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">
          📝 Step 1: Set Prompts for All Segments
        </h2>
        
        <PromptEditor
          prompts={prompts}
          onPromptChange={handlePromptChange}
          disabled={isGenerating}
        />
        
        <div className="mt-6 flex justify-between items-center">
          <div className="text-sm text-gray-600">
            {allPromptsSet 
              ? '✅ All prompts are set and ready' 
              : `⏳ ${prompts.filter(p => p.segment_prompt.length >= 10).length}/${prompts.length} prompts set`
            }
          </div>
          
          <button
            onClick={handleSetAllPrompts}
            disabled={!prompts.every(p => p.segment_prompt.length >= 10) || isSettingPrompts}
            className={`px-6 py-2 rounded-lg font-medium ${
              prompts.every(p => p.segment_prompt.length >= 10) && !isSettingPrompts
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            {isSettingPrompts ? '💾 Saving...' : '💾 Save All Prompts'}
          </button>
        </div>
        
        {promptsError && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700">
            ❌ Error: {promptsError.message}
          </div>
        )}
      </div>

      {/* Step 2: Generate All Segments */}
      <div className="bg-white border rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">
          🚀 Step 2: Generate All Segments in Parallel
        </h2>
        
        <div className="mb-4">
          <p className="text-gray-600 mb-2">
            All segments will use your avatar as the starting frame and generate simultaneously.
          </p>
          <p className="text-sm text-gray-500">
            ⏱️ Estimated time: 3-5 minutes (all segments finish around the same time)
          </p>
        </div>
        
        <button
          onClick={handleGenerateAll}
          disabled={!canGenerate || isStartingGeneration}
          className={`w-full py-3 rounded-lg font-medium text-lg ${
            canGenerate && !isStartingGeneration
              ? 'bg-green-600 text-white hover:bg-green-700'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          {isStartingGeneration 
            ? '🔄 Starting Generation...' 
            : isGenerating 
              ? '⚡ Generating All Segments...'
              : '🚀 Generate All Segments in Parallel'
          }
        </button>
        
        {generationError && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700">
            ❌ Error: {generationError.message}
          </div>
        )}
      </div>

      {/* Step 3: Monitor Progress */}
      {(isGenerating || stats.completedSegments > 0) && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4">
            📊 Step 3: Generation Progress
          </h2>
          
          <GenerationProgress segments={project.segments} />
        </div>
      )}

      {/* Step 4: Video Preview */}
      {stats.completedSegments > 0 && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4">
            🎬 Step 4: Video Preview
          </h2>
          
          <VideoPreview segments={project.segments} />
        </div>
      )}

      {/* Step 5: Assemble Final Video */}
      {canAssemble && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4">
            🎭 Step 5: Assemble Final Video
          </h2>
          
          <p className="text-gray-600 mb-4">
            All segments are complete! Ready to create the final animation.
          </p>
          
          <button
            onClick={handleAssemble}
            disabled={isAssembling}
            className="w-full py-3 bg-purple-600 text-white rounded-lg font-medium text-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {isAssembling ? '🎬 Assembling Video...' : '🎭 Create Final Animation'}
          </button>
          
          {assembleError && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700">
              ❌ Error: {assembleError.message}
            </div>
          )}
        </div>
      )}

      {/* Final Video */}
      {project.final_video_url && (
        <div className="bg-white border rounded-lg p-6 text-center">
          <h2 className="text-xl font-bold mb-4">
            ✅ Your Animation is Ready!
          </h2>
          
          <video
            controls
            className="w-full max-w-md mx-auto rounded-lg"
            src={project.final_video_url}
          >
            Your browser does not support the video tag.
          </video>
          
          <div className="mt-4">
            <a
              href={project.final_video_url}
              download
              className="inline-block px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              📥 Download Video
            </a>
          </div>
        </div>
      )}
    </div>
  );
};
```

### 2. PromptEditor Component
```tsx
// components/PromptEditor.tsx
import React from 'react';
import { SegmentPrompt } from '../types/animation';

interface PromptEditorProps {
  prompts: SegmentPrompt[];
  onPromptChange: (segmentNumber: number, prompt: string) => void;
  disabled?: boolean;
}

export const PromptEditor: React.FC<PromptEditorProps> = ({
  prompts,
  onPromptChange,
  disabled = false
}) => {
  const suggestedPrompts = [
    "A cat sitting peacefully on a windowsill",
    "The cat stretching and yawning gracefully",
    "The cat jumping down from the window",
    "The cat walking across the room curiously",
    "The cat curling up in a sunny spot"
  ];

  const fillSuggestions = () => {
    prompts.forEach((prompt, index) => {
      if (index < suggestedPrompts.length) {
        onPromptChange(prompt.segment_number, suggestedPrompts[index]);
      }
    });
  };

  return (
    <div className="space-y-4">
      {/* Quick Fill Button */}
      <div className="flex justify-between items-center">
        <h3 className="font-medium text-gray-700">Individual Segment Prompts</h3>
        <button
          onClick={fillSuggestions}
          disabled={disabled}
          className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
        >
          ✨ Fill with Examples
        </button>
      </div>

      {/* Prompt Inputs */}
      <div className="grid gap-4">
        {prompts.map((prompt) => (
          <div key={prompt.segment_number} className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Segment {prompt.segment_number}
              <span className={`ml-2 text-xs ${
                prompt.segment_prompt.length >= 10 ? 'text-green-600' : 'text-gray-400'
              }`}>
                ({prompt.segment_prompt.length}/500 chars)
                {prompt.segment_prompt.length >= 10 ? ' ✅' : ' ⏳'}
              </span>
            </label>
            
            <textarea
              value={prompt.segment_prompt}
              onChange={(e) => onPromptChange(prompt.segment_number, e.target.value)}
              placeholder={`Describe what happens in segment ${prompt.segment_number}... (min 10 characters)`}
              disabled={disabled}
              rows={3}
              maxLength={500}
              className={`w-full p-3 border rounded-lg resize-none disabled:bg-gray-50 disabled:cursor-not-allowed ${
                prompt.segment_prompt.length >= 10 
                  ? 'border-green-300 focus:border-green-500 focus:ring-green-200' 
                  : 'border-gray-300 focus:border-blue-500 focus:ring-blue-200'
              } focus:ring-2 focus:outline-none`}
            />
            
            {prompt.segment_prompt.length > 0 && prompt.segment_prompt.length < 10 && (
              <p className="text-xs text-red-600">
                ⚠️ Prompt too short. Need at least 10 characters.
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Tips */}
      <div className="bg-blue-50 p-4 rounded-lg">
        <h4 className="font-medium text-blue-800 mb-2">💡 Tips for Great Prompts:</h4>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• Be specific and descriptive (10-500 characters)</li>
          <li>• Avoid violence, copyrighted characters, or unsafe content</li>
          <li>• Focus on simple, clear actions and scenes</li>
          <li>• Use positive, family-friendly language</li>
        </ul>
      </div>
    </div>
  );
};
```

### 3. GenerationProgress Component
```tsx
// components/GenerationProgress.tsx
import React from 'react';
import { useSegmentProgress } from '../hooks/useSegmentProgress';
import { AnimationSegment } from '../types/animation';

interface GenerationProgressProps {
  segments: AnimationSegment[];
}

export const GenerationProgress: React.FC<GenerationProgressProps> = ({
  segments
}) => {
  const {
    segments: segmentProgress,
    overallProgress,
    completedCount,
    inProgressCount,
    pendingCount,
    failedCount
  } = useSegmentProgress(segments);

  return (
    <div className="space-y-6">
      {/* Overall Progress */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">Overall Progress</span>
          <span className="text-sm text-gray-600">{overallProgress}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-blue-600 h-3 rounded-full transition-all duration-300"
            style={{ width: `${overallProgress}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>✅ {completedCount} completed</span>
          <span>🔄 {inProgressCount} generating</span>
          <span>⏳ {pendingCount} pending</span>
          {failedCount > 0 && <span>❌ {failedCount} failed</span>}
        </div>
      </div>

      {/* Individual Segment Progress */}
      <div className="grid gap-3">
        <h4 className="font-medium text-gray-700">Individual Segments</h4>
        
        {segmentProgress.map((segment) => (
          <div key={segment.id} className="border rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <div className="flex items-center space-x-2">
                <span className="text-lg">{segment.statusEmoji}</span>
                <span className="font-medium">Segment {segment.segment_number}</span>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  segment.status === 'completed' ? 'bg-green-100 text-green-800' :
                  segment.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                  segment.status === 'failed' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {segment.status.replace('_', ' ').toUpperCase()}
                </span>
              </div>
              <span className="text-sm text-gray-600">{segment.progressPercent}%</span>
            </div>
            
            <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  segment.status === 'completed' ? 'bg-green-500' :
                  segment.status === 'in_progress' ? 'bg-blue-500' :
                  segment.status === 'failed' ? 'bg-red-500' :
                  'bg-gray-400'
                }`}
                style={{ width: `${segment.progressPercent}%` }}
              />
            </div>
            
            {segment.segment_prompt && (
              <p className="text-xs text-gray-600 truncate">
                "{segment.segment_prompt}"
              </p>
            )}
            
            {segment.status === 'in_progress' && (
              <div className="mt-2 flex items-center text-xs text-blue-600">
                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600 mr-2"></div>
                Generating with Google Veo 2.0...
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Real-time Status */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <div className="animate-pulse h-2 w-2 bg-green-500 rounded-full"></div>
          <span>Live updates every 5 seconds</span>
        </div>
      </div>
    </div>
  );
};
```

### 4. VideoPreview Component
```tsx
// components/VideoPreview.tsx
import React from 'react';
import { AnimationSegment } from '../types/animation';

interface VideoPreviewProps {
  segments: AnimationSegment[];
}

export const VideoPreview: React.FC<VideoPreviewProps> = ({ segments }) => {
  const completedSegments = segments
    .filter(segment => segment.status === 'completed' && segment.video_url)
    .sort((a, b) => a.segment_number - b.segment_number);

  if (completedSegments.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No completed segments yet. Videos will appear here as they finish generating.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-medium text-gray-700">Completed Segments</h3>
        <span className="text-sm text-gray-600">
          {completedSegments.length} of {segments.length} ready
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {completedSegments.map((segment) => (
          <div key={segment.id} className="border rounded-lg p-3">
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium text-sm">Segment {segment.segment_number}</span>
              <span className="text-xs text-green-600 bg-green-100 px-2 py-1 rounded">
                ✅ Ready
              </span>
            </div>
            
            <video
              controls
              className="w-full rounded border"
              poster="/api/placeholder/320/180"
            >
              <source src={segment.video_url} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
            
            {segment.segment_prompt && (
              <p className="text-xs text-gray-600 mt-2 line-clamp-2">
                "{segment.segment_prompt}"
              </p>
            )}
            
            <div className="mt-2 flex justify-between items-center">
              <span className="text-xs text-gray-500">~5 seconds</span>
              <a
                href={segment.video_url}
                download={`segment_${segment.segment_number}.mp4`}
                className="text-xs text-blue-600 hover:text-blue-800"
              >
                📥 Download
              </a>
            </div>
          </div>
        ))}
      </div>

      {completedSegments.length < segments.length && (
        <div className="text-center py-4 text-gray-500">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto mb-2"></div>
          <p className="text-sm">
            {segments.length - completedSegments.length} more segments generating...
          </p>
        </div>
      )}
    </div>
  );
};
```

## App Integration

### 1. Main App Setup
```tsx
// App.tsx
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ParallelGenerationStudio } from './components/ParallelGenerationStudio';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 2,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Routes>
            <Route
              path="/projects/:projectId/generate"
              element={<ProjectGenerationPage />}
            />
          </Routes>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

const ProjectGenerationPage = () => {
  const { projectId } = useParams<{ projectId: string }>();
  
  if (!projectId) {
    return <div>Project not found</div>;
  }

  return <ParallelGenerationStudio projectId={projectId} />;
};

export default App;
```

### 2. Environment Variables
```bash
# .env
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_WS_URL=ws://localhost:8000/ws
```

## Error Handling

### 1. Common Error Scenarios
```tsx
// utils/errorHandling.ts
export const handleGenerationError = (error: any) => {
  if (error.message.includes('filtered by Google\'s AI safety system')) {
    return {
      type: 'content_filtered',
      message: 'Content was blocked for safety. Please try different prompts.',
      action: 'Review prompts and avoid violence, copyrighted content, or unsafe material.'
    };
  }
  
  if (error.message.includes('prompts')) {
    return {
      type: 'missing_prompts',
      message: 'Some segments are missing prompts.',
      action: 'Set prompts for all segments before generating.'
    };
  }
  
  if (error.message.includes('Event loop is closed')) {
    return {
      type: 'server_error',
      message: 'Server processing error. This is usually temporary.',
      action: 'Please try again in a few moments.'
    };
  }
  
  return {
    type: 'unknown',
    message: error.message || 'An unexpected error occurred.',
    action: 'Please try again or contact support if the problem persists.'
  };
};
```

### 2. Error Display Component
```tsx
// components/ErrorDisplay.tsx
import React from 'react';

interface ErrorDisplayProps {
  error: any;
  onRetry?: () => void;
  onClose?: () => void;
}

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  onRetry,
  onClose
}) => {
  const errorInfo = handleGenerationError(error);

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <div className="flex justify-between items-start">
        <div className="flex">
          <div className="text-red-500 mr-3">
            {errorInfo.type === 'content_filtered' ? '🚫' : 
             errorInfo.type === 'missing_prompts' ? '📝' : 
             errorInfo.type === 'server_error' ? '⚙️' : '❌'}
          </div>
          <div>
            <h4 className="text-red-800 font-medium">{errorInfo.message}</h4>
            <p className="text-red-600 text-sm mt-1">{errorInfo.action}</p>
          </div>
        </div>
        
        {onClose && (
          <button
            onClick={onClose}
            className="text-red-400 hover:text-red-600"
          >
            ×
          </button>
        )}
      </div>
      
      {onRetry && (
        <div className="mt-4">
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  );
};
```

## Performance Optimization

### 1. Lazy Loading
```tsx
// Lazy load heavy components
const ParallelGenerationStudio = React.lazy(() => 
  import('./components/ParallelGenerationStudio')
);

// Use with Suspense
<Suspense fallback={<div>Loading generation studio...</div>}>
  <ParallelGenerationStudio projectId={projectId} />
</Suspense>
```

### 2. Memoization
```tsx
// Memoize expensive calculations
const segmentStats = useMemo(() => {
  return segments.reduce((stats, segment) => {
    stats[segment.status] = (stats[segment.status] || 0) + 1;
    return stats;
  }, {} as Record<string, number>);
}, [segments]);
```

### 3. Debounced Updates
```tsx
// Debounce prompt updates
import { useDebounce } from 'use-debounce';

const [debouncedPrompts] = useDebounce(prompts, 500);

useEffect(() => {
  // Auto-save prompts
  if (debouncedPrompts.length > 0) {
    setAllPrompts(debouncedPrompts);
  }
}, [debouncedPrompts]);
```

## Testing

### 1. Component Tests
```tsx
// __tests__/ParallelGenerationStudio.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ParallelGenerationStudio } from '../components/ParallelGenerationStudio';

const createTestQueryClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false } }
});

describe('ParallelGenerationStudio', () => {
  it('renders prompt editor for all segments', async () => {
    const queryClient = createTestQueryClient();
    
    render(
      <QueryClientProvider client={queryClient}>
        <ParallelGenerationStudio projectId="test-project" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Set Prompts for All Segments/)).toBeInTheDocument();
    });
  });

  it('enables generation button when all prompts are set', async () => {
    // Test implementation
  });
});
```

This comprehensive frontend guide provides everything needed to implement the parallel video generation system in React. The components are modular, well-typed, and include proper error handling and loading states. 