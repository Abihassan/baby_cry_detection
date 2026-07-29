from contextlib import asynccontextmanager
from fastapi import FastAPI
from services.ai_service import get_ai_service
from routers.audio_router import router as audio_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("⏳ Loading Hugging Face AI Models into memory (this may take 1-3 minutes depending on your hardware)...")
    get_ai_service()
    print("✅ AI Models loaded successfully. Running purely offline and stateless (No SQL).")
    
    yield
    print("🛑 Shutting down offline server...")

app = FastAPI(title="Stateless Offline AI Audio Monitor", lifespan=lifespan)

# Register endpoints
app.include_router(audio_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)