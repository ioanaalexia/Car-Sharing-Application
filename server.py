import socket
import threading
import json
import os

# Fișiere pentru stocare
USERS_FILE = "users.txt"
CARS_FILE = "cars.txt"
RENTALS_FILE = "rentals.txt"

# Stocare sesiuni utilizatori autentificați
active_sessions = {}

payment_pending = set()

# Stocare stări mașini
car_states = {}  # Exemplu: {"1": "locked", "2": "unlocked"}

# Stocare conexiuni mașini
car_connections = {}  # Exemplu: {"1": client_socket, "2": client_socket}


# Inițializare fișiere
def initialize_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write("")
    if not os.path.exists(CARS_FILE):
        with open(CARS_FILE, "w") as f:
            f.write("1,Tesla Model 3,Electric,Available\n2,BMW X5,SUV,Available")
    if not os.path.exists(RENTALS_FILE):
        with open(RENTALS_FILE, "w") as f:
            f.write("")


# Funcții pentru gestionarea datelor
def load_users():
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) == 3:
                    users[parts[0]] = {"password": parts[1], "license": parts[2]}
    return users


def save_user(username, password, license):
    with open(USERS_FILE, "a") as f:
        f.write(f"{username},{password},{license}\n")


def load_cars():
    cars = {}
    if os.path.exists(CARS_FILE):
        with open(CARS_FILE, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) == 4:
                    cars[parts[0]] = {
                        "model": parts[1],
                        "type": parts[2],
                        "available": parts[3] == "Available"
                    }
    return cars


def save_cars(cars):
    with open(CARS_FILE, "w") as f:
        for car_id, info in cars.items():
            status = "Available" if info["available"] else "Rented"
            f.write(f"{car_id},{info['model']},{info['type']},{status}\n")


def load_rentals():
    rentals = {}
    if os.path.exists(RENTALS_FILE):
        with open(RENTALS_FILE, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) == 2:
                    rentals[parts[0]] = parts[1]
    return rentals


def save_rentals(rentals):
    with open(RENTALS_FILE, "w") as f:
        for username, car_id in rentals.items():
            f.write(f"{username},{car_id}\n")


# Funcția pentru notificarea tuturor clienților (exclusiv cel curent)
def notify_clients_except_current(message, current_user):
    for user, client_socket in active_sessions.items():
        if user != current_user:
            try:
                notification = {"type": "notification", "message": message}
                client_socket.send(json.dumps(notification).encode("utf-8"))
            except Exception as e:
                print(f"[SERVER] Error notifying user {user}: {e}")


# Handler pentru clienții de tip aplicație mobilă
def handle_mobile_client(client_socket, address):
    global payment_pending  # Declarăm variabila globală pentru a o utiliza
    print(f"[SERVER] Connected to {address}")
    logged_in_user = None
    selected_car = None
    driven = False

    while True:
        try:
            data = client_socket.recv(1024).decode("utf-8")
            if not data:
                break

            # Reîncărcăm mereu datele proaspete
            users = load_users()
            cars = load_cars()
            rentals = load_rentals()
            request = json.loads(data)
            action = request.get("action")

            # ----------------- AUTHENTICATION ----------------- #
            if action == "register":
                username = request["username"]
                if username in users:
                    response = {"message": "Username already exists"}
                else:
                    save_user(username, request["password"], request["license"])
                    response = {"message": "Registration successful"}
                client_socket.send(json.dumps(response).encode("utf-8"))

            elif action == "login":
                username = request["username"]
                password = request["password"]
                if username in users and users[username]["password"] == password:
                    logged_in_user = username
                    active_sessions[username] = client_socket
                    response = {"message": "Login successful"}
                else:
                    response = {"message": "Invalid credentials"}
                client_socket.send(json.dumps(response).encode("utf-8"))

            elif action == "logout":
                if logged_in_user in rentals or logged_in_user in payment_pending:
                    response = {"type": "response", "message": "Cannot logout during active rental/payment"}
                else:
                    active_sessions.pop(logged_in_user, None)
                    logged_in_user = None
                    response = {"type": "response", "message": "Logout successful"}
                client_socket.send(json.dumps(response).encode("utf-8"))

            # ----------------- CAR OPERATIONS ----------------- #
            elif action == "query_cars":
                if not logged_in_user:
                    response = {"type": "response", "message": "Login required"}
                else:
                    available_cars = {k: v for k, v in cars.items() if v["available"]}
                    if not available_cars:  # Verifică dacă nu există mașini disponibile
                        response = {
                            "type": "response",
                            "message": "No cars available",
                            "cars": {}
                        }
                    else:
                        response = {
                            "type": "response",
                            "message": "Available cars",
                            "cars": available_cars
                        }
                client_socket.send(json.dumps(response).encode("utf-8"))

            elif action == "select_car":
                if not logged_in_user:
                    response = {"message": "Login required"}
                elif logged_in_user in rentals:
                    response = {"message": "You have an active rental"}
                else:
                    car_id = str(request["car_id"])
                    if car_id in cars and cars[car_id]["available"]:
                        selected_car = car_id
                        response = {"message": f"Car {car_id} selected"}
                    else:
                        response = {"message": "Car not available"}
                client_socket.send(json.dumps(response).encode("utf-8"))

            elif action == "start_rental":
                if not logged_in_user:
                    response = {"type": "response", "message": "Login required"}
                elif logged_in_user in rentals:
                    response = {"type": "response", "message": "You already have a rental"}
                elif not selected_car:
                    response = {"type": "response", "message": "Select a car first"}
                elif not cars[selected_car]["available"]:
                    response = {"type": "response", "message": "Car no longer available"}
                else:
                    cars[selected_car]["available"] = False
                    rentals[logged_in_user] = selected_car
                    save_cars(cars)
                    save_rentals(rentals)
                    response = {
                        "type": "response",
                        "message": f"Car {selected_car} rented successfully"
                    }
                    notify_clients_except_current(f"Car {selected_car} has been rented", logged_in_user)
                client_socket.send(json.dumps(response).encode("utf-8"))

            elif action == "drive":
                if not logged_in_user:
                    response = {"message": "Login required"}
                elif logged_in_user not in rentals:
                    response = {"message": "You must rent a car first"}
                elif driven:
                    response = {"message": "Already driving the car"}
                else:
                    driven = True
                    car_id = rentals[logged_in_user]
                    response = {"message": f"You are driving car {car_id}"}

                # Trimite comanda "unlock" către mașină înainte de a începe condusul
                if car_id in car_connections:
                    car_socket = car_connections[car_id]
                    car_socket.send(json.dumps({"action": "unlock"}).encode("utf-8"))
                print(f"[SERVER] Sent unlock command to car {car_id} for driving")

                client_socket.send(json.dumps(response).encode("utf-8"))

            elif action == "end_rental":
                if not logged_in_user or logged_in_user not in rentals:
                    response = {"type": "response", "message": "No active rental"}
                else:
                    car_id = rentals.pop(logged_in_user)
                    cars[car_id]["available"] = True
                    payment_pending.add(logged_in_user)
                    save_cars(cars)
                    save_rentals(rentals)
                    response = {"type": "response", "message": "Proceed to payment"}
                    notify_clients_except_current(f"Car {car_id} available", logged_in_user)

                    # Trimite cerere de end_rental către mașină
                    if car_id in car_connections:
                        car_socket = car_connections[car_id]
                        car_socket.send(json.dumps({"action": "lock"}).encode("utf-8"))
                        print(f"[SERVER] Sent lock command to car {car_id}")

                client_socket.send(json.dumps(response).encode("utf-8"))

            elif action == "pay_statistics":
                if logged_in_user in payment_pending:
                    payment_pending.remove(logged_in_user)  # Ștergem din așteptări
                    response = {"type": "response", "message": "Payment completed"}
                else:
                    response = {"type": "response", "message": "No pending payments"}
                client_socket.send(json.dumps(response).encode("utf-8"))

            else:
                response = {"message": "Invalid action"}
                client_socket.send(json.dumps(response).encode("utf-8"))
        except Exception as e:
            print(f"[SERVER] Error: {e}")
            break

    client_socket.close()
    print(f"[SERVER] Disconnected from mobile client at {address}")


# Handler pentru clienții de tip mașină
def handle_car_client(client_socket, address):
    print(f"[SERVER] Connected to car at {address}")
    car_id = None

    while True:
        try:
            data = client_socket.recv(1024).decode("utf-8")
            if not data:
                break

            request = json.loads(data)
            action = request.get("action")

            if action == "register_car":
                car_id = request["car_id"]
                car_states[car_id] = "locked"  # Starea inițială a mașinii
                car_connections[car_id] = client_socket  # Adăugăm conexiunea mașinii
                response = {"message": f"Car {car_id} registered successfully"}
                client_socket.send(json.dumps(response).encode("utf-8"))
                print(f"[SERVER] Car {car_id} registered. Initial state: locked")

            elif action == "reportState":
                car_id = request["car_id"]
                state = request["state"]
                car_states[car_id] = state
                response = {"message": "State updated successfully"}
                client_socket.send(json.dumps(response).encode("utf-8"))

            elif action == "checkCarState":
                car_id = request["car_id"]
                state = car_states.get(car_id, "unknown")
                response = {"car_id": car_id, "state": state}
                client_socket.send(json.dumps(response).encode("utf-8"))

            elif action == "toggleCarLock":
                car_id = request["car_id"]
                current_state = car_states.get(car_id, "locked")
                new_state = "unlocked" if current_state == "locked" else "locked"
                car_states[car_id] = new_state
                response = {"message": f"Car {car_id} is now {new_state}"}
                client_socket.send(json.dumps(response).encode("utf-8"))
                print(f"[SERVER] Car {car_id} state changed to: {new_state}")

            else:
                response = {"message": "Invalid action"}
                client_socket.send(json.dumps(response).encode("utf-8"))

        except Exception as e:
            print(f"[SERVER] Error: {e}")
            break

    if car_id:
        car_states.pop(car_id, None)  # Elimină mașina din starea serverului la deconectare
        car_connections.pop(car_id, None)  # Elimină conexiunea mașinii
    client_socket.close()
    print(f"[SERVER] Disconnected from car at {address}")


# Pornim serverul pentru clienții de tip aplicație mobilă
initialize_files()
mobile_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mobile_server.bind(("127.0.0.1", 5555))
mobile_server.listen(5)
print("[SERVER] Mobile server is running...")

# Pornim serverul pentru clienții de tip mașină
car_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
car_server.bind(("127.0.0.1", 5556))
car_server.listen(5)
print("[SERVER] Car server is running...")


# Acceptăm conexiuni de la clienții de tip aplicație mobilă
def accept_mobile_connections():
    while True:
        client_socket, addr = mobile_server.accept()
        threading.Thread(target=handle_mobile_client, args=(client_socket, addr)).start()


# Acceptăm conexiuni de la clienții de tip mașină
def accept_car_connections():
    while True:
        client_socket, addr = car_server.accept()
        threading.Thread(target=handle_car_client, args=(client_socket, addr)).start()


# Pornim thread-uri pentru a accepta conexiuni
threading.Thread(target=accept_mobile_connections, daemon=True).start()
threading.Thread(target=accept_car_connections, daemon=True).start()

# Menținem serverul activ
while True:
    pass