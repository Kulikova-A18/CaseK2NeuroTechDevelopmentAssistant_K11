"""
Utility functions for Telegram bot.
"""

import pandas as pd
from io import BytesIO
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def convert_to_excel(data: List[Dict[str, Any]]) -> Optional[BytesIO]:
    """
    Convert data to Excel file.
    
    @param data: List of dictionaries with task data
    @return: BytesIO buffer with Excel file or None
    """
    try:
        # Create DataFrame from data
        df = pd.DataFrame(data)
        
        # Create buffer for Excel file
        output = BytesIO()
        
        # Use ExcelWriter for writing
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Tasks')
            
            # Get workbook and worksheet for column width adjustment
            worksheet = writer.sheets['Tasks']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Error creating Excel file: {e}")
        return None


def csv_to_excel(csv_data: bytes) -> Optional[BytesIO]:
    """
    Convert CSV data to Excel file.
    
    @param csv_data: CSV file bytes
    @return: BytesIO buffer with Excel file or None
    """
    try:
        # Read CSV data to DataFrame
        df = pd.read_csv(BytesIO(csv_data))
        
        # Create buffer for Excel file
        output = BytesIO()
        
        # Use ExcelWriter for writing
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Tasks')
            
            # Get workbook and worksheet for column width adjustment
            worksheet = writer.sheets['Tasks']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Error converting CSV to Excel: {e}")
        return None


async def load_and_show_tasks(message, token: str, filters: Dict[str, Any], title: str = "Задачи"):
    """
    Load and display tasks.
    
    @param message: Message object
    @param token: Authentication token
    @param filters: Filter dictionary
    @param title: Title for display
    """
    from modules.api_client import APIClient
    from modules.formatters import MessageFormatter
    from modules.keyboards import Keyboards
    from modules.constants import BotConstants
    
    await message.answer(
        f"Загружаю {title.lower()}...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    async with APIClient() as api_client:
        tasks = await api_client.get_tasks(token, filters)
        
        if not tasks:
            await message.answer(
                "Задачи не найдены",
                reply_markup=Keyboards.get_tasks_menu()
            )
            return
        
        # Display tasks list
        formatter = MessageFormatter()
        tasks_text = formatter.format_tasks_list(tasks, len(tasks))
        
        # Create keyboard with export suggestion if many tasks
        reply_markup = Keyboards.get_tasks_menu()
        
        if len(tasks) > BotConstants.MAX_TASKS_TO_SHOW:
            # Add export button
            builder = InlineKeyboardBuilder()
            builder.add(
                InlineKeyboardButton(text="Экспорт всех задач", callback_data="export_all_tasks"),
            )
            reply_markup = builder.as_markup()
        
        await message.answer(
            tasks_text,
            reply_markup=reply_markup
        )