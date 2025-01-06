import json
import os
from typing import Dict, List, Optional
from datetime import datetime

class UserDatabase:
    def __init__(self, db_file: str = 'users.json'):
        self.db_file = db_file
        self.users: Dict[str, dict] = {}
        self.load_database()

    def load_database(self) -> None:
        """Load the user database from JSON file"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            except json.JSONDecodeError:
                self.users = {}
        else:
            self.users = {}

    def save_database(self) -> None:
        """Save the user database to JSON file"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=2, ensure_ascii=False)

    def add_user(self, user_id: str, username: str = None, first_name: str = None) -> None:
        """Add a new user or update existing user's information"""
        if user_id not in self.users:
            self.users[user_id] = {
                'username': username,
                'first_name': first_name,
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'command_count': 0,
                'commands_used': {}
            }
        else:
            # Update username and first_name if they changed
            self.users[user_id]['username'] = username
            self.users[user_id]['first_name'] = first_name
            self.users[user_id]['last_seen'] = datetime.now().isoformat()
        
        self.save_database()

    def log_command(self, user_id: str, command: str) -> None:
        """Log a command usage for a user"""
        if user_id in self.users:
            self.users[user_id]['command_count'] += 1
            self.users[user_id]['last_seen'] = datetime.now().isoformat()
            
            # Update command-specific count
            if command not in self.users[user_id]['commands_used']:
                self.users[user_id]['commands_used'][command] = 1
            else:
                self.users[user_id]['commands_used'][command] += 1
            
            self.save_database()

    def get_user(self, user_id: str) -> Optional[dict]:
        """Get user information"""
        return self.users.get(user_id)

    def get_all_users(self) -> List[dict]:
        """Get all users"""
        return list(self.users.values())

    def get_total_users(self) -> int:
        """Get total number of users"""
        return len(self.users)

    def get_active_users(self, days: int = 7) -> List[dict]:
        """Get users who were active in the last X days"""
        current_time = datetime.now()
        active_users = []
        
        for user_id, user_data in self.users.items():
            last_seen = datetime.fromisoformat(user_data['last_seen'])
            days_diff = (current_time - last_seen).days
            if days_diff <= days:
                active_users.append(user_data)
        
        return active_users
