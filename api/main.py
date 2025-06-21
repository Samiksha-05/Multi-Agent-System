# File: main.py (placed in the api directory)

import os
import uuid
import logging
import shutil
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import json
import csv
from io import StringIO
import sys

# Add the parent directory to sys.path so we can import modules properly
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import our local modules
from agents.email_agent import EmailAgent
from agents.pdf_agent import PdfAgent
from agents.json_agent import JsonAgent
from agents.classifier_agent import ClassifierAgent
from memory.memory_store import MemoryStore  # Import from the correct module
from router.action_router import ActionRouter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Multi-Format Autonomous AI System")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Setup static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up temporary file directory
TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

# Initialize shared memory store
memory_store = MemoryStore()

# Initialize agents
classifier_agent = ClassifierAgent(memory_store)
email_agent = EmailAgent(memory_store)
pdf_agent = PdfAgent(memory_store)
json_agent = JsonAgent(memory_store)

# Initialize action router
action_router = ActionRouter(memory_store)

# Home page route
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "current_user": "Prudhvi-Vinayak",  # In a real app, this would be from auth
            "current_time": current_time
        }
    )

# File upload route
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), intent: str = Form("")):
    try:
        # Generate a unique ID for this document
        document_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Save the file temporarily
        file_path = os.path.join(TEMP_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create metadata
        metadata = {
            "document_id": document_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "size": os.path.getsize(file_path),
            "upload_time": timestamp,
            "user": "Prudhvi-Vinayak"  # In a real app, this would be from auth
        }
        
        # Store metadata in memory
        memory_store.store(document_id, "metadata", metadata)
        memory_store.update_status(document_id, "received")
        
        # Classify the document
        classification_result = classifier_agent.classify(file_path, metadata, user_intent=intent)
        memory_store.store(document_id, "classification", classification_result)
        
        # Process the document based on its format
        format_type = classification_result.get("format")
        
        if format_type == "email":
            email_agent.process(file_path, metadata)
        elif format_type == "pdf":
            pdf_agent.process(file_path, metadata)
        elif format_type == "json":
            json_agent.process(file_path, metadata)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        # Update status to analyzed
        memory_store.update_status(document_id, "analyzed")
        
        # Redirect to results page
        return RedirectResponse(url=f"/results/{document_id}", status_code=303)
    
    except Exception as e:
        logger.error(f"Error processing upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Results page route
@app.get("/results/{document_id}", response_class=HTMLResponse)
async def get_results(document_id: str, request: Request):
    try:
        # Get document data from memory
        document = memory_store.get(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found")
        
        # Extract data for the template
        data = document.get("data", {})
        metadata = data.get("metadata", {})
        classification = data.get("classification", {})
        email_analysis = data.get("email_analysis", {})
        pdf_analysis = data.get("pdf_analysis", {})
        json_analysis = data.get("json_analysis", {})
        status = document.get("status", "unknown")
        
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        # Render the template
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "document_id": document_id,
                "metadata": metadata,
                "classification": classification,
                "email_analysis": email_analysis,
                "pdf_analysis": pdf_analysis,
                "json_analysis": json_analysis,
                "status": status,
                "current_user": "Prudhvi-Vinayak",  # In a real app, this would be from auth
                "current_time": current_time
            }
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error retrieving results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Trigger action route
@app.get("/trigger-action/{document_id}")
async def trigger_action(document_id: str, action: str = None):
    try:
        # Route the document to the appropriate action
        result = action_router.route_action(document_id, action)
        
        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("message", "Action failed"))
        
        # Redirect back to results page
        return RedirectResponse(url=f"/results/{document_id}", status_code=303)
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error triggering action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard route
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    page: int = Query(1, ge=1),
    format_filter: str = Query(""),
    status_filter: str = Query(""),
    date_filter: str = Query("")
):
    try:
        # Get all documents from memory
        all_documents = memory_store.get_all()
        
        # Apply filters
        filtered_docs = all_documents
        
        if format_filter:
            filtered_docs = [
                doc for doc in filtered_docs
                if doc.get("data", {}).get("classification", {}).get("format") == format_filter
            ]
        
        if status_filter:
            filtered_docs = [doc for doc in filtered_docs if doc.get("status") == status_filter]
        
        if date_filter:
            filtered_docs = [
                doc for doc in filtered_docs
                if doc.get("data", {}).get("metadata", {}).get("upload_time", "").startswith(date_filter)
            ]
        
        # Count formats and statuses
        format_counts = {}
        status_counts = {}
        
        for doc in all_documents:
            # Count formats
            fmt = doc.get("data", {}).get("classification", {}).get("format")
            if fmt:
                format_counts[fmt] = format_counts.get(fmt, 0) + 1
            
            # Count statuses
            status = doc.get("status")
            if status:
                status_counts[status] = status_counts.get(status, 0) + 1
        
        # Sort by upload time (newest first)
        filtered_docs.sort(
            key=lambda x: x.get("data", {}).get("metadata", {}).get("upload_time", ""),
            reverse=True
        )
        
        # Simple pagination
        per_page = 10
        total_pages = max(1, (len(filtered_docs) + per_page - 1) // per_page)
        page = min(page, total_pages)
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_docs = filtered_docs[start_idx:end_idx]
        
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        # Render the dashboard template
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "documents": paginated_docs,
                "total_count": len(all_documents),
                "format_counts": format_counts,
                "status_counts": status_counts,
                "format_filter": format_filter,
                "status_filter": status_filter,
                "date_filter": date_filter,
                "page": page,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
                "current_user": "Prudhvi-Vinayak",  # In a real app, this would be from auth
                "current_time": current_time
            }
        )
    
    except Exception as e:
        logger.error(f"Error displaying dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard metrics route
@app.get("/dashboard/metrics", response_class=HTMLResponse)
async def dashboard_metrics(request: Request):
    try:
        # Get all documents from memory
        all_documents = memory_store.get_all()
        
        # Count formats and statuses
        format_counts = {}
        status_counts = {}
        daily_counts = {}
        
        for doc in all_documents:
            # Count formats
            fmt = doc.get("data", {}).get("classification", {}).get("format")
            if fmt:
                format_counts[fmt] = format_counts.get(fmt, 0) + 1
            
            # Count statuses
            status = doc.get("status")
            if status:
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Daily counts
            upload_time = doc.get("data", {}).get("metadata", {}).get("upload_time", "")
            if upload_time:
                date = upload_time.split("T")[0]  # Extract date part
                daily_counts[date] = daily_counts.get(date, 0) + 1
        
        # Get any documents with errors for display
        error_documents = [doc for doc in all_documents if doc.get("status") == "error"][:5]
        
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        # Render the metrics template
        return templates.TemplateResponse(
            "dashboard_metrics.html",
            {
                "request": request,
                "total_count": len(all_documents),
                "format_counts": format_counts,
                "status_counts": status_counts,
                "daily_counts": daily_counts,
                "error_documents": error_documents,
                "current_user": "Prudhvi-Vinayak",  # In a real app, this would be from auth
                "current_time": current_time
            }
        )
    
    except Exception as e:
        logger.error(f"Error displaying metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Export metrics as JSON
@app.get("/dashboard/metrics/export/json")
async def export_metrics_json():
    try:
        # Get all documents from memory
        all_documents = memory_store.get_all()
        
        # Prepare export data
        export_data = {
            "total_count": len(all_documents),
            "format_distribution": {},
            "status_distribution": {},
            "daily_processing": {},
            "documents": []
        }
        
        # Calculate distributions
        for doc in all_documents:
            # Format distribution
            fmt = doc.get("data", {}).get("classification", {}).get("format")
            if fmt:
                export_data["format_distribution"][fmt] = export_data["format_distribution"].get(fmt, 0) + 1
            
            # Status distribution
            status = doc.get("status")
            if status:
                export_data["status_distribution"][status] = export_data["status_distribution"].get(status, 0) + 1
            
            # Daily processing
            upload_time = doc.get("data", {}).get("metadata", {}).get("upload_time", "")
            if upload_time:
                date = upload_time.split("T")[0]  # Extract date part
                export_data["daily_processing"][date] = export_data["daily_processing"].get(date, 0) + 1
            
            # Add minimal document info
            export_data["documents"].append({
                "document_id": doc.get("document_id"),
                "status": doc.get("status"),
                "format": doc.get("data", {}).get("classification", {}).get("format"),
                "intent": doc.get("data", {}).get("classification", {}).get("intent"),
                "upload_time": doc.get("data", {}).get("metadata", {}).get("upload_time")
            })
        
        # Return as JSON
        return JSONResponse(content=export_data)
    
    except Exception as e:
        logger.error(f"Error exporting metrics as JSON: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Export metrics as CSV
@app.get("/dashboard/metrics/export/csv")
async def export_metrics_csv():
    try:
        # Get all documents from memory
        all_documents = memory_store.get_all()
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["Document ID", "Status", "Format", "Intent", "Upload Time", "Filename"])
        
        # Write data rows
        for doc in all_documents:
            writer.writerow([
                doc.get("document_id"),
                doc.get("status"),
                doc.get("data", {}).get("classification", {}).get("format"),
                doc.get("data", {}).get("classification", {}).get("intent"),
                doc.get("data", {}).get("metadata", {}).get("upload_time"),
                doc.get("data", {}).get("metadata", {}).get("filename")
            ])
        
        # Prepare response
        response = Response(content=output.getvalue(), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=metrics_export.csv"
        return response
    
    except Exception as e:
        logger.error(f"Error exporting metrics as CSV: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Debug route to list all available routes
@app.get("/debug/routes")
async def list_routes():
    routes = []
    
    for route in app.routes:
        info = {
            "path": route.path,
            "name": route.name,
            "methods": route.methods if hasattr(route, "methods") else None
        }
        routes.append(info)
    
    # Also list the static files
    if hasattr(app, "routes"):
        for route in app.routes:
            if hasattr(route, "directory") and route.directory == "static":
                static_info = {
                    "path": route.path,
                    "name": route.name,
                    "type": "StaticFiles"
                }
                routes.append(static_info)
    
    return {"routes": routes}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)