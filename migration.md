# Ordem de migração:

1. Models (migrar para novo app e transformar modelo antigo em proxy model. Não esquecer de adicionar db_table no Meta do novo modelo.)
2. Views (e serializers, caso existam)
3. Utils (se houver)
3. Forms
4. Urls
5. Admin
6. Templates
7. Static
8. Remover proxy models
