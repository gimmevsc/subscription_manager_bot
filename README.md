## Telegram Subscription Bot

##@trusov_vip_bot Telegram Bot

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

#### 3. Create the .env File
Create a .env file in the project root directory to store sensitive credentials. Use the .env_example as a template:

.env:
```plaintext
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
PRIVATE_CHAT_ID=your-group-chat-id
STRIPE_API_KEY=your-stripe-api-key
PAYMENT_PROVIDER_TOKEN=your-payment-provider-token
WEBHOOK_SECRET=your-stripe-webhook-secret
DATABASE_PATH=your-database-file-path.db
```

#### 4. Set Up Google Drive Credentials
Download the service account credentials file (service-account.json) from your Google Cloud project.
Place the file in the project root directory.

#### 5. Start the Bot and Flask Server
Run the bot and Flask webhook server concurrently using:
```bash
python main.py
```
