from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from dotenv import load_dotenv  # ← ADDED

load_dotenv()  # ← ADDED (dapat nasa taas, bago mag-import ng ibang services)

from app.controllers import api as api_controller
from app.controllers import ws as ws_controller

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


app = FastAPI(title="FRIDAY Voice Assistant", description="Voice-controlled assistant with system control capabilities", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_controller.router)
app.include_router(ws_controller.router)


@app.on_event("startup")
async def startup_event():
    logger.info("FRIDAY Voice Assistant starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FRIDAY Voice Assistant shutting down...")