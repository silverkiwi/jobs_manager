# Quote Import Guide - Frontend Integration

## Overview

This guide provides complete instructions for implementing the frontend quote import functionality. **The backend is fully implemented and ready** with robust error handling and the critical duplicate revision bug fixed.

## Backend Status ✅

### Service Layer - IMPLEMENTED
- **Main Service**: `apps/job/services/import_quote_service.py`
- **Parser**: `apps/job/importers/quote_spreadsheet.py`
- **Diff Engine**: `apps/job/diff.py`

### API Views - IMPLEMENTED
- **Preview View**: `apps/job/views/quote_import_views.QuoteImportPreviewView`
- **Import View**: `apps/job/views/quote_import_views.QuoteImportView`
- **Status View**: `apps/job/views/quote_import_views.QuoteImportStatusView`

### URL Routes - IMPLEMENTED
- `POST /rest/jobs/{job_id}/quote/import/preview/` - Preview import
- `POST /rest/jobs/{job_id}/quote/import/` - Execute import
- `GET /rest/jobs/{job_id}/quote/status/` - Get current status

### Key Features Ready
- ✅ Hybrid revision calculation (prevents duplicate key errors)
- ✅ Comprehensive validation and error handling
- ✅ Preview functionality (no actual import)
- ✅ Detailed logging and change tracking
- ✅ Transaction safety
- ✅ Cross-platform temp file handling

---

## REST API Specification

### 1. Quote Import Preview
**Endpoint**: `POST /rest/jobs/{job_id}/quote/import/preview/`

**Purpose**: Preview import changes without actually importing

**Request**:
```typescript
// Multipart form data
Content-Type: multipart/form-data

file: File // .xlsx or .xls file
```

**Response**:
```typescript
interface PreviewResponse {
  job_id: string;
  job_name: string;
  preview: {
    success: boolean;
    validation_report: {
      issues: ValidationIssue[];
      warnings: string[];
      errors: string[];
    };
    can_proceed: boolean;
    draft_lines: DraftLine[];
    diff_preview: {
      additions_count: number;
      updates_count: number;
      deletions_count: number;
      total_changes: number;
      next_revision: number;
    } | null;
    error?: string;
  };
}

interface ValidationIssue {
  severity: 'error' | 'warning';
  message: string;
  line_number?: number;
  column?: string;
}

interface DraftLine {
  supplier: string;
  ref: string;
  description: string;
  quantity: number;
  unit_cost: number;
  total_cost: number;
  category?: string;
}
```

### 2. Quote Import Execute
**Endpoint**: `POST /rest/jobs/{job_id}/quote/import/`

**Purpose**: Actually perform the import

**Request**:
```typescript
// Multipart form data
Content-Type: multipart/form-data

file: File // .xlsx or .xls file
skip_validation?: string // 'true' or 'false' (default: 'false')
```

**Response Success**:
```typescript
interface ImportSuccessResponse {
  success: true;
  message: string;
  job_id: string;
  cost_set: {
    id: number;
    kind: 'quote';
    rev: number;
    created: string;
    summary: {
      cost: number;
      rev: number;
      hours: number;
    };
    cost_lines: CostLine[];
  };
  changes: {
    additions: number;
    updates: number;
    deletions: number;
  };
  validation?: {
    warnings_count: number;
    has_warnings: boolean;
  };
}
```

**Response Error**:
```typescript
interface ImportErrorResponse {
  success: false;
  error: string;
  job_id: string;
  validation?: {
    errors_count: number;
    critical_count: number;
    can_proceed: boolean;
  };
}
```

### 3. Quote Status
**Endpoint**: `GET /rest/jobs/{job_id}/quote/status/`

**Purpose**: Get current quote information

**Response**:
```typescript
interface StatusResponse {
  job_id: string;
  job_name: string;
  has_quote: boolean;
  quote?: {
    id: number;
    kind: 'quote';
    rev: number;
    created: string;
    summary: {
      cost: number;
      rev: number;
      hours: number;
    };
    cost_lines: CostLine[];
  };
  revision?: number;
}
```

---

## Frontend Implementation Guide

### 1. Service Layer (TypeScript)
**File**: `services/quoteImportService.ts`

```typescript
import { ApiClient } from './apiClient';

export interface QuoteImportPreviewResponse {
  job_id: string;
  job_name: string;
  preview: {
    success: boolean;
    validation_report: {
      issues: ValidationIssue[];
      warnings: string[];
      errors: string[];
    };
    can_proceed: boolean;
    draft_lines: DraftLine[];
    diff_preview: {
      additions_count: number;
      updates_count: number;
      deletions_count: number;
      total_changes: number;
      next_revision: number;
    } | null;
    error?: string;
  };
}

export interface QuoteImportResponse {
  success: boolean;
  message?: string;
  job_id: string;
  cost_set?: {
    id: number;
    kind: 'quote';
    rev: number;
    created: string;
    summary: {
      cost: number;
      rev: number;
      hours: number;
    };
    cost_lines: any[];
  };
  changes?: {
    additions: number;
    updates: number;
    deletions: number;
  };
  validation?: {
    warnings_count: number;
    has_warnings: boolean;
  };
  error?: string;
}

export interface ValidationIssue {
  severity: 'error' | 'warning';
  message: string;
  line_number?: number;
  column?: string;
}

export interface DraftLine {
  supplier: string;
  ref: string;
  description: string;
  quantity: number;
  unit_cost: number;
  total_cost: number;
  category?: string;
}

export class QuoteImportService {
  private apiClient: ApiClient;

  constructor(apiClient: ApiClient) {
    this.apiClient = apiClient;
  }

  async previewQuoteImport(jobId: string, file: File): Promise<QuoteImportPreviewResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return this.apiClient.post(
      `/rest/jobs/${jobId}/quote/import/preview/`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );
  }

  async importQuote(
    jobId: string,
    file: File,
    skipValidation: boolean = false
  ): Promise<QuoteImportResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (skipValidation) {
      formData.append('skip_validation', 'true');
    }

    return this.apiClient.post(
      `/rest/jobs/${jobId}/quote/import/`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );
  }

  async getQuoteStatus(jobId: string): Promise<any> {
    return this.apiClient.get(`/rest/jobs/${jobId}/quote/status/`);
  }
}
```

### 2. Vue Composable
**File**: `composables/useQuoteImport.ts`

```typescript
import { ref, computed } from 'vue';
import { QuoteImportService, QuoteImportPreviewResponse, QuoteImportResponse } from '@/services/quoteImportService';

export function useQuoteImport() {
  const isLoading = ref(false);
  const previewData = ref<QuoteImportPreviewResponse | null>(null);
  const importResult = ref<QuoteImportResponse | null>(null);
  const error = ref<string | null>(null);

  const canProceed = computed(() => {
    return previewData.value?.preview?.can_proceed === true;
  });

  const hasValidationIssues = computed(() => {
    return previewData.value?.preview?.validation_report?.issues?.length > 0;
  });

  const totalChanges = computed(() => {
    return previewData.value?.preview?.diff_preview?.total_changes || 0;
  });

  async function previewImport(jobId: string, file: File) {
    isLoading.value = true;
    error.value = null;

    try {
      const service = new QuoteImportService();
      previewData.value = await service.previewQuoteImport(jobId, file);
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Preview failed';
      previewData.value = null;
    } finally {
      isLoading.value = false;
    }
  }

  async function executeImport(jobId: string, file: File, skipValidation = false) {
    isLoading.value = true;
    error.value = null;

    try {
      const service = new QuoteImportService();
      importResult.value = await service.importQuote(jobId, file, skipValidation);
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Import failed';
      importResult.value = null;
    } finally {
      isLoading.value = false;
    }
  }

  function reset() {
    previewData.value = null;
    importResult.value = null;
    error.value = null;
    isLoading.value = false;
  }

  return {
    // State
    isLoading,
    previewData,
    importResult,
    error,

    // Computed
    canProceed,
    hasValidationIssues,
    totalChanges,

    // Actions
    previewImport,
    executeImport,
    reset
  };
}
```

### 3. Vue Component Example
**File**: `components/QuoteImportDialog.vue`

```vue
<template>
  <div class="quote-import-dialog">
    <div class="upload-section">
      <input
        ref="fileInput"
        type="file"
        accept=".xlsx,.xls"
        @change="handleFileSelect"
        class="file-input"
      />

      <button
        @click="handlePreview"
        :disabled="!selectedFile || isLoading"
        class="btn-preview"
      >
        {{ isLoading ? 'Loading...' : 'Preview Import' }}
      </button>
    </div>    <!-- Preview Results -->
    <div v-if="previewData" class="preview-section">
      <h3>Import Preview</h3>

      <!-- Validation Issues -->
      <div v-if="hasValidationIssues" class="validation-issues">
        <h4>Validation Issues</h4>
        <div
          v-for="issue in previewData.preview.validation_report.issues"
          :key="issue.message"
          :class="['issue', issue.severity]"
        >
          {{ issue.message }}
        </div>
      </div>

      <!-- Changes Summary -->
      <div v-if="previewData.preview.diff_preview" class="changes-summary">
        <h4>Changes Summary</h4>
        <div class="stats">
          <span class="stat">
            <span class="label">Next Revision:</span>
            <span class="value">{{ previewData.preview.diff_preview.next_revision }}</span>
          </span>
          <span class="stat">
            <span class="label">Total Changes:</span>
            <span class="value">{{ previewData.preview.diff_preview.total_changes }}</span>
          </span>
          <span class="stat additions">
            <span class="label">Additions:</span>
            <span class="value">{{ previewData.preview.diff_preview.additions_count }}</span>
          </span>
          <span class="stat updates">
            <span class="label">Updates:</span>
            <span class="value">{{ previewData.preview.diff_preview.updates_count }}</span>
          </span>
          <span class="stat deletions">
            <span class="label">Deletions:</span>
            <span class="value">{{ previewData.preview.diff_preview.deletions_count }}</span>
          </span>
        </div>
      </div>

      <!-- Import Actions -->
      <div class="import-actions">
        <button
          @click="handleImport"
          :disabled="!canProceed || isLoading"
          class="btn-import"
        >
          {{ isLoading ? 'Importing...' : 'Execute Import' }}
        </button>

        <button
          v-if="hasValidationIssues"
          @click="handleForceImport"
          :disabled="isLoading"
          class="btn-force-import"
        >
          Force Import (Skip Validation)
        </button>
      </div>
    </div>

    <!-- Import Result -->
    <div v-if="importResult" class="result-section">      <div v-if="importResult?.success" class="success">
        ✅ Import Successful!
        <div class="result-details">
          <p>Created CostSet: Rev {{ importResult.cost_set?.rev }}</p>
          <p>Total Cost: ${{ importResult.cost_set?.summary.cost }}</p>
          <p>Changes: +{{ importResult.changes?.additions || 0 }}
             ~{{ importResult.changes?.updates || 0 }}
             -{{ importResult.changes?.deletions || 0 }}</p>
        </div>
      </div>
      <div v-else-if="importResult" class="error">
        ❌ Import Failed: {{ importResult.error }}
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="error" class="error-section">
      ❌ Error: {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useQuoteImport } from '@/composables/useQuoteImport';

const props = defineProps<{
  jobId: string;
}>();

const emit = defineEmits<{
  success: [result: any];
  cancel: [];
}>();

const fileInput = ref<HTMLInputElement>();
const selectedFile = ref<File | null>(null);

const {
  isLoading,
  previewData,
  importResult,
  error,
  canProceed,
  hasValidationIssues,
  previewImport,
  executeImport,
  reset
} = useQuoteImport();

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  selectedFile.value = target.files?.[0] || null;
  reset(); // Clear previous results
}

async function handlePreview() {
  if (!selectedFile.value) return;
  await previewImport(props.jobId, selectedFile.value);
}

async function handleImport() {
  if (!selectedFile.value) return;
  await executeImport(props.jobId, selectedFile.value, false);
    if (importResult.value?.success) {
    emit('success', importResult.value);
  }
}

async function handleForceImport() {
  if (!selectedFile.value) return;
  await executeImport(props.jobId, selectedFile.value, true);

  if (importResult.value?.success) {
    emit('success', importResult.value);
  }
}
</script>

<style scoped>
.quote-import-dialog {
  padding: 20px;
  max-width: 600px;
}

.upload-section {
  margin-bottom: 20px;
}

.file-input {
  margin-bottom: 10px;
  width: 100%;
}

.btn-preview, .btn-import, .btn-force-import {
  padding: 10px 20px;
  margin-right: 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-preview {
  background: #007bff;
  color: white;
}

.btn-import {
  background: #28a745;
  color: white;
}

.btn-force-import {
  background: #ffc107;
  color: black;
}

.validation-issues {
  margin: 15px 0;
  padding: 15px;
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 4px;
}

.issue.error {
  color: #721c24;
}

.issue.warning {
  color: #856404;
}

.changes-summary {
  margin: 15px 0;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 4px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}

.stat {
  display: flex;
  justify-content: space-between;
  padding: 5px 10px;
  background: white;
  border-radius: 3px;
}

.stat.additions .value { color: #28a745; }
.stat.updates .value { color: #ffc107; }
.stat.deletions .value { color: #dc3545; }

.success {
  padding: 15px;
  background: #d4edda;
  color: #155724;
  border-radius: 4px;
}

.error {
  padding: 15px;
  background: #f8d7da;
  color: #721c24;
  border-radius: 4px;
}
</style>
```

---

## Testing

The backend includes a management command for testing:
```bash
python manage.py test_quote_import --preview-only  # Preview mode
python manage.py test_quote_import                  # Full import
```

## Integration Example

### Simple Usage in a Job Detail Page

```vue
<template>
  <div class="job-detail">
    <h1>{{ job.name }}</h1>

    <!-- Current Quote Status -->
    <div v-if="currentQuote" class="current-quote">
      <h3>Current Quote (Rev {{ currentQuote.rev }})</h3>
      <p>Cost: ${{ currentQuote.summary.cost }}</p>
      <p>Created: {{ formatDate(currentQuote.created) }}</p>
    </div>

    <!-- Import Button -->
    <button @click="showImportDialog = true" class="btn-import">
      Import New Quote
    </button>

    <!-- Import Dialog -->
    <QuoteImportDialog
      v-if="showImportDialog"
      :job-id="job.id"
      @success="handleImportSuccess"
      @cancel="showImportDialog = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { QuoteImportService } from '@/services/quoteImportService';
import QuoteImportDialog from '@/components/QuoteImportDialog.vue';

const props = defineProps<{
  job: any;
}>();

const showImportDialog = ref(false);
const currentQuote = ref(null);

onMounted(async () => {
  // Load current quote status
  const service = new QuoteImportService();
  try {
    const status = await service.getQuoteStatus(props.job.id);
    if (status.has_quote) {
      currentQuote.value = status.quote;
    }
  } catch (error) {
    console.error('Failed to load quote status:', error);
  }
});

function handleImportSuccess(result: any) {
  // Refresh quote data
  currentQuote.value = result.cost_set;
  showImportDialog.value = false;

  // Show success message
  console.log('Quote imported successfully!', result);
}

function formatDate(date: string) {
  return new Date(date).toLocaleDateString();
}
</script>
```

This provides a complete, production-ready implementation for quote importing with proper error handling, validation feedback, and a clean user experience following Vue.js best practices.
