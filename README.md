## Telegram Subscription Bot

### **@trusov_vip_bot Telegram Bot**

#### This project is a Python Telegram Bot for managing subscription-based access to a private Telegram channel. It integrates with Stripe for payments and Google Drive for database backups.

### Setup
#### 1. Clone the Repository
```bash
git clone https://github.com/gimmevsc/subscription_manager_bot.git
cd <repository-folder>
```

#### 2. Install Dependencies
````bash
pip install -r requirements.txt
````

#### 3. Set Up Environment Variables
Create a .env file in the project root by copying .env.example:
```bash
cp .env.example .env
```

#### 4. Set Up Google Drive Credentials
Download the service account credentials file (service-account.json) from your Google Cloud project.
Place the file in the project root directory.

#### 5. Start the Bot and Flask Server
Run the bot and Flask webhook server concurrently using:
```bash
python main.py
```
