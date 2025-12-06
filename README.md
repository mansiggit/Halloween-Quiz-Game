# 🎃 AI-Powered Halloween Quiz Game 👻

A Python-based, fully-interactive quiz game that dynamically generates questions based on user-defined categories, audience, and difficulty. The application leverages a local Large Language Model (LLM) for question generation and uses Gradio for the responsive web interface, all deployed using a **two-container Docker architecture**.

## ✨ Features

* **Containerized Deployment:** The application and its LLM dependency are designed to run in separate, isolated Docker containers for production-ready deployment.
* **Dynamic Quiz Generation:** Utilizes a local LLM (configured for a LocalAI endpoint) to generate unique quizzes in structured JSON format.
* **Resilience:** Features an **offline fallback mode** using hardcoded questions if the LLM service connection fails.
* **Custom UI:** Retro "CRT" aesthetic and themed styling for an immersive Halloween experience.

## 🛠️ Technologies Used

| Technology | Role |
| :--- | :--- |
| **Python** | Core application logic and game state management. |
| **Gradio** | Building the interactive, web-based User Interface. |
| **OpenAI Library** | Facilitating API calls and communication with the local LLM endpoint. |
| **HTTPX** | Underlying HTTP client for robust API requests. |
| **Docker** | Containerization and orchestration of the two-service architecture. |

## 🚀 Prerequisites (Docker Required)

This project requires **Docker** to be installed and running. It utilizes a **two-container setup** where the Quiz App container connects to an external LLM Server container.

1.  **Docker Engine**
2.  **LLM Service:** An LLM must be running and accessible on **port 8080** and serving a model named `gpt-3.5-turbo` (or a compatible alias).
