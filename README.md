# [StoreCord](https://github.com/weiwei-hacking/StoreCord/releases/latest)

A Discord bot for managing a online store system, allowing users to purchase products, check stock, and manage user credits. Built with Python and Discord.py.

## Features

- **Product Management** (`/product`):
  - Create new products with a name and price (`/product create`).
  - Remove existing products (`/product remove`).
  - Manage product stock: clear, download, or update stock (`/product stock`).

- **Stock Overview** (`/stock`):
  - Display the stock of all products in the `stock/` directory.

- **Restock Products** (`/restock`):
  - Restock products by uploading a `.txt` file and notify users in a specified channel.

- **Purchase Products** (`/purchase`):
  - Purchase products with credits, deducting from user balance and generating an order file.

- **Order Lookup** (`/order`):
  - Retrieve order details by order ID, with the order file sent via DMs or channel.

- **User Credits Management** (`/credits`):
  - Check user credits (`/balance`).
  - Modify user credits (`/credits modify`).

- **User CreditsKey Management** (`/creditskey`):
  - Add credits keys (`/creditskey add`).
  - Remove credits keys (`/creditskey remove`).
  - Redeem credit key (`/redeem`).

## Prerequisites

- Python 3.8 or higher
- Discord.py library (`discord.py`)
- A Discord bot token
- A Discord server to test the bot

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/weiwei-hacking/StoreCord.git
   cd discord-shop-bot
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Configuration Files**:
     - `permissions.json`: Defines users and roles with special permissions (e.g., `{"users": ["user_id"], "roles": ["role_id"]}`).
     - `normal.json`: Bot settings (e.g., `{"restock_channel": "channel_id", "restock_notify": "role_id"}`).

4. **Set Up Bot Token**:
   - Past your bot token in `token.txt`
   - Example `token.txt`:
     ```
     your_discord_bot_token
     ```

5. **Run the Bot**:
   - ```bash
     python bot.py
     ```



## Available Commands
   - `/product create <name> <price>`: Create a new product.
   - `/product remove <file>`: Remove a product.
   - `/product stock <action> <file>`: Manage product stock (remove, download, update).
   - `/stock`: View all product stock.
   - `/restock <file> <attachment>`: Restock a product with a `.txt` file.
   - `/purchase <amount>`: Purchase products with credits.
   - `/order <order_id>`: View an order by its ID.
   - `/balance [member]`: Check a user's credits.
   - `/credits modify <member> <action> <amount>`: Add or remove credits.
   - `/user [member]`: View user information.
   - `/creditkey <add/remove/show> <key_tpye> [amount(only add)]`: Add or remove credit key.
   - `/redeem <key>`: Redeem a creditkey.

## File Structure

```
discord-shop-bot/
│
├── cogs/
│   ├── balance.py       # Manages user credits
│   ├── order.py         # Handles order lookup
│   ├── product.py       # Manages product creation and stock
│   ├── purchase.py      # Handles product purchases
│   ├── stock.py         # Displays stock and handles restocking
│   └── userpanel.py     # Displays user information
|   └── creditkey.py     # Manages credit key
│
├── configs/
│   ├── balance.json     # User credits data
│   ├── permissions.json # Permission settings
│   ├── price.json       # Product prices
│   └── normal.json      # Misc settings
│
├── creditkey/
│   ├── 100.txt          # 100 credit key
│   ├── custom.txt       # custom credit key
│
├── stock/               # Product stock files (.txt)
├── order/               # Generated order files (.txt)
├── bot.py               # Main bot file (not included, user to create)
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Make your changes and commit (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/weiwei-hacking/StoreCord/blob/main/LICENSE) file for details.

## Acknowledgments

- Powered by [grok.com](https://x.ai)
- Built with [Discord.py](https://discordpy.readthedocs.io/en/stable/)
- Inspired by Discord bot communities
