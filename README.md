# spending-app-aiogram

## Running the Application with Docker Compose

1. **Prepare your `.env` file**

   Make sure you have a `.env` file in the project root directory with all required environment variables for your application. This file will be used to configure the bot.

2. **Build and start the application**

   Run the following command in your project directory:

   ```bash
   docker compose up --build -d
   ```

   This will build the Docker image and start the bot using the configuration from your `.env` file.

3. **Database Persistence**

   The `docker-compose.yml` mounts the `spending.sqlite3` file from your host to the container, so your data will persist between restarts.

4. **Stopping the Application**

   To stop the application, press `Ctrl+C` in the terminal or run:

   ```bash
   docker compose down
   ```

---

**Note:**

- Ensure your `.env` file is present and properly configured before starting the application.
- You can modify the `docker-compose.yml` file to adjust environment variables, volumes, or other settings as needed.