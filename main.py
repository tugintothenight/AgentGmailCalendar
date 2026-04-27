from interfaces.telegram_bot import TelegramInterface, AVAILABLE_TOOLS
from core.background_jobs import BackgroundJobManager

if __name__ == "__main__":
    app = TelegramInterface()
    
    bg_manager = BackgroundJobManager(
        orchestrator=app.orchestrator,
        bot_interface=app,
        available_tools=AVAILABLE_TOOLS
    )
    
    bg_manager.start()
    
    app.start() 