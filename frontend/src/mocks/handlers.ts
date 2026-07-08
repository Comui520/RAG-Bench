import { http, HttpResponse } from 'msw';
import {
  MOCK_TASK_ID,
  mockUploadResponse,
  mockTaskStatusCompleted,
  mockGoldens,
  mockResults,
  mockHistory,
} from './fixtures';

const BASE = 'http://localhost:8000/api';

export const handlers = [
  http.post(`${BASE}/upload`, () =>
    HttpResponse.json(mockUploadResponse)
  ),

  http.post(`${BASE}/evaluate`, () =>
    HttpResponse.json({ task_id: MOCK_TASK_ID })
  ),

  http.get(`${BASE}/task/:taskId`, () =>
    HttpResponse.json(mockTaskStatusCompleted)
  ),

  http.get(`${BASE}/goldens/:taskId`, () =>
    HttpResponse.json(mockGoldens)
  ),

  http.post(`${BASE}/goldens/:taskId/confirm`, () =>
    HttpResponse.json({ status: 'confirmed' })
  ),

  http.get(`${BASE}/results/:taskId`, () =>
    HttpResponse.json(mockResults)
  ),

  http.get(`${BASE}/history`, () =>
    HttpResponse.json(mockHistory)
  ),
];
