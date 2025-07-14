# spending-app-aiogram

## Running the Application with Docker Compose



1. **Prepare your `.env` file**

   Create a `.env` file in the project root directory with the following content (see `.env.example`):

   ```
   BOT_TOKEN=your_telegram_bot_token
   POSTGRES_DB=spending
   POSTGRES_PASSWORD=your_postgres_password
   POSTGRES_DSN=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
   EXCHANGE_API_KEY=your_exchange_api_key  # optional
   ```

   - `BOT_TOKEN`: Your Telegram bot token
   - `POSTGRES_DB`: Name of the PostgreSQL database (default: `spending`)
   - `POSTGRES_PASSWORD`: Password for the PostgreSQL user (set a secure password for production)
   - `POSTGRES_DSN`: Connection string for PostgreSQL (use the format above)
   - `EXCHANGE_API_KEY`: (Optional) API key for currency exchange

   **Note:** Do NOT commit your real secrets to git. Use `.env.example` as a template.

2. **Build and start the application**

   Run the following command in your project directory:

   ```bash
   docker compose up --build -d
   ```

   This will build the Docker image and start the bot using the configuration from your `.env` file.

3. **Database Persistence**

   The application now uses PostgreSQL for data storage. The `docker-compose.yml` file includes a PostgreSQL service, and your data will persist in the PostgreSQL volume between restarts.

4. **Stopping the Application**

   To stop the application, press `Ctrl+C` in the terminal or run:

   ```bash
   docker compose down
   ```

---

**Note:**

- Ensure your `.env` file is present and properly configured before starting the application.
- You can modify the `docker-compose.yml` file to adjust environment variables, volumes, or other settings as needed.
- The application no longer uses SQLite. All data is stored in PostgreSQL.