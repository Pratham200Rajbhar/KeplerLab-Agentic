You are a senior engineer performing a full codebase cleanup on KeplerLab (FastAPI backend + Next.js frontend).

TASK: Remove all dead/unnecessary code and rewrite remaining code to be clean and human-readable.

BACKEND — Remove:
- Entire `services/tts_provider/` and `services/yt_translation/` directories (only __pycache__ remains)
- Legacy wrappers: `process_material()`, `process_url_material()`, `process_text_material()` in material_service.py
- Unused imports across all route files: `ClearChatRequest`, `ALLOWED_MIME_TYPES`, `HTMLResponse`, `asyncio` in mindmap.py, `MindMapResponse`, top-level `load_material_text` in worker.py
- Dead functions: `gpu_session()` sync method in gpu_manager.py, `getExplainerStatus` in explainer.js
- Dead dependencies from requirements.txt: `SQLAlchemy[asyncio]`, `asyncpg`, `redis` (not used anywhere — Prisma is exclusive ORM)
- Audit `selenium` + `webdriver-manager` usage; remove if Playwright covers all cases
- Audit `TTS` (Coqui) usage; remove if `edge-tts` is the only active TTS provider
- Duplicate `DifficultyLevel` enum defined in both flashcard.py and quiz.py — consolidate into `models/shared_enums.py`

FRONTEND — Remove:
- Entire `components/auth/` empty directory
- `QUICK_ACTIONS` and `API_FALLBACK_URL` constants from `lib/utils/constants.js`
- Chakra UI entirely: remove `@chakra-ui/react`, `@emotion/react`, `@emotion/styled`, `framer-motion` from package.json, delete `lib/chakra/provider.jsx`, remove ChakraProvider wrapper from `providers.jsx`
- Remove manual FOUC prevention `<script dangerouslySetInnerHTML>` in `layout.jsx` — next-themes handles this automatically
- Remove `parseSlashCommand` duplicate from `lib/utils/helpers.js` (canonical version is in `slashCommands.js`)
- `getExplainerStatus` export from `explainer.js`

REFACTOR FOR READABILITY:
- Consolidate all `API_BASE` declarations in `podcast.js`, `agent.js`, `FileViewerContent.jsx` to import from `lib/api/config.js`
- Move material CRUD endpoints out of `upload.py` into a new `routes/materials.py` file
- Apply router prefix directly on `APIRouter(prefix="/chat")` etc. in each route file instead of only in main.py
- Standardize all prompt loading through `prompts/__init__.py` with `@lru_cache` — eliminate raw `open()` calls in individual services
- Unify inconsistent Prisma client access: standardize on `from app.db.prisma_client import prisma` singleton everywhere, remove `get_prisma()` calls
- Standardize prompt placeholder syntax to `{{DOUBLE_BRACES}}` across all 12 prompt files

Do not change any business logic. Only remove dead code, fix imports, and improve naming/structure clarity.
