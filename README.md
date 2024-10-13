# Running the Application

This project uses Docker Compose to run a FastAPI server and a PostgreSQL database. Follow these steps to get the application up and running:

1. Make sure you have Docker and Docker Compose installed on your system. If not, follow these instructions:

   - **Docker**:

     - For Windows and macOS, download and install Docker Desktop from [Docker's official website](https://www.docker.com/products/docker-desktop).
     - For Linux, follow the instructions on [Docker's official documentation](https://docs.docker.com/engine/install/).

   - **Docker Compose**:
     - Docker Desktop includes Docker Compose. For Linux, follow the instructions on [Docker Compose's official documentation](https://docs.docker.com/compose/install/).

2. Unzip the provided file and navigate to the project directory:

   ```
   unzip llm_application_server.zip
   cd llm_application_server
   ```

3. Build and start the containers:

   ```
   docker-compose up --build
   ```

   This command will build the Docker images if they don't exist and start the containers. The `--build` flag ensures that the images are rebuilt if there are any changes.

4. Once the containers are up and running, you can access the API server at `http://localhost:80`.

5. To access the documentation and test various APIs exposed by the server, visit `http://localhost:80/docs` in your web browser.

6. To connect to the PostgreSQL server, use the following connection details:

   - Host: `db`
   - Port: `5432`
   - Username: `refuel`
   - Password: `refuel123`
   - Database: `refuel_db`

   You can use these credentials to connect to the PostgreSQL server from within your application or using a tool like `psql` from the command line.

   To connect to the PostgreSQL server from within a Docker container, use the following command:

   ```
   psql -h db -U refuel -d refuel_db
   ```

   Replace the host `db` with `localhost` when connecting from the host machine.

   This will start the `psql` command line tool and connect to the PostgreSQL server using the provided credentials.

7. To stop the application, press `Ctrl+C` in the terminal where docker-compose is running, or run the following command in a new terminal:

   ```
   docker-compose down
   ```

   This will stop and remove the containers, networks, and volumes created by `docker-compose up`.
