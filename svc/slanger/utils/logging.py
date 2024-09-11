import logging

class ColoredFormatter(logging.Formatter):
    # Define color codes
    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '\033[92m',   # Green
        'WARNING': '\033[93m',# Yellow
        'ERROR': '\033[91m',  # Red
        'CRITICAL': '\033[95m'# Magenta
    }
    RESET = '\033[0m'  # Reset color
    TICKER_COLOR = '\033[96m'  # Cyan for ticker

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        
        # Add color to the ticker symbol if present in the message
        if 'ticker' in message:
            message = message.replace('ticker', f"{self.TICKER_COLOR}ticker{self.RESET}")
        
        return f"{log_color}{message}{self.RESET}"