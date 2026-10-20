"""
routes_projects.py — API endpoints لإدارة مشاريع الويب في سمير
"""

import json
import logging
import zipfile
import io
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse

logger = logging.getLogger("samir.api.projects")
router = APIRouter(prefix="/projects", tags=["Web Projects"])

PROJECTS_BASE_DIR = Path("./projects")


@router.get("/")
async def list_projects(project_type: str = None):
    """جلب قائمة جميع المشاريع المحفوظة"""
    try:
        projects = []
        if not PROJECTS_BASE_DIR.exists():
            return {"count": 0, "projects": []}

        for folder in sorted(PROJECTS_BASE_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            meta_file = folder / "meta.json"
            if folder.is_dir() and meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    if project_type and meta.get("type") != project_type:
                        continue
                    meta["preview_url"] = f"/projects/{folder.name}/index.html"
                    projects.append(meta)
                except Exception:
                    pass

        return {"count": len(projects), "projects": projects}
    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/meta")
async def get_project_meta(project_id: str):
    """جلب بيانات مشروع معين"""
    project_dir = PROJECTS_BASE_DIR / project_id
    meta_file = project_dir / "meta.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail=f"المشروع '{project_id}' غير موجود.")
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        meta["preview_url"] = f"/projects/{project_id}/index.html"
        return meta
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/download")
async def download_project_zip(project_id: str):
    """تحميل المشروع كملف ZIP"""
    project_dir = PROJECTS_BASE_DIR / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"المشروع '{project_id}' غير موجود.")

    try:
        # جلب الاسم من meta.json
        meta_file = project_dir / "meta.json"
        project_name = project_id
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            project_name = meta.get("name", project_id).replace(" ", "_")

        # إنشاء ZIP في الذاكرة
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in project_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(project_dir)
                    zf.write(file_path, arcname=str(arcname))

        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={project_name}.zip"},
        )
    except Exception as e:
        logger.error(f"Error creating ZIP for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """حذف مشروع"""
    import shutil
    project_dir = PROJECTS_BASE_DIR / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"المشروع '{project_id}' غير موجود.")
    try:
        shutil.rmtree(project_dir)
        return {"deleted": True, "project_id": project_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
