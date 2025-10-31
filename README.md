# 📨 Asynchronous Task Processing with Celery and Django

## 📘 Overview
This project demonstrates how to integrate **Celery** with a **Django application** to perform tasks asynchronously — specifically for sending booking and payment confirmation emails after a booking is created.  

Using Celery ensures that long-running tasks like sending emails do not block the main request-response cycle, improving overall application performance and user experience.

---

## ⚙️ Technologies Used
- **Django** – Web framework
- **Celery** – Distributed task queue for asynchronous processing
- **RabbitMQ** – Message broker for task communication
- **Redis / RPC** – (optional) result backend
- **cURL / Postman** – API testing tools
- **Ubuntu (WSL2)** – Development environment

---

## 🧩 Task Description

### 🎯 Goal
To test asynchronous task execution using Celery by sending booking and payment confirmation emails after a booking is successfully created through the API.

### 🧵 Workflow
1. User sends a **booking request** via the Django REST API.
2. The booking is saved to the database.
3. A **Celery task** is triggered to:
   - Send a **booking confirmation email**.
   - Send a **payment confirmation email** asynchronously.
4. The response is immediately returned to the user — email sending happens in the background.

---
