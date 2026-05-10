# VKID Backend

This is a simple Go application that logs "hello world". This README provides instructions on how to build and run the application using Docker and Docker Compose, as well as how to configure environment variables.

## Prerequisites

Make sure you have the following installed on your machine:

- [Docker](https://www.docker.com/get-started) (with Docker Compose)
- [Go](https://golang.org/doc/install) (for development purposes)

## Setup

1. **Clone the repository**:
   ```bash
   git clone <https://github.com/Project-practice-MEPHI-2024/vkid-backend.git>
   cd <vkid-backend>
   ```

2. **Добавить локальное окружение**:
    ```bash
   #открываем vkid-backend
   cd vkid-backend

   if [ -f ".local.env" ]; then
    echo "Файл local.env уже существует."
   else

   # Создание файла local.env
   touch ./local.env
   echo "./local.env файл создан."
   fi

   # Добавление переменной CONFIG_PATH в local.env, если она не существует
   if ! grep -q "LOCAL_CONFIG_PATH=config/local.yaml" "$env_file"; then
   echo "LOCAL_CONFIG_PATH=config/local.yaml" >> "$env_file"
   echo "Переменная LOCAL_CONFIG_PATH добавлена в $env_file."
   else
   echo "Переменная LOCAL_CONFIG_PATHH уже присутствует в $env_file."
   fi
   ```
   Если не работает, надо руками создать local.env в корне проекта и записать в него
   ```CONFIG_PATH=config/local.yaml```
   Еще нужно это же добавить к себе в постоянные переменные окружения. возможно понадобится перезапуск пк


3. **Build and run**:
    ```bash
   docker-compose up
   ```