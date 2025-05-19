# Tutorial de Migração: Workflow → Job

Este documento fornece instruções passo a passo para migrar funcionalidades relacionadas a jobs do app `workflow` para o novo app `job`.

## Visão Geral

A migração envolve:
1. Mover arquivos de código (views, services, templates, estáticos)
2. Atualizar importações e referências
3. Testar cada componente após a migração
4. Resolver conflitos e dependências

## Pré-requisitos

1. App `job` já criado e adicionado a `INSTALLED_APPS` no settings.py
2. Modelos principais já migrados (com migrações de estado)
3. Acesso de escrita aos diretórios relevantes

## Processo de Migração

### Fase 1: Planejamento e Backup

1. **Criar um branch Git para a migração**
   ```bash
   git checkout -b migrate-job-module
   ```

2. **Fazer backup dos arquivos existentes**
   ```bash
   cp -r workflow/views workflow_views_backup
   cp -r workflow/services workflow_services_backup
   cp -r workflow/templates workflow_templates_backup
   cp -r workflow/static workflow_static_backup
   ```

### Fase 2: Migração de Serviços

Os serviços geralmente têm menos dependências, por isso começamos por eles.

1. **Migrar job_service.py**
   ```bash
   mkdir -p job/services
   cp workflow/services/job_service.py job/services/
   ```

2. **Atualizar importações no job_service.py**
   - Altere: `from workflow.models import ...` 
   - Para: `from job.models import ...`

3. **Migrar file_service.py**
   ```bash
   cp workflow/services/file_service.py job/services/
   ```

4. **Atualizar importações no file_service.py**
   - Altere: `from workflow.helpers import get_job_folder_path` 
   - Para: `from job.helpers import get_job_folder_path`
   
   Não se esqueça de criar o arquivo helpers.py no app job com a função get_job_folder_path.

5. **Migrar workshop_pdf_service.py**
   ```bash
   cp workflow/services/workshop_pdf_service.py job/services/
   ```

6. **Atualizar importações no workshop_pdf_service.py**
   - Ajuste: `from job.models import Job`

### Fase 3: Migração de Views

1. **Criar estrutura de diretórios**
   ```bash
   mkdir -p job/views
   ```

2. **Migrar arquivos de view relacionados a job**
   ```bash
   cp workflow/views/job_management_view.py job/views/management_view.py
   cp workflow/views/job_file_view.py job/views/file_view.py
   # Continue com os outros arquivos listados no mapeamento
   ```

3. **Atualizar importações em cada view**
   - Altere: `from workflow.models import ...` 
   - Para: `from job.models import ...`
   - Altere: `from workflow.services import ...` 
   - Para: `from job.services import ...`

4. **Verificar e atualizar URLs e templates**
   - Verifique referências de URL nas views
   - Atualize caminhos de template

### Fase 4: Migração de Templates

1. **Criar estrutura de diretórios para templates**
   ```bash
   mkdir -p job/templates/jobs
   mkdir -p job/templates/job_pricing
   ```

2. **Migrar templates**
   ```bash
   cp -r workflow/templates/jobs/* job/templates/jobs/
   cp -r workflow/templates/job_pricing/* job/templates/job_pricing/
   ```

3. **Atualizar referências nos templates**
   - Verifique e atualize caminhos nas tags `{% extends %}` e `{% include %}`
   - Atualize URLs em `{% url '...' %}`

### Fase 5: Migração de Arquivos Estáticos

1. **Criar estrutura para arquivos estáticos**
   ```bash
   mkdir -p job/static/js
   mkdir -p job/static/css
   ```

2. **Migrar arquivos JavaScript**
   ```bash
   cp -r workflow/static/js/job/* job/static/js/
   cp workflow/static/js/kanban.js job/static/js/
   ```

3. **Migrar arquivos CSS**
   ```bash
   cp workflow/static/css/job-cards.css job/static/css/
   cp workflow/static/css/edit_job.css job/static/css/
   cp workflow/static/css/kanban.css job/static/css/
   cp workflow/static/css/kanban-enhanced.css job/static/css/
   ```

4. **Atualizar referências nos templates e JavaScript**
   - Ajuste os caminhos de `{% static '...' %}`
   - Atualize importações em arquivos JavaScript

### Fase 6: Migração de Management Commands

1. **Criar estrutura para management commands**
   ```bash
   mkdir -p job/management/commands
   ```

2. **Migrar o comando validate_jobs**
   ```bash
   cp workflow/management/commands/validate_jobs.py job/management/commands/
   ```

3. **Atualizar importações no comando**
   - Ajuste as importações para usar `job.models` em vez de `workflow.models`

### Fase 7: Atualização de URLs

1. **Adicionar URLs do job ao projeto**
   - Edite o arquivo `urls.py` principal para incluir as URLs do app job
   ```python
   # No urls.py do projeto
   urlpatterns = [
       # Outras URLs...
       path('job/', include('job.urls')),
   ]
   ```

2. **Criar arquivo de URLs para o app job**
   ```python
   # job/urls.py
   from django.urls import path
   from job.views import (
       management_view, file_view, file_upload, edit_view_ajax,
       assign_view, archive_view, workshop_view, 
       submit_quote_view, kanban_view
   )

   urlpatterns = [
       path('<uuid:job_id>/', management_view.job_detail, name='job_detail'),
       # Adicione as demais URLs conforme necessário
   ]
   ```

### Fase 8: Testes

1. **Executar testes de unidade**
   ```bash
   python manage.py test job
   ```

2. **Verificar integridade dos templates**
   ```bash
   python manage.py validate_templates
   ```

3. **Testar manualmente fluxos principais**
   - Criação de job
   - Edição de job
   - Upload de arquivos
   - Visualização no kanban

### Fase 9: Limpeza

1. **Remover código antigo progressivamente**
   - Após confirmar que a funcionalidade foi migrada com sucesso, remova o código do app workflow
   - Mantenha o código antigo comentado por um período antes de remover completamente

2. **Atualizar a documentação**
   - Atualize a documentação para refletir a nova estrutura
   - Crie ou atualize o README.md do app job

3. **Revisar e atualizar testes**
   - Certifique-se de que todos os testes foram atualizados para usar o novo módulo

## Considerações Importantes

### Dependências Circulares

- Preste atenção a possíveis dependências circulares, especialmente entre workflow e job
- Use injeção de dependência ou importações locais quando necessário

### Proxy Models

- Os modelos proxy já foram configurados. Certifique-se de que as views e serviços usem os modelos corretos
- Verifique se as consultas usam os modelos do app job e não do workflow

### APIs e Endpoints

- Mantenha a compatibilidade com endpoints existentes
- Considere implementar redirecionamentos temporários para novas URLs

### Permissões e Autenticação

- Certifique-se de que o sistema de permissões continue funcionando
- Verifique se os decoradores de permissão foram migrados corretamente

## Resolução de Problemas

### Templates não encontrados
- Verifique a configuração de `DIRS` em `TEMPLATES` no settings.py
- Certifique-se de que os caminhos estão corretos

### Erros de importação
- Verifique circular imports (importações circulares)
- Certifique-se de que todas as dependências foram migradas

### Erro 404 em URLs
- Verifique se o arquivo `urls.py` do app job está configurado corretamente
- Confirme que o namespace foi preservado, se aplicável

### Arquivos estáticos não encontrados
- Execute `python manage.py collectstatic`
- Verifique os caminhos de arquivos estáticos nos templates
