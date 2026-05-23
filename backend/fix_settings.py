import asyncio
from app import app, db
from models import User

async def fix_user_settings():
    with app.app_context():
        users = db.query(User).all()
        
        default_settings = {
            'ladder': {
                'autoRefresh': False,
                'refreshInterval': 30,
                'smartMode': True,
                'showFirstBoard': True
            },
            'watchlist': {
                'autoRefresh': False,
                'refreshInterval': 30,
                'smartMode': True
            },
            'statistics': {
                'autoRefresh': False,
                'refreshInterval': 30,
                'smartMode': True
            },
            'news': {
                'autoRefresh': False,
                'refreshInterval': 300,
                'smartMode': True,
                'showAllNews': False,
                'speechEnabled': True,
                'speechSettings': {
                    'voices': {},
                    'rate': 1.0,
                    'pitch': 1.0,
                    'volume': 1.0
                }
            },
            'reports': {
                'autoRefresh': False,
                'refreshInterval': 3600,
                'smartMode': False
            }
        }
        
        for user in users:
            if user.settings:
                # 合并缺失的字段
                for page, default_page_settings in default_settings.items():
                    if page not in user.settings:
                        user.settings[page] = default_page_settings
                    else:
                        # 合并页面级别的缺失字段
                        for key, value in default_page_settings.items():
                            if key not in user.settings[page]:
                                user.settings[page][key] = value
                
                print(f"Fixed settings for user {user.uid}")
        
        db.commit()
        print("All user settings fixed!")

if __name__ == '__main__':
    asyncio.run(fix_user_settings())
