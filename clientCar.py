import socket
import json
import random
import time
import threading


class CarClient:
    def __init__(self, car_id, server_ip="127.0.0.1", port=5556):
        self.car_id = car_id
        self.server_ip = server_ip
        self.port = port
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False

        self.rental_active = False
        self.total_distance = 0
        self.total_time = 0
        self.start_time = None
        self.car_state = "locked"

    def connect_to_server(self):
        """Conectare la server"""
        try:
            self.client.connect((self.server_ip, self.port))
            self.connected = True
            print(f"[CAR {self.car_id}] Connected to server.")
            self.register_car()
        except Exception as e:
            print(f"[CAR {self.car_id}] Connection error: {e}")
            self.connected = False

    def register_car(self):
        """Trimite un mesaj de înregistrare către server"""
        registration_msg = json.dumps({"action": "register_car", "car_id": self.car_id})
        self.client.send(registration_msg.encode("utf-8"))

        response = self.client.recv(1024).decode("utf-8")
        if response:
            print(f"[CAR {self.car_id}] Server response: {json.loads(response).get('message')}")

    def send_status_update(self):
        """Trimite starea actuală a mașinii la server"""
        if self.connected:
            status_msg = json.dumps({
                "action": "reportState",
                "car_id": self.car_id,
                "state": self.car_state,
                "distance": self.total_distance,
                "time": self.total_time
            })
            self.client.send(status_msg.encode("utf-8"))
            print(f"[CAR {self.car_id}] Status sent: {self.car_state}, Distance: {self.total_distance} km, Time: {self.total_time} sec")

    def receive_commands(self):
        """Ascultă și procesează comenzile de la server"""
        while self.connected:
            try:
                data = self.client.recv(4096).decode("utf-8")
                if not data:
                    break

                request = json.loads(data)
                action = request.get("action")

                print(f"[CAR {self.car_id}] Received data: {request}")  # Debugging

                if action == "unlock":
                    self.car_state = "unlocked"
                    print(f"[CAR {self.car_id}] Car unlocked!")
                    self.send_status_update()
                elif action == "lock":
                    self.car_state = "locked"
                    print(f"[CAR {self.car_id}] Car locked!")
                    self.send_status_update()
                elif action == "start_rental":
                    self.start_rental()
                elif action == "drive":
                    self.drive()
                elif action == "end_rental":
                    self.end_rental()
                else:
                    print(f"[CAR {self.car_id}] Unknown command: {action}")
            except Exception as e:
                print(f"[CAR {self.car_id}] Error processing command: {e}")
                break

        self.disconnect()

    def start_rental(self):
        """Pornirea închirierii mașinii"""
        self.rental_active = True
        self.total_distance = 0
        self.total_time = 0
        self.start_time = time.time()

        print(f"[CAR {self.car_id}] Rental started.")
        self.send_status_update()

    def drive(self):
        """Simulează deplasarea mașinii"""
        if self.rental_active:
            self.car_state = "unlocked"
            distance = random.randint(1, 50)
            self.total_distance += distance
            self.total_time = int(time.time() - self.start_time)

            print(f"[CAR {self.car_id}] Driving... Covered {distance} km. Total: {self.total_distance} km.")
            self.send_status_update()

    def end_rental(self):
        """Închiderea închirierii și verificarea stării mașinii"""
        if self.rental_active:
            self.rental_active = False
            self.total_time = int(time.time() - self.start_time)
            self.car_state = "locked"

            print(f"[CAR {self.car_id}] Rental ended. Car locked.")
            self.send_status_update()

    def disconnect(self):
        """Închide conexiunea cu serverul"""
        self.connected = False
        self.client.close()
        print(f"[CAR {self.car_id}] Disconnected from server.")

    def start(self):
        """Pornește clientul mașinii"""
        self.connect_to_server()

        if self.connected:
            threading.Thread(target=self.receive_commands, daemon=True).start()
            while self.connected:
                time.sleep(3)
                self.send_status_update()


if __name__ == "__main__":
    car_id = input("Enter car ID: ")
    car = CarClient(car_id)
    car.start()