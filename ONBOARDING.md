# Plane Developer Onboarding Guide

> Complete guide for new full-stack developers joining the Plane project

**Welcome!** This guide will help you understand the entire Plane codebase - both frontend and backend - from the ground up.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Understanding the Monorepo](#understanding-the-monorepo)
3. [What Happens When You Run pnpm dev](#what-happens-when-you-run-pnpm-dev)
4. [Backend Structure (Django)](#backend-structure-django)
5. [Frontend Structure (React)](#frontend-structure-react)
6. [How Frontend & Backend Connect](#how-frontend--backend-connect)
7. [Step-by-Step Code Flow](#step-by-step-code-flow)
8. [Local Development Setup](#local-development-setup)
9. [Making Your First Change](#making-your-first-change)
10. [Common Confusions Explained](#common-confusions-explained)

---

## Project Overview

### What is Plane?

Plane is an **open-source project management tool** (like Jira, Linear, or Asana) built with:

**Frontend:**

- React + TypeScript
- React Router v7 (modern React framework)
- TailwindCSS for styling
- MobX for state management

**Backend:**

- Django REST Framework (Python)
- PostgreSQL database
- Redis for caching
- Celery for background tasks
- RabbitMQ for task queue

### Architecture at a Glance

```
┌─────────────────────────────────────────────────────┐
│                   USER'S BROWSER                    │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│              FRONTEND (4 React Apps)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │   Web    │ │  Admin   │ │  Space   │ │  Live  ││
│  │  :3000   │ │  :3001   │ │  :3002   │ │ :3100  ││
│  └──────────┘ └──────────┘ └──────────┘ └────────┘│
└─────────────────────────────────────────────────────┘
                        ↓ (HTTP API Calls)
┌─────────────────────────────────────────────────────┐
│            BACKEND (Django REST API)                │
│                  localhost:8000                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  Django Views → Business Logic → Database   │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│                   DATA LAYER                        │
│  ┌────────────┐ ┌────────┐ ┌──────────────────┐   │
│  │ PostgreSQL │ │ Redis  │ │ RabbitMQ+Celery │   │
│  │   :5432    │ │ :6379  │ │      :5672       │   │
│  └────────────┘ └────────┘ └──────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## Understanding the Monorepo

### What Even is a Monorepo?

**Instead of this (separate repos):**

```
plane-web/          (separate Git repo)
plane-admin/        (separate Git repo)
plane-api/          (separate Git repo)
plane-ui-library/   (separate Git repo)
```

**Plane uses this (single repo):**

```
plane/
  ├── apps/web/           (React app)
  ├── apps/admin/         (React app)
  ├── apps/api/           (Django API)
  ├── packages/ui/        (Shared components)
  └── ... everything together!
```

### Why Monorepo?

✅ **Share code easily**: One UI component used by all apps
✅ **Atomic changes**: Update a type once, everywhere gets updated
✅ **Simpler development**: One clone, one install, everything works
✅ **Better coordination**: See how frontend and backend work together

---

## What Happens When You Run `pnpm dev`

This is the **most confusing part** for new developers. Let me break it down step by step.

### The Files That Matter

```
plane/
├── package.json              # 👈 Root: Defines scripts for the entire project
├── pnpm-workspace.yaml       # 👈 Tells PNPM which folders are "packages"
├── turbo.json               # 👈 Tells Turborepo how to build/run everything
│
├── apps/
│   ├── web/
│   │   └── package.json     # 👈 Web app: Has its own dev script
│   ├── admin/
│   │   └── package.json     # 👈 Admin app: Has its own dev script
│   └── space/
│       └── package.json     # 👈 Space app: Has its own dev script
│
└── packages/
    ├── ui/
    │   └── package.json     # 👈 UI library: Needs to build before apps run
    └── types/
        └── package.json     # 👈 Types: Needs to build before apps run
```

### Step-by-Step: What Happens

**1. You type: `pnpm dev`**

```bash
$ pnpm dev
```

**2. PNPM looks at root `package.json`:**

```json
// plane/package.json
{
  "scripts": {
    "dev": "turbo run dev --concurrency=18"
  }
}
```

This says: "Run Turborepo's `dev` task with max 18 parallel processes"

**3. Turborepo reads `turbo.json`:**

```json
// plane/turbo.json
{
  "tasks": {
    "dev": {
      "dependsOn": ["^build"], // ← Build dependencies FIRST
      "persistent": true, // ← Keep running (don't exit)
      "cache": false
    }
  }
}
```

**Translation:** "Before running `dev`, build all packages that apps depend on"

**4. Turborepo reads `pnpm-workspace.yaml`:**

```yaml
packages:
  - apps/* # All folders in apps/ are packages
  - packages/* # All folders in packages/ are packages
```

**Translation:** "Scan `apps/` and `packages/` for package.json files"

**5. Turborepo discovers all packages:**

```
Found:
  - apps/web        (depends on @plane/ui, @plane/types, etc.)
  - apps/admin      (depends on @plane/ui, @plane/types, etc.)
  - apps/space      (depends on @plane/ui, @plane/types, etc.)
  - apps/live       (depends on @plane/editor, etc.)
  - packages/ui     (depends on @plane/types)
  - packages/types  (no dependencies)
  - packages/services (depends on @plane/types)
  ... 20+ packages total
```

**6. Turborepo builds the dependency graph:**

```
packages/types  ─────┐
                     ├──→ packages/ui ──┐
packages/constants ──┘                  ├──→ apps/web
                                        ├──→ apps/admin
packages/services ──────────────────────┘
```

**7. Turborepo builds packages in order:**

```bash
[1/3] Building packages/types...        ✓ (2s)
[2/3] Building packages/constants...    ✓ (1s)
[3/3] Building packages/ui...           ✓ (5s)  # ← Waits for types to finish
...
```

**8. Turborepo starts all apps in parallel:**

```bash
apps/web:dev: $ react-router dev --port 3000
apps/admin:dev: $ react-router dev --port 3001
apps/space:dev: $ react-router dev --port 3002
apps/live:dev: $ node server --port 3100

✓ Web app ready at http://localhost:3000
✓ Admin ready at http://localhost:3001
✓ Space ready at http://localhost:3002
✓ Live server ready at http://localhost:3100
```

**9. Turborepo watches for changes:**

```
Watching for changes...

[packages/ui/src/button.tsx changed]
  → Rebuilding @plane/ui...
  → Hot reloading apps/web
  → Hot reloading apps/admin
  → Hot reloading apps/space
```

### Visual Flow Diagram

```
YOU TYPE: pnpm dev
    ↓
Root package.json
    ↓
Executes: turbo run dev --concurrency=18
    ↓
Turborepo reads turbo.json
    ↓
Sees: dev task depends on "^build"
    ↓
Scans pnpm-workspace.yaml
    ↓
Finds all apps/* and packages/*
    ↓
Builds dependency graph
    ↓
Builds packages in order:
  ├─ @plane/types ✓
  ├─ @plane/constants ✓
  ├─ @plane/utils ✓ (after types)
  ├─ @plane/ui ✓ (after types, utils)
  └─ @plane/services ✓ (after types)
    ↓
Runs dev script in each app (parallel):
  ├─ apps/web → react-router dev --port 3000
  ├─ apps/admin → react-router dev --port 3001
  ├─ apps/space → react-router dev --port 3002
  └─ apps/live → node server --port 3100
    ↓
ALL APPS RUNNING! 🎉
```

---

## Backend Structure (Django)

### Directory Overview

```
apps/api/
├── manage.py                    # Django CLI entry point
├── plane/                       # Main Django project
│   ├── __init__.py
│   ├── settings/               # Settings split by environment
│   │   ├── common.py          # Shared settings
│   │   ├── local.py           # Development settings
│   │   ├── production.py      # Production settings
│   │   └── redis.py           # Redis configuration
│   ├── urls.py                # Root URL configuration
│   ├── wsgi.py                # WSGI server entry point
│   ├── celery.py              # Celery task queue config
│   │
│   ├── api/                   # API endpoints (DRF views)
│   │   ├── views/
│   │   │   ├── workspace.py   # Workspace CRUD
│   │   │   ├── project.py     # Project CRUD
│   │   │   ├── issue.py       # Issue CRUD
│   │   │   ├── cycle.py       # Cycle CRUD
│   │   │   └── ...
│   │   ├── serializers/       # DRF serializers
│   │   │   ├── workspace.py
│   │   │   ├── project.py
│   │   │   └── ...
│   │   └── urls.py           # API URL routing
│   │
│   ├── db/                    # Database models
│   │   ├── models/
│   │   │   ├── workspace.py   # Workspace model
│   │   │   ├── project.py     # Project model
│   │   │   ├── issue.py       # Issue model
│   │   │   └── ...
│   │   └── migrations/        # Database migrations
│   │
│   ├── bgtasks/              # Celery background tasks
│   ├── utils/                # Utility functions
│   ├── middleware/           # Custom middleware
│   └── license/              # License management
│
├── requirements.txt          # Python dependencies
├── .env                     # Environment variables
└── .venv/                   # Python virtual environment
```

### Django App Structure Explained

Django uses an **MVT pattern** (Model-View-Template), but we use DRF (Django REST Framework) so it's more like **MVS** (Model-View-Serializer):

#### 1. Models (Database Layer)

```python
# apps/api/plane/db/models/project.py
from django.db import models

class Project(models.Model):
    """Database table for projects"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "projects"
        ordering = ["-created_at"]
```

**This creates a table:**

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    workspace_id UUID REFERENCES workspaces(id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### 2. Serializers (Data Transformation)

```python
# apps/api/plane/api/serializers/project.py
from rest_framework import serializers
from plane.db.models import Project

class ProjectSerializer(serializers.ModelSerializer):
    """Converts Python objects ↔ JSON"""

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "workspace",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
```

**What it does:**

```python
# Python object → JSON
project = Project.objects.get(id="123")
serializer = ProjectSerializer(project)
json_data = serializer.data  # → {"id": "123", "name": "My Project", ...}

# JSON → Python object (create/update)
serializer = ProjectSerializer(data=request.data)
if serializer.is_valid():
    project = serializer.save()  # Creates database record
```

#### 3. Views (API Endpoints)

```python
# apps/api/plane/api/views/project.py
from rest_framework import viewsets
from plane.db.models import Project
from plane.api.serializers import ProjectSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoints:
    - GET    /api/workspaces/{slug}/projects/           → List projects
    - POST   /api/workspaces/{slug}/projects/           → Create project
    - GET    /api/workspaces/{slug}/projects/{id}/      → Get project
    - PUT    /api/workspaces/{slug}/projects/{id}/      → Update project
    - DELETE /api/workspaces/{slug}/projects/{id}/      → Delete project
    """
    serializer_class = ProjectSerializer

    def get_queryset(self):
        workspace_slug = self.kwargs["workspace_slug"]
        return Project.objects.filter(
            workspace__slug=workspace_slug
        ).select_related("workspace")

    def perform_create(self, serializer):
        workspace_slug = self.kwargs["workspace_slug"]
        workspace = Workspace.objects.get(slug=workspace_slug)
        serializer.save(workspace=workspace, created_by=self.request.user)
```

#### 4. URLs (Routing)

```python
# apps/api/plane/api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet

router = DefaultRouter()
router.register(
    r"workspaces/(?P<workspace_slug>[\w-]+)/projects",
    ProjectViewSet,
    basename="project"
)

urlpatterns = [
    path("api/", include(router.urls)),
]
```

**This creates routes:**

```
GET    /api/workspaces/my-workspace/projects/
POST   /api/workspaces/my-workspace/projects/
GET    /api/workspaces/my-workspace/projects/abc-123/
PUT    /api/workspaces/my-workspace/projects/abc-123/
DELETE /api/workspaces/my-workspace/projects/abc-123/
```

### Django Settings Structure

```python
# apps/api/plane/settings/common.py
# Base settings shared by all environments

INSTALLED_APPS = [
    "django.contrib.auth",
    "rest_framework",
    "plane.db",        # Our models
    "plane.api",       # Our API views
    # ...
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT"),
    }
}
```

```python
# apps/api/plane/settings/local.py
# Development-specific settings
from .common import *

DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

```python
# apps/api/plane/settings/production.py
# Production-specific settings
from .common import *

DEBUG = False
SECURE_SSL_REDIRECT = True
```

### How to Run Django Commands

```bash
cd apps/api
source .venv/bin/activate

# Load environment variables
set -a && source .env && set +a

# Run Django commands
python manage.py runserver 8000          # Start dev server
python manage.py migrate                  # Run migrations
python manage.py makemigrations          # Create new migrations
python manage.py createsuperuser         # Create admin user
python manage.py shell                   # Django Python shell
python manage.py dbshell                 # Database shell
```

---

## Frontend Structure (React)

### React Router v7 Basics

Plane uses **React Router v7** (formerly Remix) which is different from traditional React apps:

**Traditional React (Create React App):**

```
src/
├── App.tsx
├── pages/
│   ├── ProjectPage.tsx
│   └── IssuePage.tsx
└── components/
    └── Header.tsx
```

**React Router v7 (Plane):**

```
app/
├── root.tsx              # App shell
├── routes.ts             # Route definitions
└── routes/
    ├── project.tsx       # Handles /project route
    └── issue.tsx         # Handles /issue route
```

### Web App Structure

```
apps/web/
├── app/
│   ├── root.tsx                    # App root (wraps everything)
│   ├── layout.tsx                  # Main layout
│   ├── provider.tsx                # Context providers (auth, state, etc.)
│   ├── routes.ts                   # Route configuration
│   │
│   ├── routes/                     # Route handlers
│   │   ├── core/                   # Core routes
│   │   │   ├── workspace.tsx
│   │   │   ├── project.tsx
│   │   │   ├── issue.tsx
│   │   │   └── ...
│   │   └── extended/               # Extended features
│   │
│   ├── components/                 # React components
│   │   ├── workspace/
│   │   ├── project/
│   │   ├── issue/
│   │   └── ...
│   │
│   ├── store/                      # MobX stores
│   │   ├── workspace.store.ts
│   │   ├── project.store.ts
│   │   └── ...
│   │
│   └── types/                      # App-specific types
│
├── public/                         # Static assets
├── package.json
└── .env
```

### How Routing Works

```typescript
// apps/web/app/routes.ts
import { route } from "@react-router/dev/routes";

export default [
  route("/workspace/:workspaceSlug", "./routes/workspace.tsx"),
  route("/workspace/:workspaceSlug/projects/:projectId", "./routes/project.tsx"),
  route("/workspace/:workspaceSlug/projects/:projectId/issues/:issueId", "./routes/issue.tsx"),
];
```

**What this creates:**

```
/workspace/acme-corp                          → workspace.tsx
/workspace/acme-corp/projects/proj-123        → project.tsx
/workspace/acme-corp/projects/proj-123/issues/issue-456 → issue.tsx
```

### Route File Example

```typescript
// apps/web/app/routes/project.tsx
import { useParams } from "react-router";
import { useProject } from "@plane/hooks";
import { Button } from "@plane/ui";
import type { IProject } from "@plane/types";

export default function ProjectPage() {
  const { workspaceSlug, projectId } = useParams();
  const { fetchProject } = useProject();
  const [project, setProject] = useState<IProject | null>(null);

  useEffect(() => {
    async function loadProject() {
      const data = await fetchProject(workspaceSlug!, projectId!);
      setProject(data);
    }
    loadProject();
  }, [projectId]);

  if (!project) return <div>Loading...</div>;

  return (
    <div>
      <h1>{project.name}</h1>
      <p>{project.description}</p>
      <Button>Edit Project</Button>
    </div>
  );
}
```

---

## How Frontend & Backend Connect

### The Full Request Flow

**Example: User creates a new project**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER INTERACTION (Browser)                              │
│    User clicks "Create Project" button                     │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. REACT COMPONENT (apps/web/app/routes/workspace.tsx)     │
│    import { Button } from "@plane/ui";                     │
│    import { useProject } from "@plane/hooks";              │
│                                                             │
│    function WorkspacePage() {                              │
│      const { createProject } = useProject();               │
│                                                             │
│      const handleCreate = async () => {                    │
│        await createProject("my-workspace", {               │
│          name: "New Project",                              │
│          description: "Description"                        │
│        });                                                  │
│      };                                                     │
│                                                             │
│      return <Button onClick={handleCreate}>Create</Button>;│
│    }                                                        │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. REACT HOOK (packages/hooks/src/use-project.ts)          │
│    import { ProjectService } from "@plane/services";       │
│                                                             │
│    export const useProject = () => {                       │
│      const projectService = new ProjectService();          │
│                                                             │
│      const createProject = async (slug, data) => {         │
│        return await projectService.createProject(slug, data);│
│      };                                                     │
│                                                             │
│      return { createProject };                             │
│    };                                                       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. API SERVICE (packages/services/src/project.service.ts)  │
│    import axios from "axios";                              │
│    import type { IProject } from "@plane/types";           │
│                                                             │
│    export class ProjectService {                           │
│      async createProject(workspaceSlug: string,            │
│                          data: Partial<IProject>)          │
│                          : Promise<IProject> {             │
│        const response = await axios.post(                  │
│          `/api/workspaces/${workspaceSlug}/projects/`,    │
│          data                                              │
│        );                                                   │
│        return response.data;                               │
│      }                                                      │
│    }                                                        │
└─────────────────────────────────────────────────────────────┘
                        ↓
              HTTP POST Request
    POST http://localhost:8000/api/workspaces/my-workspace/projects/
    Body: { "name": "New Project", "description": "..." }
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. DJANGO URL ROUTER (apps/api/plane/api/urls.py)          │
│    Matches route to ProjectViewSet                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. DJANGO VIEW (apps/api/plane/api/views/project.py)       │
│    class ProjectViewSet(viewsets.ModelViewSet):            │
│      def create(self, request, workspace_slug):            │
│        serializer = ProjectSerializer(data=request.data)   │
│        if serializer.is_valid():                           │
│          project = serializer.save(                        │
│            workspace=get_workspace(workspace_slug)         │
│          )                                                  │
│          return Response(ProjectSerializer(project).data)  │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. DJANGO SERIALIZER                                        │
│    Validates data → Creates Project model → Saves to DB    │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. POSTGRESQL DATABASE                                      │
│    INSERT INTO projects (id, name, description, ...)       │
│    VALUES (...);                                            │
└─────────────────────────────────────────────────────────────┘
                        ↓
              Response flows back up:
    Django → Serializer → View → HTTP Response
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 9. FRONTEND RECEIVES RESPONSE                               │
│    Service → Hook → Component                              │
│    Component updates UI with new project                   │
└─────────────────────────────────────────────────────────────┘
```

### Code Example: Complete Flow

**Frontend (React):**

```typescript
// apps/web/app/routes/workspace.tsx
import { useProject } from "@plane/hooks";
import { Button } from "@plane/ui";

function WorkspacePage() {
  const { createProject } = useProject();

  const handleCreate = async () => {
    try {
      const newProject = await createProject("my-workspace", {
        name: "New Project",
        description: "My awesome project",
      });
      console.log("Created:", newProject);
      // UI updates automatically
    } catch (error) {
      console.error("Failed to create project:", error);
    }
  };

  return <Button onClick={handleCreate}>Create Project</Button>;
}
```

**Backend (Django):**

```python
# apps/api/plane/api/views/project.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from plane.db.models import Project, Workspace
from plane.api.serializers import ProjectSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer

    def create(self, request, workspace_slug):
        # Get workspace
        workspace = Workspace.objects.get(slug=workspace_slug)

        # Validate data
        serializer = ProjectSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        # Save to database
        project = serializer.save(
            workspace=workspace,
            created_by=request.user
        )

        # Return created project
        return Response(
            ProjectSerializer(project).data,
            status=status.HTTP_201_CREATED
        )
```

---

## Step-by-Step Code Flow

### Example: Loading Issues for a Project

**1. User navigates to:** `/workspace/acme/projects/proj-123/issues`

**2. React Router matches route:**

```typescript
// apps/web/app/routes.ts
route("/workspace/:workspaceSlug/projects/:projectId/issues", "./routes/issues.tsx");
```

**3. Issues component loads:**

```typescript
// apps/web/app/routes/issues.tsx
import { useParams } from "react-router";
import { useIssue } from "@plane/hooks";

export default function IssuesPage() {
  const { workspaceSlug, projectId } = useParams();
  const { fetchIssues } = useIssue();
  const [issues, setIssues] = useState([]);

  useEffect(() => {
    loadIssues();
  }, [projectId]);

  async function loadIssues() {
    const data = await fetchIssues(workspaceSlug, projectId);
    setIssues(data);
  }

  return (
    <div>
      {issues.map((issue) => (
        <IssueCard key={issue.id} issue={issue} />
      ))}
    </div>
  );
}
```

**4. Hook calls service:**

```typescript
// packages/hooks/src/use-issue.ts
import { IssueService } from "@plane/services";

export const useIssue = () => {
  const issueService = new IssueService();

  const fetchIssues = async (workspaceSlug, projectId) => {
    return await issueService.getIssues(workspaceSlug, projectId);
  };

  return { fetchIssues };
};
```

**5. Service makes HTTP request:**

```typescript
// packages/services/src/issue.service.ts
import { APIService } from "./api.service";
import type { IIssue } from "@plane/types";

export class IssueService extends APIService {
  async getIssues(workspaceSlug: string, projectId: string): Promise<IIssue[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/`);
  }
}
```

**6. Django receives request:**

```python
# apps/api/plane/api/views/issue.py
class IssueViewSet(viewsets.ModelViewSet):
    def list(self, request, workspace_slug, project_id):
        # Get issues from database
        issues = Issue.objects.filter(
            project_id=project_id,
            project__workspace__slug=workspace_slug
        ).select_related("project", "state", "assignees")

        # Serialize to JSON
        serializer = IssueSerializer(issues, many=True)

        # Return response
        return Response(serializer.data)
```

**7. Response returns to frontend:**

```
Django → JSON response → Service → Hook → Component → UI renders
```

---

## Local Development Setup

### Prerequisites

- **Node.js** 20+ (for frontend)
- **Python** 3.8+ (for backend)
- **PostgreSQL** 14+ (database)
- **Redis** 6.2+ (caching)
- **RabbitMQ** 3.x (optional, for background tasks)

### Quick Start

```bash
# 1. Clone repo
git clone https://github.com/makeplane/plane.git
cd plane

# 2. Make setup script executable and run it
chmod +x setup.sh
./setup.sh

# This will:
# - Copy .env.example files to .env
# - Generate Django SECRET_KEY
# - Install frontend dependencies (pnpm install)
```

### Backend Setup

```bash
# 1. Navigate to API directory
cd apps/api

# 2. Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Update .env with your database credentials
# Edit apps/api/.env:
#   POSTGRES_HOST="localhost"
#   POSTGRES_USER="postgres"
#   POSTGRES_PASSWORD="your-password"
#   DATABASE_URL=postgresql://postgres:your-password@localhost:5432/plane

# 5. Run migrations
set -a && source .env && set +a
python manage.py migrate

# 6. Create superuser (optional)
python manage.py createsuperuser

# 7. Start Django server
python manage.py runserver 8000
```

### Frontend Setup

```bash
# Already done by setup.sh, but if needed:
pnpm install

# Start all frontend apps
pnpm dev
```

### Verify Everything Works

Open these URLs:

- http://localhost:3000 - Web app
- http://localhost:3001/god-mode - Admin panel
- http://localhost:3002 - Space (public views)
- http://localhost:8000/api/ - Django API

---

## Making Your First Change

### Task: Add a "Priority" Badge to Project Cards

**1. Add type definition:**

```typescript
// packages/types/src/project.d.ts
export interface IProject {
  id: string;
  name: string;
  description: string;
  priority?: "high" | "medium" | "low"; // ← Add this
  // ... other fields
}
```

**2. Create UI component:**

```typescript
// packages/ui/src/components/priority-badge.tsx
interface PriorityBadgeProps {
  priority: "high" | "medium" | "low";
}

export const PriorityBadge = ({ priority }: PriorityBadgeProps) => {
  const colors = {
    high: "bg-red-500",
    medium: "bg-yellow-500",
    low: "bg-green-500",
  };

  return <span className={`px-2 py-1 rounded text-white ${colors[priority]}`}>{priority.toUpperCase()}</span>;
};
```

**3. Export from package:**

```typescript
// packages/ui/src/index.ts
export { PriorityBadge } from "./components/priority-badge";
```

**4. Use in app:**

```typescript
// apps/web/app/components/project-card.tsx
import { PriorityBadge } from "@plane/ui";
import type { IProject } from "@plane/types";

interface ProjectCardProps {
  project: IProject;
}

export const ProjectCard = ({ project }: ProjectCardProps) => {
  return (
    <div className="border rounded-lg p-4">
      <div className="flex justify-between items-center">
        <h3>{project.name}</h3>
        {project.priority && <PriorityBadge priority={project.priority} />}
      </div>
      <p>{project.description}</p>
    </div>
  );
};
```

**5. See changes:**

- Save files
- Turborepo rebuilds `@plane/ui`
- All apps using `ProjectCard` reload automatically
- Your badge appears! ✨

---

## Common Confusions Explained

### 1. "Why are there so many package.json files?"

Each folder in `apps/` and `packages/` is its own **package** with its own dependencies:

```
plane/
├── package.json              ← Root: Manages workspace
├── apps/
│   ├── web/
│   │   └── package.json     ← Web app dependencies
│   └── admin/
│       └── package.json     ← Admin app dependencies
└── packages/
    └── ui/
        └── package.json     ← UI package dependencies
```

This allows each package to have only the dependencies it needs.

### 2. "What's the difference between package.json scripts?"

```json
// Root package.json
{
  "scripts": {
    "dev": "turbo run dev"        // ← Runs dev in ALL packages
  }
}

// apps/web/package.json
{
  "scripts": {
    "dev": "react-router dev --port 3000"  // ← Specific to web app
  }
}
```

When you run `pnpm dev` at root, Turborepo runs each package's own `dev` script.

### 3. "What is workspace:\*?"

```json
{
  "dependencies": {
    "@plane/ui": "workspace:*" // ← Links to local packages/ui
  }
}
```

Instead of downloading from npm, PNPM links to the local folder. Changes in `packages/ui` immediately affect apps.

### 4. "How do I know which port each app uses?"

Check each app's package.json:

```json
// apps/web/package.json
{
  "scripts": {
    "dev": "react-router dev --port 3000" // ← Port is here
  }
}
```

### 5. "Why do I need to build packages before running apps?"

Packages like `@plane/ui` and `@plane/types` are written in TypeScript and need to be compiled to JavaScript before apps can use them:

```
TypeScript (.ts/.tsx) → Build → JavaScript (.js) → Used by apps
```

Turborepo handles this automatically via `"dependsOn": ["^build"]`.

### 6. "What's the difference between apps/web, apps/admin, apps/space?"

- **apps/web**: Main app for logged-in users (dashboards, projects, issues)
- **apps/admin**: Instance settings (only admins see this)
- **apps/space**: Public views (share with people without accounts)
- **apps/live**: WebSocket server (not a React app!)

They're separate apps that share code via `packages/`.

### 7. "How does Django connect to React?"

Django doesn't "connect" to React. They're completely separate:

```
React (Frontend)  →  HTTP Requests  →  Django (Backend API)
```

React makes API calls like any client would. Django doesn't know or care if it's React, mobile app, or curl.

---

## Next Steps

### Learning Path

1. **Week 1**: Understand the monorepo structure
2. **Week 2**: Explore backend (Django models, views, serializers)
3. **Week 3**: Explore frontend (React components, hooks, services)
4. **Week 4**: Make your first contribution!

### Recommended Reading Order

1. Read this file (you're here!)
2. Read `app_structure.md` for deep-dive on frontend
3. Read Django docs: https://docs.djangoproject.com/
4. Read React Router docs: https://reactrouter.com/

### Practice Tasks

1. Add a new field to Project model
2. Create a new API endpoint
3. Build a new UI component in `packages/ui`
4. Use your component in `apps/web`
5. Create a new route in web app

---

## Getting Help

- **Discord**: https://discord.com/invite/A92xrEGCge
- **GitHub Issues**: https://github.com/makeplane/plane/issues
- **Docs**: https://docs.plane.so/

---

**Welcome to Plane! Happy coding! 🚀**
