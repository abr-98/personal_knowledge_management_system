# personal_knowledge_management_system

## API

The project now includes a layered FastAPI backend under `src/` with:

- domain models and repository contracts
- application services
- PostgreSQL repositories
- REST APIs for auth, chat threads/messages, records, workitems, and timelines
- a parallel MCP server for chatbot workflows

Run it with:

```bash
uvicorn src.main:app --reload
```

Run the MCP server with:

```bash
python -m src.mcp.server
```

The MCP layer exposes chatbot-ready tools for:

- user registration, login, and password change
- chat thread and message operations
- token usage logging
- record, workitem, and timeline CRUD
- aggregated chatbot context retrieval

Optional database environment variables:

- `PKMS_DB_HOST`
- `PKMS_DB_PORT`
- `PKMS_DB_NAME`
- `PKMS_DB_USER`
- `PKMS_DB_PASSWORD`