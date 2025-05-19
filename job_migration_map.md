# Mapeamento de Arquivos Relacionados a Job

Este documento mapeia todos os arquivos no app `workflow` que devem ser migrados para o novo app `job`.

## Views

| Arquivo Workflow | Função | Destino Job |
|------------------|--------|-------------|
| workflow/views/job_management_view.py | Gerenciamento de jobs | job/views/management_view.py |
| workflow/views/job_file_view.py | Gerenciamento de arquivos de job | job/views/file_view.py |
| workflow/views/job_file_upload.py | Upload de arquivos para jobs | job/views/file_upload.py |
| workflow/views/edit_job_view_ajax.py | Edição de jobs via AJAX | job/views/edit_view_ajax.py |
| workflow/views/assign_job_view.py | Atribuição de pessoas a jobs | job/views/assign_view.py |
| workflow/views/archive_completed_jobs_view.py | Arquivamento de jobs concluídos | job/views/archive_view.py |
| workflow/views/workshop_view.py | Inclui referências a Job | job/views/workshop_view.py |
| workflow/views/submit_quote_view.py | Submissão de cotações vinculadas a jobs | job/views/submit_quote_view.py |
| workflow/views/stock_view.py | Referência a Job e JobPricing | job/views/stock_view.py |
| workflow/views/purchase_order_view.py | Referência a Job | job/views/purchase_order_view.py |
| workflow/views/kanban_view.py | Visualização de jobs em kanban | job/views/kanban_view.py |

## Modelos

| Arquivo Workflow | Já Migrado Para | Observações |
|------------------|-----------------|-------------|
| workflow/models/job.py | job/models/job.py | Classe base Job |
| workflow/models/job_event.py | job/models/job_event.py | Eventos do job |
| workflow/models/job_file.py | job/models/job_file.py | Arquivos do job |
| workflow/models/job_pricing.py | job/models/job_pricing.py | Preços do job |

## Serviços

| Arquivo Workflow | Função | Destino Job |
|------------------|--------|-------------|
| workflow/services/job_service.py | Core do serviço de jobs | job/services/job_service.py |
| workflow/services/file_service.py | Gerenciamento de arquivos | job/services/file_service.py |
| workflow/services/workshop_pdf_service.py | Geração de PDFs para jobs | job/services/workshop_pdf_service.py |
| workflow/services/delivery_receipt_service.py | Contém referências a Job | job/services/delivery_receipt_service.py |
| workflow/services/kpi_service.py | Contém referência a ID de job específico | job/services/kpi_service.py |

## Templates

| Diretório/Arquivo Workflow | Destino Job |
|----------------------------|-------------|
| workflow/templates/jobs/ | job/templates/jobs/ |
| workflow/templates/job_pricing/ | job/templates/job_pricing/ |
| workflow/templates/reports/ | Contem referências a jobs (parcial) |
| workflow/templates/purchases/ | Contém referências a jobs (parcial) |
| workflow/templates/general/dashboard.html | Contém links para criar job |
| workflow/templates/base.html | Contém links para criar job |

## Arquivos Estáticos

| Arquivo Workflow | Função | Destino Job |
|------------------|--------|-------------|
| workflow/static/js/job/ | Diretório JavaScript relacionado a job | job/static/js/ |
| workflow/static/js/kanban.js | Visualização de jobs | job/static/js/kanban.js |
| workflow/static/css/job-cards.css | Estilo para cards de job | job/static/css/job-cards.css |
| workflow/static/css/edit_job.css | Estilo para edição de job | job/static/css/edit_job.css |
| workflow/static/css/kanban.css | Estilo para kanban de jobs | job/static/css/kanban.css |
| workflow/static/css/kanban-enhanced.css | Estilo avançado para kanban | job/static/css/kanban-enhanced.css |

## Management Commands

| Arquivo Workflow | Função | Destino Job |
|------------------|--------|-------------|
| workflow/management/commands/validate_jobs.py | Validação de jobs | job/management/commands/validate_jobs.py |

## Migrations

| Status | Observações |
|--------|-------------|
| ✅ Concluído | As migrações foram ajustadas para estado-apenas (state-only) |
| ✅ Concluído | Modelos proxy foram criados no app job |
