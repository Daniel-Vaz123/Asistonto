# Configurar base de datos vectorial en Supabase

Esta guía explica cómo crear la base vectorial en Supabase (pgvector) y conectar el asistente para usar el cache de preguntas/respuestas en la nube en lugar de Chroma local.

---

## 1. Crear proyecto en Supabase

1. Entra en [supabase.com](https://supabase.com) e inicia sesión.
2. **New project**: elige organización, nombre del proyecto, contraseña de base de datos (guárdala) y región.
3. Espera a que el proyecto esté listo.

---

## 2. Activar la extensión pgvector

1. En el panel de Supabase: **Database** → **Extensions**.
2. Busca **vector** (pgvector).
3. Actívala con el botón **Enable**.

O desde **SQL Editor** ejecuta:

```sql
create extension if not exists vector;
```

---

## 3. Crear la tabla del cache Q&A

En **SQL Editor** → **New query**, pega y ejecuta:

```sql
-- Tabla para cache de preguntas/respuestas (mismo uso que Chroma, en la nube)
create table if not exists public.qa_cache (
  id uuid primary key default gen_random_uuid(),
  query_text text not null,
  response_text text not null,
  embedding vector(384) not null,
  created_at timestamptz default now()
);

-- Comentario: 384 = dimensión del modelo paraphrase-multilingual-MiniLM-L12-v2
comment on table public.qa_cache is 'Cache vectorial de Q&A para ahorrar créditos DeepSeek';
```

La dimensión **384** es la del modelo que usa el proyecto (`paraphrase-multilingual-MiniLM-L12-v2`). No la cambies si usas ese modelo.

---

## 4. Índice para búsqueda rápida por similitud

Para que las búsquedas “por vector más parecido” sean rápidas:

```sql
-- Índice HNSW para búsqueda por similitud coseno
create index if not exists qa_cache_embedding_idx
  on public.qa_cache
  using hnsw (embedding vector_cosine_ops);
```

---

## 5. Función para buscar la respuesta más similar

Así el código Python puede enviar el vector de la pregunta y recibir la fila más parecida:

```sql
-- Devuelve la fila más similar (menor distancia coseno) y la distancia
create or replace function public.match_qa_cache(
  query_embedding vector(384),
  match_count int default 1,
  max_distance float default 0.2
)
returns table (
  id uuid,
  query_text text,
  response_text text,
  distance float
)
language sql stable
as $$
  select
    qa_cache.id,
    qa_cache.query_text,
    qa_cache.response_text,
    (qa_cache.embedding <=> query_embedding) as distance
  from public.qa_cache
  where (qa_cache.embedding <=> query_embedding) <= max_distance
  order by qa_cache.embedding <=> query_embedding
  limit match_count;
$$;
```

- `<=>` en pgvector es **distancia coseno** (0 = idéntico, 2 = opuesto).
- `max_distance 0.2` equivale aproximadamente a similitud coseno ≥ 0.9 (porque similitud = 1 - distancia).

---

## 6. Permitir escritura en la tabla (RLS)

En Supabase las tablas nuevas tienen **Row Level Security (RLS)** activado y sin políticas, por eso los **INSERT** pueden fallar y no se guarda nada.

Ejecuta en **SQL Editor** uno de estos dos:

**Opción A – Desactivar RLS en esta tabla (recomendado para cache interno):**

```sql
alter table public.qa_cache disable row level security;
```

**Opción B – Mantener RLS y permitir todo al cliente (anon/service):**

```sql
alter table public.qa_cache enable row level security;
create policy "qa_cache_allow_all" on public.qa_cache
  for all using (true) with check (true);
```

Si usas la **service_role key** en `.env`, con la Opción A suele ser suficiente. Si usas la clave **anon (publishable)**, prueba primero la Opción A; si sigue fallando, usa la **service_role** en `SUPABASE_SERVICE_KEY`.

---

## 7. Permisos (clave API)

- **Project Settings** → **API**: copia **Project URL** y **service_role** (secret) para `SUPABASE_SERVICE_KEY` si la Opción A no basta con la clave anon.

---

## 8. Variables de entorno en tu proyecto

En el archivo `.env` del asistente añade:

```env
# Supabase - cache vectorial en la nube (opcional)
SUPABASE_URL=https://TU_PROYECTO.supabase.co
SUPABASE_SERVICE_KEY=eyJ...tu_service_role_key...
```

- **SUPABASE_URL**: en Supabase → **Project Settings** → **API** → **Project URL**.
- **SUPABASE_SERVICE_KEY**: en **API** → **Project API keys** → **service_role** (la clave secreta, no la anon). No la subas a git.

Para usar Supabase en lugar de Chroma, en `config.json`:

```json
"features": {
  "vector_cache_enabled": true,
  "vector_cache_backend": "supabase"
}
```

Si no pones `vector_cache_backend` o pones `"chroma"`, se seguirá usando Chroma local.

---

## 9. Resumen de pasos

| Paso | Dónde | Qué hacer |
|------|--------|-----------|
| 1 | Supabase Dashboard | Crear proyecto |
| 2 | Database → Extensions | Activar **vector** (pgvector) |
| 3 | SQL Editor | Ejecutar `create table qa_cache` |
| 4 | SQL Editor | Ejecutar `create index qa_cache_embedding_idx` |
| 5 | SQL Editor | Ejecutar `create function match_qa_cache` |
| 6 | SQL Editor | Ejecutar `alter table public.qa_cache disable row level security` (o política RLS) |
| 7 | .env | Añadir `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` |
| 8 | config.json | `vector_cache_backend`: `"supabase"` |

Cuando todo esté configurado, el asistente usará Supabase para buscar y guardar el cache de preguntas/respuestas en la base de datos en lugar de la carpeta local de Chroma.

---

## 10. Tabla de notas del usuario (solo en base de datos)

Las notas que creas con voz se guardan **solo en Supabase** (no en archivos locales). Crea la tabla `user_notes`:

En **SQL Editor** → **New query**, ejecuta:

```sql
-- Tabla para notas del usuario (voz o app)
create table if not exists public.user_notes (
  id uuid primary key default gen_random_uuid(),
  content text not null,
  source text default 'voice',
  created_at timestamptz default now()
);

comment on table public.user_notes is 'Notas del usuario guardadas por el asistente (solo en BD)';

-- Permitir que el asistente lea/escriba
alter table public.user_notes disable row level security;
```

Las mismas variables (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`) sirven para cache Q&A y para notas.
